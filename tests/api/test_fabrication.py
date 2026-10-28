"""Fabrication par code branchée sur la file (étape 5) : lancer depuis Génération, essais, échecs, asset en revue."""
import json
import shutil

import pytest

from api import chemins, db
from api.services import fabrication, outils
from tests.conftest import ecrire_config
from worker.main import Worker

BESOIN = "Des armes de légionnaire et un peu de mobilier."


def _worker_tourne(cfg, timeout=120):
    w = Worker(verrou="test", tick_s=0.05, backoff_base_s=0, charger_config=lambda: cfg)
    try:
        w.tour()
        assert w.attendre_fin(timeout)
    finally:
        w.arreter(delai_s=1)


@pytest.fixture
def avec_scutum(atelier):
    """Le générateur scutum du dépôt, dans le dossier de générateurs du test (il importe generators._base du dépôt)."""
    shutil.copy(chemins.racine() / "generators" / "scutum.py", atelier.generateurs / "scutum.py")


def _choisir_variante(client, conn, lid, oid, params=None):
    """La variante que l'écran Références aurait rendue et que l'utilisateur choisit (posée en base : pas de Blender)."""
    pid = db.inserer(conn, "propositions", {
        "objet_id": oid, "serie": 1, "rang": 0, "genre": "variante", "fichier": "s1-1.png", "legende": "Motif ailes",
        "params_json": json.dumps(params or {"variante": "A", "motif": "ailes", "courbure": 0.5}), "credits": 0,
        "simule": 0, "cree_le": db.maintenant()})
    conn.commit()
    assert client.put(f"/api/lots/{lid}/objets/{oid}/reference", json={"proposition_id": pid}).status_code == 200
    return pid


def _lancer_scutum(client, conn, cfg, garder_seulement_le_scutum=True):
    """Brief validé, variante du scutum choisie, « Lancer la génération 3D » : la tâche de fabrication du scutum."""
    lid, scutum = _lot_avec_scutum(client, cfg, garder_seulement_le_scutum)
    _choisir_variante(client, conn, lid, scutum)
    r = client.post(f"/api/lots/{lid}/lancer")
    assert r.status_code == 202, r.text
    return lid, scutum, r.json()["taches"][0]


def _lot_avec_scutum(client, cfg, garder_seulement_le_scutum=False):
    """Un lot dont la liste simulée contient un objet « scutum » : en voie code grâce au générateur."""
    lot = client.post("/api/lots", json={"theme": "Thème", "besoin": BESOIN}).json()
    client.post(f"/api/lots/{lot['id']}/proposition")
    _worker_tourne(cfg)
    objets = client.get(f"/api/lots/{lot['id']}/objets").json()["objets"]
    scutum = next(o for o in objets if o["type_objet"] == "scutum")
    assert scutum["voie"] == "code" and scutum["generateur"] == "scutum"
    for o in objets:
        if garder_seulement_le_scutum and o["id"] != scutum["id"]:
            client.patch(f"/api/lots/{lot['id']}/objets/{o['id']}", json={"retenu": False})
        elif o["voie"] == "a_creer":
            client.patch(f"/api/lots/{lot['id']}/objets/{o['id']}", json={"voie": "ia"})
    assert client.post(f"/api/lots/{lot['id']}/valider-brief").status_code == 200
    return lot["id"], scutum["id"]


def test_refus_clairs(client, conn, cfg, avec_scutum):
    lot = client.post("/api/lots", json={"theme": "T", "besoin": BESOIN}).json()
    r = client.post(f"/api/lots/{lot['id']}/lancer")
    assert r.status_code == 409 and "choisis d'abord une référence" in r.json()["erreur"]
    lid, scutum = _lot_avec_scutum(client, cfg)
    r = client.post(f"/api/lots/{lid}/fabriquer", json={"objet_id": scutum})
    assert r.status_code == 409 and "choisis d'abord sa référence" in r.json()["erreur"]
    ia = next(o for o in client.get(f"/api/lots/{lid}/objets").json()["objets"] if o["voie"] == "ia" and not o["retire"])
    r = client.post(f"/api/lots/{lid}/fabriquer", json={"objet_id": ia["id"]})
    assert r.status_code == 409 and "choisis d'abord sa référence" in r.json()["erreur"]
    assert client.post(f"/api/lots/{lid}/fabriquer", json={"objet_id": 999}).status_code == 404
    # La fabrication se lance depuis les Références : l'onglet Génération s'ouvre au lancement.
    etapes = {e["cle"]: e for e in client.get(f"/api/lots/{lid}").json()["etapes"]}
    assert etapes["generation"]["atteinte"] is False
    _choisir_variante(client, conn, lid, scutum)
    assert client.post(f"/api/lots/{lid}/lancer").status_code == 202
    etapes = {e["cle"]: e for e in client.get(f"/api/lots/{lid}").json()["etapes"]}
    assert etapes["generation"]["atteinte"] is True and etapes["revue"]["atteinte"] is False


