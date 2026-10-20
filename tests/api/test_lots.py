"""Lots (B1) : création, liste par groupe, étape calculée, en-tête, duplication, validation du brief."""
from api.services import lots as lots_svc


def _creer(client, **corps):
    r = client.post("/api/lots", json=corps)
    assert r.status_code == 201, r.text
    return r.json()


def _objet(conn, lot_id, nom, etape="brief", voie="ia", retire=0, **extra):
    champs = {"lot_id": lot_id, "nom": nom, "type_objet": nom.lower(), "etape": etape, "voie": voie, "retire": retire, **extra}
    cols = ", ".join(champs)
    conn.execute(f"INSERT INTO objets({cols}) VALUES ({', '.join('?' for _ in champs)})", tuple(champs.values()))
    conn.commit()
    return conn.execute("SELECT last_insert_rowid() AS id").fetchone()["id"]


def test_liste_vide(client):
    assert client.get("/api/lots").json() == {"compteurs": {"tous": 0, "en_cours": 0, "termines": 0, "brouillons": 0}, "lots": []}
    assert client.get("/api/lots/42").status_code == 404
    assert client.get("/api/lots?groupe=inconnu").status_code == 422


def test_nouveau_lot_vide_au_brief(client, atelier):
    lot = _creer(client)
    assert lot["nom"] == "" and lot["etape_courante"] == 1 and lot["etat"] == "brouillon"
    assert lot["style"]["code"] == "rome-stylise-v0"  # le seul style validé : pris par défaut
    assert lot["statut"] == "Brouillon" and lot["detail"] == "aucun objet pour l'instant" and lot["lien"] == f"/lots/{lot['id']}/brief"
    assert lot["libelle_etape"] == "Étape 1 sur 4 · Brief"
    assert [e["atteinte"] for e in lot["etapes"]] == [True, False, False, False]
    assert [e["faite"] for e in lot["etapes"]] == [False, False, False, False]
    assert lot["ligne_etat"].startswith("0 objet · créé le ")
    assert (atelier.lots / str(lot["id"])).is_dir()
    liste = client.get("/api/lots").json()
    assert liste["compteurs"] == {"tous": 1, "en_cours": 0, "termines": 0, "brouillons": 1}
    assert liste["lots"][0]["nb_objets"] == 0 and liste["lots"][0]["action"] == "Reprendre"
    assert client.get("/api/lots?groupe=en_cours").json()["lots"] == []
    assert len(client.get("/api/lots?groupe=brouillons").json()["lots"]) == 1


def test_modifier_le_lot(client):
    lot = _creer(client, nom="  Camp ", theme="Rome antique", besoin="Des armes.")
    assert lot["nom"] == "Camp"
    r = client.patch(f"/api/lots/{lot['id']}", json={"nom": "Camp de légionnaires", "besoin": "Armes et mobilier."})
    assert r.status_code == 200 and r.json()["nom"] == "Camp de légionnaires" and r.json()["besoin"] == "Armes et mobilier."
    assert client.patch(f"/api/lots/{lot['id']}", json={"style_id": 999}).status_code == 422
    assert client.patch("/api/lots/999", json={"nom": "x"}).status_code == 404
    # La recherche globale voit le lot
    assert client.get("/api/recherche?q=légion").json()["resultats"][0]["lien"] == f"/lots/{lot['id']}"


