"""Validation : l'objet fabriqué tel que l'écran le voit (verdict, fichiers), et les décisions garder, jeter, refaire, corriger."""
import json
import shutil

from api import chemins, db
from api.services import lots as lots_svc
from pipeline import validate

AMPHORE = chemins.racine() / "docs" / "maquette" / "modeles" / "amphore-lod0.glb"  # 0,35 × 0,35 × 0,90 m, posée au sol, centrée


def _controle(nom, ok=True, etat="", detail="", bloquant=True):
    return validate.Controle(nom=nom, mesure=None, seuil=None, bloquant=bloquant, ok=ok, detail=detail, etat=etat)


def _projet(client, conn, atelier, *, voie="ia", etat_objet="revue", controles=None, glb=True):
    """Un projet avec un objet fabriqué : essai fini, asset en revue, fichiers sur le disque."""
    lot = client.post("/api/lots", json={"besoin": "Des amphores.", "nom": "Camp"}).json()
    lid = lot["id"]
    conn.execute("INSERT INTO objets(lot_id, nom, type_objet, etape, voie, generateur) VALUES (?, 'Amphore', 'amphore', ?, ?, ?)",
                 (lid, etat_objet, voie, "amphore" if voie == "code" else "meshy"))
    oid = conn.execute("SELECT last_insert_rowid() AS id").fetchone()["id"]
    dossier = f"{lid}/{oid}/essai-1"
    asset = atelier.lots / dossier / "asset"
    (asset / "rendus").mkdir(parents=True)
    if glb:
        shutil.copy(AMPHORE, asset / "ROM_PROP_Amphore_A.glb")
    (asset / "rendus" / "face.png").write_bytes(b"png")
    (asset / "rendus" / "planche.png").write_bytes(b"png")
    controles = controles if controles is not None else [_controle(n) for n in validate.NOMS_CONTROLES[:8]]
    validate.Rapport(id="ROM_PROP_Amphore_A", controles=controles, licence={"ok": True}).ecrire(asset / "rapport.json")
    (asset / "meta.json").write_text(json.dumps({"dimensions_m": [0.35, 0.35, 0.9], "tris_lod0": 3816, "tris_lod1": 1908,
                                                  "tris_lod2": 954}), encoding="utf-8")
    conn.execute("INSERT INTO essais(objet_id, numero, generateur, etat, dossier, cout_credits) VALUES (?, 1, ?, 'pret', ?, 42)",
                 (oid, "meshy" if voie == "ia" else "amphore", dossier))
    essai_id = conn.execute("SELECT last_insert_rowid() AS id").fetchone()["id"]
    maintenant = db.maintenant()
    conn.execute("INSERT INTO assets(id, lot_id, objet_id, nom, theme, voie, statut, cree_le, maj_le) VALUES "
                 "('ROM_PROP_Amphore_A', ?, ?, 'Amphore', 'ROM', ?, 'revue', ?, ?)", (lid, oid, voie, maintenant, maintenant))
    conn.commit()
    lots_svc.synchroniser_etat(conn, lid)
    return lid, oid, essai_id


def _decider(client, lid, oid, decision, **corps):
    return client.post(f"/api/lots/{lid}/objets/{oid}/decision", json={"decision": decision, **corps})