def test_sans_blender_echec_definitif_puis_nouvel_essai(client, conn, cfg, avec_scutum, atelier):
    lid, scutum = _lot_avec_scutum(client, cfg)
    code = [o["id"] for o in client.get(f"/api/lots/{lid}/objets").json()["objets"] if o["voie"] == "code" and not o["retire"]]
    assert len(code) >= 1
    for oid in code:
        _choisir_variante(client, conn, lid, oid)
    r = client.post(f"/api/lots/{lid}/lancer")
    assert r.status_code == 202 and len(r.json()["taches"]) == len(code)  # une tâche Blender par objet code
    tid = next(t for t in r.json()["taches"] if client.get(f"/api/taches/{t}").json()["objet_id"] == scutum)
    t = client.get(f"/api/taches/{tid}").json()
    assert t["file"] == "blender" and t["objet_id"] == scutum
    assert client.post(f"/api/lots/{lid}/fabriquer", json={"objet_id": scutum}).json()["erreur"].startswith("déjà en cours")
    ecrire_config(atelier.config, lambda c: c["blender"].update({"chemin": ""}))
    from api import config as cfgmod
    _worker_tourne(cfgmod.charger())
    t = client.get(f"/api/taches/{tid}").json()
    assert t["etat"] == "echouee" and t["tentatives"] == 1 and "Blender introuvable" in t["erreur"]
    g = client.get(f"/api/lots/{lid}/generation").json()
    o = next(x for x in g["objets"] if x["id"] == scutum)
    assert o["essai"]["etat"] == "echec" and o["statut"].startswith("Échec à l'étape Génération")
    assert [p["etat"] for p in o["etapes"]] == ["echec", "a_faire", "a_faire", "a_faire"] and o["peut_fabriquer"]
    # Relancer = un nouvel essai (numéro 2), dans son propre dossier.
    client.post(f"/api/lots/{lid}/fabriquer", json={"objet_id": scutum})
    essais = db.toutes(conn, "SELECT numero, dossier, etat FROM essais WHERE objet_id = ? ORDER BY numero", (scutum,))
    assert [(e["numero"], e["etat"]) for e in essais] == [(1, "echec"), (2, "en_attente")]
    assert essais[1]["dossier"] == f"{lid}/{scutum}/essai-2"


def test_identifiants_d_asset(conn):
    assert fabrication._mot("bouclier rond à umbo") == "BouclierRondAUmbo"
    assert fabrication.identifiant(conn, "ROM", "prop_moyen", "scutum", 1) == "ROM_PROP_Scutum_A"
    assert fabrication.identifiant(conn, "ROM", "module_archi", "colonne", 2) == "ROM_ARCHI_Colonne_A"


@pytest.fixture
def cfg_blender(cfg, atelier):
    chemin = outils.detecter_blender()
    if chemin is None:
        pytest.skip("Blender 5.2 introuvable sur cette machine")
    ecrire_config(atelier.config, lambda c: c["blender"].update({"chemin": chemin}))
    from api import config as cfgmod
    return cfgmod.charger()


@pytest.mark.blender
def test_scutum_fabrique_par_le_worker_jusqu_a_la_revue(client, conn, cfg_blender, avec_scutum):
    lid, scutum, tid = _lancer_scutum(client, conn, cfg_blender)
    _worker_tourne(cfg_blender, timeout=300)
    t = client.get(f"/api/taches/{tid}").json()
    assert t["etat"] == "terminee", t["erreur"]
    asset = db.une(conn, "SELECT * FROM assets WHERE objet_id = ?", (scutum,))
    assert asset["id"] == "ROM_PROP_Scutum_A" and asset["statut"] == "revue" and asset["voie"] == "code"
    v = db.une(conn, "SELECT * FROM versions WHERE asset_id = ?", (asset["id"],))
    meta = json.loads(v["meta_json"])
    assert v["numero"] == 1 and meta["licence"] is None and meta["generateur"].startswith("generators/scutum.py@")
    g = client.get(f"/api/lots/{lid}/generation").json()
    o = next(x for x in g["objets"] if x["id"] == scutum)
    assert [p["etat"] for p in o["etapes"]] == ["fait"] * 4 and o["statut"] == "Prêt à valider"
    assert o["asset_id"] == "ROM_PROP_Scutum_A" and g["tuiles"]["prets_revue"] == 1
    for url in (o["vignette"], o["planche"]):
        r = client.get(url)
        assert r.status_code == 200 and r.headers["content-type"] == "image/png"
    assert client.get(f"/api/fichiers/essais/{o['essai']['id']}/..%2Fmeta.json").status_code == 404
    rapport = json.loads(db.une(conn, "SELECT rapport_tests_json FROM essais WHERE objet_id = ?", (scutum,))["rapport_tests_json"])
    assert rapport["bloquants_ok"] is True
    # Le seul objet fabriqué du lot est prêt : le lot passe à la revue, une seule notification.
    assert client.get(f"/api/lots/{lid}").json()["etape_courante"] == 4
    notifs = client.get("/api/notifications").json()["notifications"]
    assert [n["titre"] for n in notifs if n["type"] == "revue_prete"] == [f"À valider · {client.get(f'/api/lots/{lid}').json()['nom']}"]


@pytest.mark.blender
def test_reprise_apres_arret_sans_refaire_la_generation(client, conn, cfg_blender, avec_scutum, monkeypatch):
    from pipeline import blender

    _lid, _scutum, tid = _lancer_scutum(client, conn, cfg_blender)
    vrai = blender.lancer
    appels = []

    def lancer(commande, *a, **k):
        appels.append(commande)
        if commande == "finir" and appels.count("finir") == 1:
            raise InterruptedError("arrêt du worker (simulé)")
        return vrai(commande, *a, **k)
    monkeypatch.setattr(blender, "lancer", lancer)
    _worker_tourne(cfg_blender, timeout=300)  # arrêté pendant la finition : remise en attente
    assert client.get(f"/api/taches/{tid}").json()["etat"] == "en_attente"
    _worker_tourne(cfg_blender, timeout=300)  # reprise
    assert client.get(f"/api/taches/{tid}").json()["etat"] == "terminee"
    assert appels.count("generer") == 1 and appels.count("finir") == 2