def test_etape_calculee_depuis_l_objet_le_moins_avance(client, conn):
    lot = _creer(client, nom="L")
    lid = lot["id"]
    a = _objet(conn, lid, "Scutum", etape="references", voie="code")
    _objet(conn, lid, "Amphore", etape="generation", voie="ia")
    _objet(conn, lid, "Tente", etape="garde", voie="reutilise")  # réutilisé : ne compte pas
    _objet(conn, lid, "Oublié", etape="brief", voie="ia", retire=1)  # retiré : ne compte pas
    lots_svc.synchroniser_etat(conn, lid)
    e = client.get(f"/api/lots/{lid}?etape=references").json()
    assert e["etape_courante"] == 2 and e["statut"] == "À toi" and e["detail"] == "1 référence à choisir" and e["ton"] == "warn"
    assert e["ligne_etat"] == "3 objets · 1 référence choisie · 1 sans référence (import, réutilisation)"
    assert [x["atteinte"] for x in e["etapes"]] == [True, True, True, False]  # Génération ouverte dès le brief validé (A-TRANCHER 5.1) and e["etapes"][0]["faite"] is True
    assert client.get("/api/lots?groupe=en_cours").json()["compteurs"]["en_cours"] == 1

    conn.execute("UPDATE objets SET etape = 'rendus' WHERE id = ?", (a,))
    conn.commit()
    e = client.get(f"/api/lots/{lid}").json()
    assert e["etape_courante"] == 3 and e["statut"] == "En génération" and e["detail"] == "0 sur 2 générés"

    conn.execute("UPDATE objets SET etape = 'revue' WHERE lot_id = ? AND voie != 'reutilise' AND retire = 0", (lid,))
    conn.commit()
    e = client.get(f"/api/lots/{lid}?etape=revue").json()
    assert e["etape_courante"] == 4 and e["statut"] == "Revue prête" and e["detail"] == "2 objets à juger"
    assert e["ligne_etat"] == "3 objets · 0 gardé · 2 à décider · 1 réutilisé"

    conn.execute("UPDATE objets SET etape = 'garde' WHERE id = ?", (a,))
    conn.execute("UPDATE objets SET etape = 'rejete' WHERE lot_id = ? AND etape = 'revue'", (lid,))
    conn.commit()
    lots_svc.synchroniser_etat(conn, lid)
    e = client.get(f"/api/lots/{lid}").json()
    assert e["etape_courante"] == 5 and e["statut"] == "Terminé" and e["detail"] == "1 gardé, 1 jeté"
    assert e["libelle_etape"] == "Terminé" and e["lien"] == f"/bibliotheque?lot={lid}" and e["action"] == "Voir les assets"
    assert all(x["atteinte"] and x["faite"] for x in e["etapes"])
    assert client.get("/api/lots?groupe=termines").json()["compteurs"] == {"tous": 1, "en_cours": 0, "termines": 1, "brouillons": 0}


def test_dupliquer_copie_le_brief_et_les_choix_sans_taches(client, conn):
    lot = _creer(client, nom="Camp", theme="Rome", besoin="Armes.")
    lid = lot["id"]
    _objet(conn, lid, "Scutum", etape="revue", voie="code", generateur="scutum", description="Bouclier")
    _objet(conn, lid, "Amphore", etape="generation", voie="ia", retire=1)
    oid = _objet(conn, lid, "Ratelier", etape="brief", voie="ia", voie_forcee=1, raison_voie="Voie choisie à la main")
    conn.execute("INSERT INTO pieces(objet_id, ordre, nom, nature, voie, etape) VALUES (?, 1, 'Pied', 'geometrique', 'code', 'brief')", (oid,))
    conn.execute("INSERT INTO taches(type, file, etat, lot_id, cree_le) VALUES ('x', 'api', 'terminee', ?, 'x')", (lid,))
    conn.commit()
    r = client.post(f"/api/lots/{lid}/dupliquer")
    assert r.status_code == 201, r.text
    copie = r.json()
    assert copie["nom"] == "Camp (copie)" and copie["duplique_de_id"] == lid and copie["etape_courante"] == 1
    objets = client.get(f"/api/lots/{copie['id']}/objets").json()["objets"]
    assert [o["nom"] for o in objets] == ["Scutum", "Amphore", "Ratelier"]
    assert all(o["etape"] == "brief" for o in objets)  # les choix sont copiés, pas l'avancement
    assert objets[1]["retire"] is True and objets[2]["voie_forcee"] is True and objets[2]["raison_voie"] == "Voie choisie à la main"
    assert objets[0]["generateur"] == "scutum" and objets[2]["pieces"][0]["nom"] == "Pied"
    assert conn.execute("SELECT COUNT(*) AS n FROM taches WHERE lot_id = ?", (copie["id"],)).fetchone()["n"] == 0
    assert client.get("/api/lots").json()["compteurs"]["tous"] == 2


