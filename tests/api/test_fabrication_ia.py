"""Fabrication par IA (étape 7) : l'image choisie part à Meshy (simulé), l'objet 3D suit la chaîne commune jusqu'à la revue."""
import json

import pytest

from api import db
from api.adapters import get_meshy
from api.services import fabrication, fabrication_ia, taches
from tests.conftest import ecrire_config
from worker.main import Worker

BESOIN = "Des contenants et un peu de décor."


def _worker_tourne(cfg, timeout=120):
    w = Worker(verrou="test", tick_s=0.05, backoff_base_s=0, charger_config=lambda: cfg)
    try:
        for _ in range(20):
            w.tour()
            assert w.attendre_fin(timeout)
            conn = db.connexion()
            try:
                if not db.une(conn, "SELECT 1 FROM taches WHERE etat = 'en_attente'"):
                    break
            finally:
                conn.close()
    finally:
        w.arreter(delai_s=1)


def _objet_ia_choisi(client, cfg):
    """Un lot validé, ses images simulées arrivées, une image choisie pour un objet IA ; les autres retirés."""
    lot = client.post("/api/lots", json={"theme": "Thème", "besoin": BESOIN}).json()
    client.post(f"/api/lots/{lot['id']}/proposition")
    _worker_tourne(cfg)
    objets = client.get(f"/api/lots/{lot['id']}/objets").json()["objets"]
    cible = next(o for o in objets if not o["retire"] and o["voie"] in ("ia", "a_creer"))
    for o in objets:
        if o["id"] != cible["id"] and not o["retire"]:
            client.patch(f"/api/lots/{lot['id']}/objets/{o['id']}", json={"retenu": False})
    if cible["voie"] == "a_creer":
        client.patch(f"/api/lots/{lot['id']}/objets/{cible['id']}", json={"voie": "ia"})
    assert client.post(f"/api/lots/{lot['id']}/valider-brief").status_code == 200
    _worker_tourne(cfg)
    o = client.get(f"/api/lots/{lot['id']}/references").json()["objets"][0]
    client.put(f"/api/lots/{lot['id']}/objets/{o['id']}/reference", json={"proposition_id": o["propositions"][1]["id"]})
    return lot["id"], o["id"]


@pytest.fixture
def cfg_blender(cfg, atelier):
    from api import config as cfgmod
    from api.services import outils

    chemin = outils.detecter_blender()
    if chemin is None:
        pytest.skip("Blender 5.2 introuvable sur cette machine")
    ecrire_config(atelier.config, lambda c: c["blender"].update({"chemin": chemin}))
    return cfgmod.charger()


def test_lancer_envoie_l_image_choisie_a_meshy_avec_le_budget_du_style(client, conn, cfg):
    lid, oid = _objet_ia_choisi(client, cfg)
    r = client.post(f"/api/lots/{lid}/lancer")
    assert r.status_code == 202 and r.json()["par_ia"] == 1
    tid = r.json()["taches"][0]
    t = taches.lire_tache(conn, tid)
    assert t["type"] == "generer_ia" and t["file"] == "meshy"
    essai = db.une(conn, "SELECT * FROM essais WHERE objet_id = ?", (oid,))
    options = json.loads(essai["params_json"])
    assert options["should_remesh"] is True and options["topology"] == "triangle" and options["enable_pbr"] is True
    objet = db.une(conn, "SELECT categorie FROM objets WHERE id = ?", (oid,))
    from api.services import styles
    assert options["target_polycount"] == styles.charger_style("rome-stylise-v0").budget(objet["categorie"])
    # Sans Blender (config de test) : l'objet 3D arrive de Meshy, la finition échoue avec un motif clair.
    _worker_tourne(cfg)
    meshy = get_meshy(cfg).etat.charger()["taches"]
    envoi = next(x for x in meshy.values() if x["genre"] == "3d")
    assert envoi["entree"]["image"].endswith(".png") and "/references/" in envoi["entree"]["image"]
    assert envoi["entree"]["options"] == options
    essai = db.une(conn, "SELECT * FROM essais WHERE objet_id = ?", (oid,))
    source = json.loads(essai["source_json"])
    assert source["glb"].endswith(".glb") and (fabrication.dossier_essai(essai) / source["glb"]).is_file()
    assert essai["cout_credits"] == 30 and essai["etat"] == "echec" and "Blender introuvable" in essai["erreur"]
    cout = db.une(conn, "SELECT * FROM couts WHERE type = 'generation_3d'")
    assert cout["credits"] == 30 and cout["simule"] and cout["lot_id"] == lid
    g = client.get(f"/api/lots/{lid}/generation").json()
    o = next(x for x in g["objets"] if x["id"] == oid)
    assert o["statut"].startswith("Échec à l'étape Génération") and o["peut_fabriquer"] and o["peut_rechoisir"]
    assert {t["libelle"] for t in g["taches"]} >= {"Objet 3D par IA (Meshy)", "Finition d'un objet IA (Blender)"}
    # Refaire : un nouvel essai, une nouvelle génération Meshy.
    r = client.post(f"/api/lots/{lid}/fabriquer", json={"objet_id": oid})
    assert r.status_code == 202 and taches.lire_tache(conn, r.json()["taches"][0])["type"] == "generer_ia"
    assert db.une(conn, "SELECT COUNT(*) AS n FROM essais WHERE objet_id = ?", (oid,))["n"] == 2


def _prendre(conn, tid):
    """La tâche passe « en cours », comme si le worker l'avait prise."""
    conn.execute("UPDATE taches SET etat = 'en_cours' WHERE id = ?", (tid,))
    conn.commit()