def test_la_vue_donne_le_verdict_les_fichiers_et_les_mesures_du_vrai_fichier(client, conn, atelier):
    lid, _oid, essai = _projet(client, conn, atelier)
    v = client.get(f"/api/lots/{lid}/validation").json()
    assert v["resume"] == {"total": 1, "a_valider": 1, "gardes": 0, "jetes": 0, "pas_prets": 0} and v["termine"] is False
    o = v["objets"][0]
    assert o["etat"] == "a_valider" and o["peut_corriger"] is True and o["peut_annuler"] is False
    assert o["credits_correction"] == 12  # 4 images à 3 crédits
    assert o["modele"] == f"/api/fichiers/essais/{essai}/modele.glb"
    assert [x["nom"] for x in o["vues"]] == ["face"] and o["planche"].endswith("/planche.png")
    assert o["source"] == "Faite par Meshy d'après ton look · essai 1"
    assert o["faits"] == {"dimensions_m": [0.35, 0.35, 0.9], "tris": {"lod0": 3816, "lod1": 1908, "lod2": 954}, "credits": 42,
                          "nombre_essais": 1}
    assert o["verdict"]["etat"] == "ok" and all(r["ok"] for r in o["verdict"]["raisons"])
    textes = [r["texte"] for r in o["verdict"]["raisons"]]
    # Les mesures du fichier passent avant les contrôles.
    assert textes == ["Taille : 0,35 × 0,35 × 0,90 m", "Posé au sol", "Bien centré sur son point d'ancrage", "Forme fermée, sans trou"]
    assert o["verdict"]["autres_ok"] == 7  # 8 contrôles + 3 mesures, moins les 4 montrées
    assert o["avis_ia"] is None  # pas d'avis tant qu'aucune IA n'en a écrit un


def test_un_controle_en_alerte_rend_le_verdict_attentif_et_passe_en_premier(client, conn, atelier):
    controles = [_controle("Maillage fermé"), _controle("Normales", ok=False, bloquant=False, detail="12 faces inversées"),
                 _controle("Polycount"), _controle("Critique IA", etat="non exécuté")]
    lid, _, _ = _projet(client, conn, atelier, controles=controles)
    verdict = client.get(f"/api/lots/{lid}/validation").json()["objets"][0]["verdict"]
    assert verdict["etat"] == "attention"
    assert verdict["raisons"][0] == {"ok": False, "texte": "Des surfaces sont à l'envers (12 faces inversées)"}
    assert not any("IA" in r["texte"] for r in verdict["raisons"])  # un contrôle non exécuté ne dit rien


def test_un_fichier_illisible_ou_absent_est_dit_sans_casser_l_ecran(client, conn, atelier):
    lid, _, essai = _projet(client, conn, atelier, glb=False)
    o = client.get(f"/api/lots/{lid}/validation").json()["objets"][0]
    assert o["modele"] is None and o["verdict"]["etat"] == "attention"
    assert o["verdict"]["raisons"][0]["texte"] == "Le fichier 3D n'a pas pu être mesuré"
    assert client.get(f"/api/fichiers/essais/{essai}/modele.glb").status_code == 404


def test_le_fichier_3d_est_servi_avec_son_type(client, conn, atelier):
    _, _, essai = _projet(client, conn, atelier)
    r = client.get(f"/api/fichiers/essais/{essai}/modele.glb")
    assert r.status_code == 200 and r.headers["content-type"] == "model/gltf-binary" and r.content[:4] == b"glTF"
    assert client.get("/api/fichiers/essais/999/modele.glb").status_code == 404


def test_garder_range_l_objet_dans_la_collection_du_projet_et_s_annule(client, conn, atelier):
    lid, oid, _ = _projet(client, conn, atelier)
    r = _decider(client, lid, oid, "garder")
    assert r.status_code == 200 and r.json()["etat"] == "garde" and r.json()["peut_annuler"] is True
    assert conn.execute("SELECT statut FROM assets WHERE id = 'ROM_PROP_Amphore_A'").fetchone()["statut"] == "garde"
    liens = conn.execute("SELECT c.nom FROM collections c JOIN collections_assets ca ON ca.collection_id = c.id "
                         "WHERE ca.asset_id = 'ROM_PROP_Amphore_A'").fetchall()
    assert [x["nom"] for x in liens] == ["Camp"]
    v = client.get(f"/api/lots/{lid}/validation").json()
    assert v["termine"] is True and v["resume"]["gardes"] == 1
    # Tous les objets sont décidés : le projet passe à l'Essai.
    assert client.get(f"/api/lots/{lid}").json()["etape_courante"] == 5

    r = _decider(client, lid, oid, "annuler")
    assert r.status_code == 200 and r.json()["etat"] == "a_valider"
    assert conn.execute("SELECT COUNT(*) AS n FROM collections_assets").fetchone()["n"] == 0
    assert conn.execute("SELECT statut FROM assets WHERE id = 'ROM_PROP_Amphore_A'").fetchone()["statut"] == "revue"
    assert client.get(f"/api/lots/{lid}").json()["etape_courante"] == 4