def test_valider_le_brief(client, conn):
    lot = _creer(client, nom="Camp")
    lid = lot["id"]
    r = client.post(f"/api/lots/{lid}/valider-brief")
    assert r.status_code == 409 and "aucun objet retenu" in r.json()["erreur"]
    a = _objet(conn, lid, "Scutum", voie="code", generateur="scutum")
    b = _objet(conn, lid, "Amphore", voie="ia")
    c = _objet(conn, lid, "Ratelier", voie="a_creer")
    d = _objet(conn, lid, "Legionnaire", voie="hors_perimetre")
    e = _objet(conn, lid, "Tente", voie="reutilise", reutilise_asset_id="ROM_PROP_Tente_A")
    f = _objet(conn, lid, "Colonne", voie="mixte", retire=1)
    r = client.post(f"/api/lots/{lid}/valider-brief")
    assert r.status_code == 409 and "Ratelier" in r.json()["erreur"] and "Claude Code" in r.json()["erreur"]

    client.patch(f"/api/lots/{lid}/objets/{c}", json={"voie": "ia"})
    objets = client.get(f"/api/lots/{lid}/objets").json()
    assert objets["resume"] == {"retenus": 5, "a_fabriquer": 3, "cc0": 0, "reutilises": 1, "hors_perimetre": 1, "a_creer": 0,
                                "credits_estimes": 2 * 42, "credits_par_objet_ia": 42}
    r = client.post(f"/api/lots/{lid}/valider-brief")
    assert r.status_code == 200, r.text
    tete = r.json()
    assert tete["etape_courante"] == 2 and tete["etat"] == "en_cours" and tete["credits_prevus"] == 84
    etapes = {o["id"]: (o["etape"], o["retire"]) for o in client.get(f"/api/lots/{lid}/objets").json()["objets"]}
    assert etapes[a] == ("references", False) and etapes[b] == ("references", False) and etapes[c] == ("references", False)
    assert etapes[d] == ("brief", True)  # hors périmètre : retiré, rien à fabriquer
    assert etapes[e] == ("garde", False)  # réutilisé : déjà fait
    assert etapes[f] == ("brief", True)
    assert conn.execute("SELECT type FROM evenements WHERE type = 'brief_valide' AND lot_id = ?", (lid,)).fetchone()
    assert client.get("/api/menu").json()["badges"]["lots"] == 1


def test_cocher_decocher_et_choisir_la_voie(client, conn):
    lot = _creer(client, nom="Camp")
    lid = lot["id"]
    oid = _objet(conn, lid, "Ratelier", voie="a_creer")
    r = client.patch(f"/api/lots/{lid}/objets/{oid}", json={"retenu": False})
    assert r.status_code == 200 and r.json()["objets"][0]["retire"] is True and r.json()["resume"]["retenus"] == 0
    r = client.patch(f"/api/lots/{lid}/objets/{oid}", json={"retenu": True, "voie": "ia"})
    o = r.json()["objets"][0]
    assert o["retire"] is False and o["voie"] == "ia" and o["voie_forcee"] is True and o["generateur"] == "meshy"
    assert r.json()["resume"]["credits_estimes"] == 42
    assert client.patch(f"/api/lots/{lid}/objets/{oid}", json={"voie": "cc0"}).status_code == 422
    assert client.patch(f"/api/lots/{lid}/objets/999", json={"retenu": True}).status_code == 404


def test_appliquer_une_nouvelle_version_du_style_estimation_seulement(client, conn):
    lot = _creer(client, nom="Camp")
    lid = lot["id"]
    assert client.get(f"/api/lots/{lid}").json()["style_plus_recent"] is None
    _objet(conn, lid, "Scutum", etape="revue", voie="code")
    _objet(conn, lid, "Amphore", etape="revue", voie="ia")
    _objet(conn, lid, "Brasero", etape="garde", voie="mixte")
    _objet(conn, lid, "Nouveau", etape="brief", voie="ia")  # pas encore fabriqué : rien à refaire
    v1 = client.post(f"/api/styles/{lot['style']['id']}/versions", json={"note": "v1"}).json()
    assert client.get(f"/api/lots/{lid}").json()["style_plus_recent"] == {"id": v1["id"], "code": "rome-stylise-v1", "version": 1}
    r = client.get(f"/api/lots/{lid}/appliquer-style?style_id={v1['id']}")
    assert r.status_code == 200
    assert r.json() == {"objets_code": ["Scutum"], "objets_ia": ["Amphore", "Brasero"], "credits": 60, "lancement_possible": False,
                        "raison": "Refaire les objets arrive avec la fabrication (étapes 5 et 7 du plan)"}
    assert client.get(f"/api/lots/{lid}/appliquer-style?style_id=999").status_code == 422
    assert client.get(f"/api/lots/{lid}/appliquer-style").status_code == 422