def test_reprise_sans_payer_deux_fois(client, conn, cfg):
    lid, _oid = _objet_ia_choisi(client, cfg)
    tid = client.post(f"/api/lots/{lid}/lancer").json()["taches"][0]
    essai_id = taches.lire_tache(conn, tid)["essai_id"]
    meshy = get_meshy(cfg)
    _prendre(conn, tid)
    arrets = iter([False, True])  # le worker s'arrête pendant l'attente de Meshy
    with pytest.raises(InterruptedError):
        fabrication_ia.executer_generation(conn, meshy, cfg, {"essai_id": essai_id}, tache_id=tid,
                                           arret=lambda: next(arrets, True), attente_s=0)
    restants = meshy.solde()["restants"]
    r = fabrication_ia.executer_generation(conn, meshy, cfg, {"essai_id": essai_id}, tache_id=tid, attente_s=0)
    assert meshy.solde()["restants"] == restants  # la reprise relit la tâche Meshy, elle n'en paie pas une autre
    assert sum(1 for x in meshy.etat.charger()["taches"].values() if x["genre"] == "3d") == 1
    # Refaire la tâche ne double ni le coût ni la finition.
    r2 = fabrication_ia.executer_generation(conn, meshy, cfg, {"essai_id": essai_id}, tache_id=tid, attente_s=0)
    assert r2["finition"] == r["finition"]
    assert db.une(conn, "SELECT COUNT(*) AS n FROM couts WHERE type = 'generation_3d'")["n"] == 1


def test_meshy_refuse_l_essai_echoue_sans_relance(client, conn, cfg, monkeypatch):
    from api.adapters.meshy.base import RefusMeshy
    from api.adapters.meshy.simule import MeshySimule

    def refus(self, *a, **k):
        raise RefusMeshy("crédits Meshy insuffisants")

    monkeypatch.setattr(MeshySimule, "image_vers_3d", refus)
    lid, oid = _objet_ia_choisi(client, cfg)
    tid = client.post(f"/api/lots/{lid}/lancer").json()["taches"][0]
    _prendre(conn, tid)
    with pytest.raises(taches.TacheDefinitive):
        fabrication_ia.executer_generation(conn, get_meshy(cfg), cfg, taches.lire_tache(conn, tid)["params"], tache_id=tid,
                                           attente_s=0)
    essai = db.une(conn, "SELECT * FROM essais WHERE objet_id = ?", (oid,))
    assert essai["etat"] == "echec" and "crédits Meshy insuffisants" in essai["erreur"]


def test_relance_automatique_trois_fois_au_plus(client, conn, cfg):
    lid, oid = _objet_ia_choisi(client, cfg)
    client.post(f"/api/lots/{lid}/lancer")
    essai = db.une(conn, "SELECT * FROM essais WHERE objet_id = ?", (oid,))
    suites = []
    for _ in range(5):
        conn.execute("UPDATE taches SET etat = 'annulee' WHERE etat = 'en_attente'")
        conn.commit()
        try:
            r = fabrication._echec_qualite(conn, cfg, essai, True, "contrôles en échec : Maillage fermé", {"controles": []})
        except taches.TacheDefinitive as e:
            assert "après 3 relances automatiques" in str(e)
            break
        suites.append(r["relance"])
        essai = db.une(conn, "SELECT * FROM essais WHERE objet_id = ? ORDER BY numero DESC LIMIT 1", (oid,))
    assert len(suites) == 3  # 1 essai + 3 relances (Réglages : relances automatiques = 3)
    g = client.get(f"/api/lots/{lid}/generation").json()
    assert g["tuiles"]["relances"] >= 3
    assert db.une(conn, "SELECT COUNT(*) AS n FROM evenements WHERE type = 'relance_auto'")["n"] == 3


@pytest.mark.blender
def test_l_image_devient_un_objet_pret_pour_la_revue(client, conn, cfg_blender):
    lid, oid = _objet_ia_choisi(client, cfg_blender)
    client.post(f"/api/lots/{lid}/lancer")
    _worker_tourne(cfg_blender, timeout=300)
    essai = db.une(conn, "SELECT * FROM essais WHERE objet_id = ? ORDER BY numero DESC LIMIT 1", (oid,))
    assert essai["etat"] == "pret", essai["erreur"]
    asset = db.une(conn, "SELECT * FROM assets WHERE objet_id = ?", (oid,))
    assert asset["statut"] == "revue" and asset["voie"] == "ia"
    dossier = fabrication.dossier_essai(essai) / "asset"
    meta = json.loads((dossier / "meta.json").read_text(encoding="utf-8"))
    assert meta["voie"] == "A" and meta["sources"][0]["licence"] == "Meshy-Pro" and meta["outils_ia"]["geometrie"]
    assert meta["parametres"]["reference"]["genre"] == "image" and meta["licence"] is None
    interne = json.loads((dossier / "rapport_interne.json").read_text(encoding="utf-8"))
    assert interne["normalisation"]["reparation"]["debris_retires"] == 1  # le débris du GLB simulé
    assert interne["textures"] and interne["textures"][0]["px"] == 1024  # 2K de Meshy ramené à la taille du style
    rapport = json.loads(db.une(conn, "SELECT rapport_tests_json FROM essais WHERE id = ?", (essai["id"],))["rapport_tests_json"])
    assert rapport["bloquants_ok"] is True
    dims = next(c for c in rapport["controles"] if c["nom"] == "Dimensions")
    assert dims["ok"] and "proportions à juger en revue" in dims["detail"]
    g = client.get(f"/api/lots/{lid}/generation").json()
    o = next(x for x in g["objets"] if x["id"] == oid)
    assert o["statut"] == "Prêt à valider" and o["vignette"].endswith("vignette.png")
