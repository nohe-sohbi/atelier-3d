"""Demande pour Claude Code : Markdown depuis le style et l'objet, écriture idempotente, détection du script."""
import pytest

from api.services import demandes
from tests.fabrique_generateur import ecrire_generateur
from worker.main import Worker
from worker.periodiques import Periodiques


def _lot_avec_objet(client, conn, **objet):
    lot = client.post("/api/lots", json={"nom": "Camp de légionnaires", "theme": "Rome antique", "besoin": "Armes."}).json()
    champs = {"lot_id": lot["id"], "nom": "Râtelier d'armes", "type_objet": "ratelier d'armes", "categorie": "grand_prop",
              "nature": "geometrique", "voie": "a_creer", "famille": "mobilier", "symetrique": "X",
              "description": "Râtelier vertical en bois, deux traverses, cinq emplacements pour pilums.",
              "dimensions_json": '{"largeur": 1.2, "profondeur": 0.4, "hauteur": 1.6, "source": "claude"}',
              "materiaux_json": '["bois", "fer"]', "parametres_json": '["emplacements", "hauteur", "usure"]', **objet}
    cols = ", ".join(champs)
    conn.execute(f"INSERT INTO objets({cols}) VALUES ({', '.join('?' for _ in champs)})", tuple(champs.values()))
    conn.commit()
    oid = conn.execute("SELECT last_insert_rowid() AS id").fetchone()["id"]
    return lot["id"], oid


def test_nom_module_et_chemins():
    assert demandes.nom_module("Bouclier rond") == "bouclier_rond"
    assert demandes.nom_module("Râtelier d'armes") == "ratelier_darmes"
    assert demandes.chemin_relatif("ratelier") == "generators/demandes/ratelier.md"
    assert demandes.texte_a_coller("ratelier") == ("Lis generators/demandes/ratelier.md et écris generators/ratelier.py en suivant "
                                                   "generators/CONTRAT.md. Lance les tests de finition avant de rendre la main.")
    with pytest.raises(ValueError):
        demandes.nom_module("…")


def test_markdown_depuis_le_style_et_l_objet(client, conn, atelier):
    lid, oid = _lot_avec_objet(client, conn)
    r = client.get(f"/api/lots/{lid}/objets/{oid}/demande")
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["chemin_md"] == "generators/demandes/ratelier_darmes.md" and d["script_attendu"] == "generators/ratelier_darmes.py"
    assert d["etat"] == "a_ecrire" and d["libelle_etat"] == "Pas encore écrite" and d["ecrite_le"] is None
    md = d["markdown"]
    assert md.startswith("# Générateur à écrire : râtelier d'armes\n")
    assert "type        : ratelier_darmes" in md and "taille      : grand_prop" in md
    assert "dimensions  : 1,20 × 1,60 m, profondeur 0,40 m" in md
    assert "budget      : 15 000 tris (grand objet, style rome-stylise-v0)" in md  # lu dans le style, jamais en dur
    assert "matériaux   : bois, fer (palette du style)" in md and "pivot       : au sol, centré" in md
    assert "Intention : Râtelier vertical en bois" in md and "Paramètres attendus : emplacements, hauteur, usure." in md
    assert "Demandé par : lot Camp de légionnaires." in md and "generators/CONTRAT.md" in md
    assert d["tests"] == {"disponibles": False, "raison": "Les tests du script (finition, Blender) arrivent à l'étape 5 du plan"}
    assert not (atelier.generateurs / "demandes").exists()
    assert client.get(f"/api/lots/{lid}/objets/999/demande").status_code == 404