def test_jeter_garde_le_motif_et_refuse_un_motif_inconnu(client, conn, atelier):
    lid, oid, _ = _projet(client, conn, atelier)
    assert _decider(client, lid, oid, "jeter", motif="n_importe_quoi").status_code == 422
    r = _decider(client, lid, oid, "jeter", motif="proportions")
    assert r.status_code == 200 and r.json()["etat"] == "jete"
    assert conn.execute("SELECT statut FROM assets WHERE id = 'ROM_PROP_Amphore_A'").fetchone()["statut"] == "archive"
    notes = conn.execute("SELECT texte FROM evenements WHERE type = 'objet_jete'").fetchall()
    assert [n["texte"] for n in notes] == ["motif : proportions"]
    assert _decider(client, lid, oid, "annuler").json()["etat"] == "a_valider"


def test_une_decision_qui_ne_convient_pas_a_l_etat_de_l_objet_est_refusee(client, conn, atelier):
    lid, oid, _ = _projet(client, conn, atelier, etat_objet="generation")
    for d in ("garder", "jeter", "refaire", "annuler"):
        assert _decider(client, lid, oid, d).status_code == 409, d
    assert _decider(client, lid, oid, "n_importe_quoi").status_code == 422
    assert _decider(client, lid, 9999, "garder").status_code == 404
    assert client.get(f"/api/lots/{lid}/validation").json()["objets"][0]["etat"] == "en_fabrication"


def test_refaire_ramene_l_objet_au_look_sans_rien_depenser(client, conn, atelier):
    lid, oid, _ = _projet(client, conn, atelier)
    r = _decider(client, lid, oid, "refaire")
    assert r.status_code == 200 and r.json()["etat"] == "look"
    assert conn.execute("SELECT etape FROM objets WHERE id = ?", (oid,)).fetchone()["etape"] == "references"
    assert conn.execute("SELECT COUNT(*) AS n FROM taches WHERE objet_id = ?", (oid,)).fetchone()["n"] == 0
    assert client.get(f"/api/lots/{lid}").json()["etape_courante"] == 2


def test_corriger_redessine_les_looks_avec_les_remarques(client, conn, atelier):
    lid, oid, _ = _projet(client, conn, atelier)
    assert _decider(client, lid, oid, "corriger").status_code == 422  # sans remarque, rien à corriger
    r = _decider(client, lid, oid, "corriger", notes=["anse trop fine", " "], texte="terre cuite plus claire")
    assert r.status_code == 200 and r.json()["etat"] == "look"
    o = conn.execute("SELECT etape, consigne FROM objets WHERE id = ?", (oid,)).fetchone()
    assert o["etape"] == "references" and o["consigne"].endswith("Corrections demandées : 1. anse trop fine terre cuite plus claire")
    tache = conn.execute("SELECT type, file FROM taches WHERE objet_id = ?", (oid,)).fetchall()
    assert [(t["type"], t["file"]) for t in tache] == [("references_images", "meshy")]


def test_corriger_est_refuse_pour_un_objet_fait_par_script(client, conn, atelier):
    lid, oid, _ = _projet(client, conn, atelier, voie="code")
    o = client.get(f"/api/lots/{lid}/validation").json()["objets"][0]
    assert o["peut_corriger"] is False
    r = _decider(client, lid, oid, "corriger", texte="plus haut")
    assert r.status_code == 409 and "Refaire" in r.json()["erreur"]
    assert conn.execute("SELECT etape FROM objets WHERE id = ?", (oid,)).fetchone()["etape"] == "revue"


def test_validation_d_un_projet_inconnu(client):
    assert client.get("/api/lots/42/validation").status_code == 404