def test_ecrire_est_idempotent_et_reste_dans_le_depot(client, conn, atelier):
    lid, oid = _lot_avec_objet(client, conn)
    r = client.post(f"/api/lots/{lid}/objets/{oid}/demande")
    assert r.status_code == 201, r.text
    d = r.json()
    fichier = atelier.generateurs / "demandes" / "ratelier_darmes.md"
    assert fichier.read_text(encoding="utf-8") == d["markdown"]
    assert d["etat"] == "ecrite" and d["libelle_etat"] == "Écrite dans le dépôt" and d["ecrite_le"]
    assert conn.execute("SELECT COUNT(*) AS n FROM evenements WHERE type = 'demande_ecrite'").fetchone()["n"] == 1

    d2 = client.post(f"/api/lots/{lid}/objets/{oid}/demande").json()
    assert d2["ecrite_le"] == d["ecrite_le"]
    assert conn.execute("SELECT COUNT(*) AS n FROM demandes_generateurs").fetchone()["n"] == 1
    assert conn.execute("SELECT COUNT(*) AS n FROM evenements WHERE type = 'demande_ecrite'").fetchone()["n"] == 1
    assert [p.name for p in (atelier.generateurs / "demandes").iterdir()] == ["ratelier_darmes.md"]
    assert demandes.lister(conn)[0]["type_objet"] == "ratelier d'armes"


def test_un_type_tordu_ne_sort_pas_du_dossier(client, conn, atelier):
    lid, oid = _lot_avec_objet(client, conn, type_objet="../../etc/passwd", nom="Tordu")
    d = client.post(f"/api/lots/{lid}/objets/{oid}/demande").json()
    assert d["chemin_md"] == "generators/demandes/etcpasswd.md"
    assert (atelier.generateurs / "demandes" / "etcpasswd.md").exists()


def test_script_detecte_reroute_les_objets(client, conn, atelier):
    lid, oid = _lot_avec_objet(client, conn)
    client.post(f"/api/lots/{lid}/objets/{oid}/demande")
    assert demandes.scanner(conn) == []  # pas encore de script

    ecrire_generateur(atelier.generateurs, "ratelier_darmes", types=["ratelier d'armes"], categorie="grand_prop")
    assert "scanner_generateurs" in Periodiques().tour(conn, forcer=True)
    d = client.get(f"/api/lots/{lid}/objets/{oid}/demande").json()
    assert d["etat"] == "script_detecte" and d["libelle_etat"] == "Script détecté" and d["script_detecte_le"]
    o = client.get(f"/api/lots/{lid}/objets").json()["objets"][0]
    assert o["voie"] == "code" and o["generateur"] == "ratelier_darmes" and o["regle_id"] == 3 and o["voie_forcee"] is False
    ev = conn.execute("SELECT * FROM evenements WHERE type = 'script_detecte'").fetchone()
    assert ev["titre"] == "Script détecté : generators/ratelier_darmes.py" and ev["lien"] == f"/lots/{lid}/brief"
    assert demandes.scanner(conn) == []  # déjà détecté : pas de second événement
    assert conn.execute("SELECT COUNT(*) AS n FROM evenements WHERE type = 'script_detecte'").fetchone()["n"] == 1


def test_une_voie_forcee_n_est_pas_reroutee(client, conn, atelier):
    lid, oid = _lot_avec_objet(client, conn, voie="ia", voie_forcee=1)
    client.post(f"/api/lots/{lid}/objets/{oid}/demande")
    ecrire_generateur(atelier.generateurs, "ratelier_darmes", types=["ratelier d'armes"])
    assert demandes.scanner(conn) == ["ratelier_darmes"]
    assert client.get(f"/api/lots/{lid}/objets").json()["objets"][0]["voie"] == "ia"


def test_le_worker_lance_le_scanner_a_chaque_tour_mais_pas_plus_souvent_que_la_periode(atelier, conn, cfg):
    appels = []
    horloge = [0.0]
    p = Periodiques({"compteur": (30.0, lambda c: appels.append(horloge[0]))}, horloge=lambda: horloge[0])
    w = Worker(verrou="test", tick_s=0.05, charger_config=lambda: cfg, periodiques=p)
    try:
        w.tour()
        horloge[0] = 10.0
        w.tour()
        horloge[0] = 31.0
        w.tour()
    finally:
        w.arreter(delai_s=1)
    assert appels == [0.0, 31.0]


def test_un_periodique_qui_casse_ne_tue_pas_la_boucle(conn):
    def casse(c):
        raise RuntimeError("boum")
    p = Periodiques({"casse": (30.0, casse), "ok": (30.0, lambda c: None)})
    assert p.tour(conn, forcer=True) == ["ok"]
