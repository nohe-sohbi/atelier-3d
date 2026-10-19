"""Relecture indépendante de l'étape 2 (PASSATION.md §4.1) : un test par constat, écrit avant le correctif."""
import logging

import httpx
import pytest
import yaml

from api import db
from api.adapters import _commun, get_meshy
from api.adapters.meshy import reel
from api.adapters.meshy.simule import MeshySimule
from api.services import styles, taches
from api.services.taches import TacheDefinitive
from tests.conftest import ecrire_config
from worker.main import Worker

PALETTE = {"Chêne": "#8A6A45", "Fer": "#5B5F66", "Pierre": "#9A968D", "Rouge": "#A63A2E", "Lin": "#D9CBB0",
           "Or": "#C9A13B", "Bleu nuit": "#2B3A55", "Ivoire": "#F1EBDD"}


def _pilote(client):
    return next(s for s in client.get("/api/styles").json()["styles"] if s["code"] == "rome-stylise-v0")


def _nouveau(client, nom="Médiéval stylisé", **extra):
    r = client.post("/api/styles", json={"nom": nom, "palette": PALETTE, "budgets_depuis": _pilote(client)["id"], **extra})
    assert r.status_code == 201, r.text
    return r.json()


def _worker_tourne(cfg):
    w = Worker(verrou="test", tick_s=0.05, backoff_base_s=0, charger_config=lambda: cfg)
    try:
        w.tour()
        assert w.attendre_fin(30)
    finally:
        w.arreter(delai_s=1)


class MeshyEspion(MeshySimule):
    """Le simulateur, qui garde la trace des appels image."""

    def __init__(self, cfg, **kw):
        super().__init__(cfg, **kw)
        self.appels: list[dict] = []

    def image_vers_image(self, prompt, image=None, n=1):
        self.appels.append({"prompt": prompt, "image": image, "n": n})
        return super().image_vers_image(prompt, image, n)


# --- B1 · deux styles du même nom et de la même version ----------------------------------------

def test_b1_meme_nom_meme_version_409_sans_dossier_orphelin(client, atelier):
    r = client.post("/api/styles", json={"nom": "Rome antique stylisée", "code": "autre-rome-v0", "palette": PALETTE,
                                         "budgets_depuis": _pilote(client)["id"]})
    assert r.status_code == 409, r.text
    assert "Rome antique stylisée" in r.json()["erreur"]
    assert not (atelier.styles / "autre-rome-v0").exists()


def test_b1_un_doublon_sur_le_disque_n_empeche_pas_l_api_de_demarrer(atelier, caplog):
    brut = yaml.safe_load((atelier.styles / "rome-stylise-v0" / "style.yaml").read_text(encoding="utf-8"))
    brut["style"] = "zz-doublon-v0"  # importé après le pilote ; même nom et même version que le style pilote
    (atelier.styles / "zz-doublon-v0").mkdir()
    (atelier.styles / "zz-doublon-v0" / "style.yaml").write_text(yaml.safe_dump(brut, allow_unicode=True), encoding="utf-8")
    from fastapi.testclient import TestClient

    from api.main import create_app
    with caplog.at_level(logging.WARNING), TestClient(create_app()) as c:
        codes = [s["code"] for s in c.get("/api/styles").json()["styles"]]
    assert "rome-stylise-v0" in codes and "zz-doublon-v0" not in codes
    assert any("zz-doublon-v0" in m for m in caplog.messages)


def test_b1_modifier_vers_un_nom_pris_409_et_fichier_intact(client, atelier):
    d = _nouveau(client)
    avant = (atelier.styles / d["code"] / "style.yaml").read_text(encoding="utf-8")
    r = client.put(f"/api/styles/{d['id']}", json={"nom": "Rome antique stylisée"})
    assert r.status_code == 409, r.text
    assert (atelier.styles / d["code"] / "style.yaml").read_text(encoding="utf-8") == avant  # I4 : rien d'écrit


# --- B2 · arrêt du worker pendant une planche ----------------------------------------------------

def test_b2_arret_pendant_la_planche_puis_reprise_sans_doublon(client, conn, cfg, atelier):
    d = _nouveau(client)
    tid = client.post(f"/api/styles/{d['id']}/planche").json()["tache_id"]
    t = taches.prendre_tache(conn, "meshy", "w1", 1)
    assert t["id"] == tid
    with pytest.raises(InterruptedError):
        styles.executer_planche(conn, get_meshy(cfg), t["params"], tache_id=tid, attente_s=0, arret=lambda: True)
    taches.remettre_en_attente(conn, tid, "arrêt du worker avant la fin")
    assert db.une(conn, "SELECT COUNT(*) AS n FROM planche_images WHERE style_id = ?", (d["id"],))["n"] == 0
    _worker_tourne(cfg)  # reprise : les tâches Meshy déjà payées sont reprises, pas redemandées
    assert client.get(f"/api/taches/{tid}").json()["etat"] == "terminee"
    detail = client.get(f"/api/styles/{d['id']}").json()
    assert len(detail["planche"]) == 6 and detail["credits_planche"] == 18
    assert get_meshy(cfg).solde()["restants"] == 1000 - 18
    lignes = db.toutes(conn, "SELECT tache_id FROM planche_images WHERE style_id = ?", (d["id"],))
    assert {x["tache_id"] for x in lignes} == {tid}


def test_b2_rangement_idempotent(client, conn, cfg):
    d = _nouveau(client)
    tid = client.post(f"/api/styles/{d['id']}/planche").json()["tache_id"]
    params = taches.lire_tache(conn, tid)["params"]
    meshy = get_meshy(cfg)
    styles.executer_planche(conn, meshy, params, tache_id=tid, attente_s=0)
    styles.executer_planche(conn, meshy, params, tache_id=tid, attente_s=0)  # coupure après le rangement, avant la fin
    detail = client.get(f"/api/styles/{d['id']}").json()
    assert len(detail["planche"]) == 6 and detail["credits_planche"] == 18
    assert meshy.solde()["restants"] == 1000 - 18


# --- I1, I2, I3 · ce qui part à Meshy ------------------------------------------------------------

def test_i1_les_consignes_viennent_de_la_description_du_nouveau_style(client, atelier):
    d = _nouveau(client, description="Château fort, bois sombre et fer forgé.")
    brut = yaml.safe_load((atelier.styles / d["code"] / "style.yaml").read_text(encoding="utf-8"))
    assert all("Château fort, bois sombre et fer forgé" in g for g in brut["prompts_reference"].values())
    assert "Rome" not in str(brut["prompts_reference"]) and "romain" not in str(brut["prompts_reference"])


def test_i2_un_appel_meshy_par_objet(client, conn, cfg):
    d = _nouveau(client, description="Château fort.")
    tid = client.post(f"/api/styles/{d['id']}/planche").json()["tache_id"]
    meshy = MeshyEspion(cfg)
    styles.executer_planche(conn, meshy, taches.lire_tache(conn, tid)["params"], tache_id=tid, attente_s=0)
    objets = ["caisse", "amphore", "lampe", "banc", "casque", "table"]
    assert [a["n"] for a in meshy.appels] == [1] * 6
    assert [a["prompt"].split(",")[0] for a in meshy.appels] == objets
    assert all("Château fort" in a["prompt"] for a in meshy.appels)
    assert [i["objet"] for i in client.get(f"/api/styles/{d['id']}").json()["planche"]] == objets


def test_i3_les_images_d_inspiration_partent_a_meshy(client, conn, cfg, atelier):
    d = _nouveau(client)
    client.post(f"/api/styles/{d['id']}/inspirations", files=[("fichiers", ("ref.png", b"\x89PNG\r\n", "image/png"))])
    tid = client.post(f"/api/styles/{d['id']}/planche").json()["tache_id"]
    meshy = MeshyEspion(cfg)
    styles.executer_planche(conn, meshy, taches.lire_tache(conn, tid)["params"], tache_id=tid, attente_s=0)
    attendu = [str(atelier.styles / d["code"] / "inspiration" / "ref.png")]
    assert all([str(p) for p in a["image"]] == attendu for a in meshy.appels)


# --- I4 · modifier : la base d'abord ---------------------------------------------------------------

def test_i4_modifier_un_yaml_impossible_a_ecrire_laisse_la_base_intacte(client, conn, monkeypatch):
    d = _nouveau(client)

    def echec(*a, **k):
        raise OSError("disque plein")
    monkeypatch.setattr(styles.style_yaml, "ecrire", echec)
    with pytest.raises(OSError):
        styles.modifier(conn, d["id"], {"nom": "Autre nom"})
    assert db.une(conn, "SELECT nom FROM styles WHERE id = ?", (d["id"],))["nom"] == "Médiéval stylisé"


# --- I5 · renommer une couleur ---------------------------------------------------------------------

def test_i5_renommer_une_couleur_les_materiaux_suivent(client):
    pilote = _pilote(client)
    d = client.get(f"/api/styles/{pilote['id']}").json()
    palette = {("Terre rouge" if c["nom"] == "terre_cuite" else c["nom"]): c["hex"] for c in d["palette"]}
    r = client.put(f"/api/styles/{pilote['id']}", json={"palette": palette})
    assert r.status_code == 200, r.text
    d2 = r.json()
    assert d2["palette"][0]["nom"] == "terre_rouge"
    avant = [m["nom"] for m in d["materiaux"] if m["base"] == "terre_cuite"]
    assert avant and [m["nom"] for m in d2["materiaux"] if m["base"] == "terre_rouge"] == avant


def test_i5_retirer_une_couleur_utilisee_dit_quel_materiau(client):
    pilote = _pilote(client)
    d = client.get(f"/api/styles/{pilote['id']}").json()
    palette = {c["nom"]: c["hex"] for c in d["palette"] if c["nom"] != "fer"}
    r = client.put(f"/api/styles/{pilote['id']}", json={"palette": palette})
    assert r.status_code == 422 and "fer" in r.json()["erreur"]


# --- I6 · dupliquer --------------------------------------------------------------------------------

def test_i6_dupliquer_qui_echoue_ne_laisse_rien_et_se_refait(client, conn, atelier, monkeypatch):
    pilote = _pilote(client)
    vrai = styles._inserer
    monkeypatch.setattr(styles, "_inserer", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("panne")))
    with pytest.raises(RuntimeError):
        styles.dupliquer(conn, pilote["id"])
    assert not (atelier.styles / "rome-stylise-v1").exists()
    assert db.une(conn, "SELECT COUNT(*) AS n FROM styles")["n"] == 1
    monkeypatch.setattr(styles, "_inserer", vrai)
    assert client.post(f"/api/styles/{pilote['id']}/versions", json={}).json()["code"] == "rome-stylise-v1"


def test_m2_la_copie_ne_reprend_pas_les_credits(client, cfg):
    d = _nouveau(client)
    client.post(f"/api/styles/{d['id']}/planche")
    _worker_tourne(cfg)
    v1 = client.post(f"/api/styles/{d['id']}/versions", json={}).json()
    assert len(v1["planche"]) == 6 and v1["credits_planche"] == 0
    assert client.get(f"/api/styles/{d['id']}").json()["credits_planche"] == 18


# --- I7 · réimport au démarrage ----------------------------------------------------------------------

def test_i7_reimport_garde_l_etat_et_la_planche(client, conn, cfg, atelier, monkeypatch):
    valide = _nouveau(client, nom="Validé")
    brouillon = _nouveau(client, nom="Brouillon")
    client.post(f"/api/styles/{valide['id']}/planche")
    _worker_tourne(cfg)
    images = client.get(f"/api/styles/{valide['id']}").json()["planche"]
    for i in images[:2]:
        client.put(f"/api/styles/{valide['id']}/planche/{i['id']}", json={"gardee": True})
    client.post(f"/api/styles/{valide['id']}/valider")
    # Nouvelle base, mêmes dossiers de styles (un autre poste, ou atelier.db effacée).
    monkeypatch.setenv("ATELIER_DB", str(atelier.racine / "autre.db"))
    db.initialiser()
    c2 = db.connexion()
    try:
        styles.importer_dossier(c2)
        etats = {r["code"]: r["etat"] for r in db.toutes(c2, "SELECT code, etat FROM styles")}
        assert etats == {"rome-stylise-v0": "valide", valide["code"]: "valide", brouillon["code"]: "brouillon"}
        sid = db.une(c2, "SELECT id FROM styles WHERE code = ?", (valide["code"],))["id"]
        planche = styles.detail(c2, sid)["planche"]
        assert [(i["fichier"], i["objet"], i["gardee"], i["simule"]) for i in planche] == \
            [(i["fichier"], i["objet"], True, True) for i in images[:2]]
    finally:
        c2.close()


def test_m4_import_dans_l_ordre_des_versions(atelier, conn):
    conn.execute("DELETE FROM styles")
    for v in (2, 10, 1):
        brut = yaml.safe_load((atelier.styles / "rome-stylise-v0" / "style.yaml").read_text(encoding="utf-8"))
        brut.update({"style": f"rome-stylise-v{v}", "version": v})
        (atelier.styles / f"rome-stylise-v{v}").mkdir()
        (atelier.styles / f"rome-stylise-v{v}" / "style.yaml").write_text(yaml.safe_dump(brut, allow_unicode=True), encoding="utf-8")
    assert styles.importer_dossier(conn) == [f"rome-stylise-v{v}" for v in (0, 1, 2, 10)]
    parents = {r["code"]: r["parent"] for r in db.toutes(conn, """
        SELECT s.code, p.code AS parent FROM styles s LEFT JOIN styles p ON p.id = s.parent_id""")}
    assert parents == {"rome-stylise-v0": None, "rome-stylise-v1": "rome-stylise-v0",
                       "rome-stylise-v2": "rome-stylise-v1", "rome-stylise-v10": "rome-stylise-v2"}


# --- I8 · tarif exposé par l'adaptateur ---------------------------------------------------------------

def test_i8_estimation_et_202_suivent_le_tarif_de_l_adaptateur(client, monkeypatch):
    e = client.get("/api/styles/estimation-planche").json()
    assert e == {"credits_par_image": 3, "images_max": 6, "simule": True}
    monkeypatch.setattr(MeshySimule, "credits_image", 5)
    assert client.get("/api/styles/estimation-planche").json()["credits_par_image"] == 5
    d = _nouveau(client)
    assert d["images_planche"] == 6
    assert client.post(f"/api/styles/{d['id']}/planche").json()["credits_estimes"] == 30


def test_m13_style_a_la_main_avec_deux_types_deux_images(client, cfg):
    r = client.post("/api/styles", json={
        "nom": "Deux types", "palette": PALETTE, "texel_density": 512,
        "budgets": {"petit_prop": 4000, "prop_moyen": 12000, "grand_prop": 30000, "module_archi": 16000},
        "dimensions_m": {"caisse": [0.6, 0.4, 0.4], "lampe": [0.1, 0.1, 0.3]}})
    sid = r.json()["id"]
    assert r.json()["images_planche"] == 2
    assert client.post(f"/api/styles/{sid}/planche").json()["credits_estimes"] == 6
    _worker_tourne(cfg)
    assert [i["objet"] for i in client.get(f"/api/styles/{sid}").json()["planche"]] == ["caisse", "lampe"]


# --- I9 · Meshy réel : un refus n'est pas relancé, et la planche suit l'API documentée ------------------

def _meshy_reel(monkeypatch, handler):
    monkeypatch.setattr(_commun, "client_http", lambda timeout=None, **kw: httpx.Client(transport=httpx.MockTransport(handler), **kw))
    return reel.MeshyReel({"services": {"meshy": {"mode": "reel", "cle_api": "k-secret", "credits_mensuels": 1000}}})


@pytest.mark.parametrize("code", [400, 401, 402])
def test_i9_refus_meshy_echec_definitif(client, conn, monkeypatch, code):
    d = _nouveau(client)
    tid = client.post(f"/api/styles/{d['id']}/planche").json()["tache_id"]
    meshy = _meshy_reel(monkeypatch, lambda req: httpx.Response(code, json={"message": "refusé"}))
    with pytest.raises(TacheDefinitive) as e:
        styles.executer_planche(conn, meshy, taches.lire_tache(conn, tid)["params"], tache_id=tid, attente_s=0)
    assert f"HTTP {code}" in str(e.value) and "secret" not in str(e.value)


def test_i9_meshy_reel_texte_vers_image_puis_image_vers_image(client, conn, monkeypatch, atelier):
    d = _nouveau(client, description="Château fort.")
    vus = []

    def handler(req: httpx.Request):
        if req.method == "POST":
            vus.append((req.url.path, __import__("json").loads(req.content)))
            return httpx.Response(202, json={"result": f"t{len(vus)}"})
        if req.url.path.startswith("/openapi/v1/"):
            tid = req.url.path.rsplit("/", 1)[1]
            return httpx.Response(200, json={"id": tid, "status": "SUCCEEDED", "progress": 100,
                                             "image_urls": [f"https://assets.meshy.ai/{tid}.png"]})
        return httpx.Response(200, content=b"\x89PNG\r\n")  # pas de champ credits : le tarif fait foi
    meshy = _meshy_reel(monkeypatch, handler)
    tid = client.post(f"/api/styles/{d['id']}/planche").json()["tache_id"]
    styles.executer_planche(conn, meshy, taches.lire_tache(conn, tid)["params"], tache_id=tid, attente_s=0)
    assert {p for p, _ in vus} == {"/openapi/v1/text-to-image"} and len(vus) == 6
    assert vus[0][1]["ai_model"] == "nano-banana" and vus[0][1]["prompt"].startswith("caisse, Château fort")
    detail = client.get(f"/api/styles/{d['id']}").json()
    assert detail["credits_planche"] == 18 and not any(i["simule"] for i in detail["planche"])

    vus.clear()
    client.post(f"/api/styles/{d['id']}/inspirations", files=[("fichiers", ("ref.png", b"\x89PNG\r\n", "image/png"))])
    image = detail["planche"][0]
    tid = client.post(f"/api/styles/{d['id']}/planche/{image['id']}/refaire").json()["tache_id"]
    styles.executer_planche(conn, meshy, taches.lire_tache(conn, tid)["params"], tache_id=tid, attente_s=0)
    assert [p for p, _ in vus] == ["/openapi/v1/image-to-image"]
    assert vus[0][1]["reference_image_urls"][0].startswith("data:image/png;base64,")


# --- échecs Meshy et délai ------------------------------------------------------------------------------

def test_meshy_failed_relance_puis_echec(client, conn, cfg, monkeypatch):
    d = _nouveau(client)
    monkeypatch.setattr(MeshySimule, "etat_tache", lambda self, tid: {"id": tid, "status": "FAILED", "progress": 0,
                                                                      "task_error": {"message": "contenu refusé"}})
    tid = client.post(f"/api/styles/{d['id']}/planche").json()["tache_id"]
    for _ in range(4):  # 1 essai + 3 relances (réglage par défaut)
        _worker_tourne(cfg)
    t = client.get(f"/api/taches/{tid}").json()
    assert t["etat"] == "echouee" and t["tentatives"] == 4 and "contenu refusé" in t["erreur"]


def test_meshy_delai_depasse(client, conn, cfg, monkeypatch):
    d = _nouveau(client)
    monkeypatch.setattr(MeshySimule, "etat_tache", lambda self, tid: {"id": tid, "status": "IN_PROGRESS", "progress": 10})
    tid = client.post(f"/api/styles/{d['id']}/planche").json()["tache_id"]
    with pytest.raises(RuntimeError, match="délai dépassé"):
        styles.executer_planche(conn, get_meshy(cfg), taches.lire_tache(conn, tid)["params"], tache_id=tid,
                                attente_s=0, max_lectures=3)


# --- M1, M7, M12, M15 ------------------------------------------------------------------------------------

def test_m1_garder_apres_validation_met_le_yaml_a_jour(client, cfg, atelier):
    d = _nouveau(client)
    client.post(f"/api/styles/{d['id']}/planche")
    _worker_tourne(cfg)
    images = client.get(f"/api/styles/{d['id']}").json()["planche"]
    client.put(f"/api/styles/{d['id']}/planche/{images[0]['id']}", json={"gardee": True})
    client.post(f"/api/styles/{d['id']}/valider")
    client.put(f"/api/styles/{d['id']}/planche/{images[1]['id']}", json={"gardee": True})
    brut = yaml.safe_load((atelier.styles / d["code"] / "style.yaml").read_text(encoding="utf-8"))
    assert [p["fichier"] for p in brut["planche"]] == [images[0]["fichier"], images[1]["fichier"]]


def test_m7_progression_marquee_simule(client, conn, cfg):
    d = _nouveau(client)
    tid = client.post(f"/api/styles/{d['id']}/planche").json()["tache_id"]
    textes = []
    styles.executer_planche(conn, get_meshy(cfg), taches.lire_tache(conn, tid)["params"], tache_id=tid, attente_s=0,
                            progression=lambda pct, texte="": textes.append(texte))
    assert textes and all("simulé" in t for t in textes)


def test_m12_usage_des_materiaux_pas_invente(client):
    d = client.get(f"/api/styles/{_pilote(client)['id']}").json()
    assert all(m["usage_assets"] is None for m in d["materiaux"])


@pytest.mark.parametrize("champs", [
    {"tolerances": {"dimensions_pct": -5, "texel_pct": 15, "symetrie_m": 0.005, "lod_pct": 10}},
    {"textures_px": {"petit_prop": -512, "prop_moyen": 1024, "grand_prop": 2048, "module_archi": 1024}},
])
def test_m15_valeurs_negatives_refusees(client, champs):
    r = client.put(f"/api/styles/{_pilote(client)['id']}", json=champs)
    assert r.status_code == 422, r.text


# --- routes de la file en HTTP ------------------------------------------------------------------------------

def test_routes_taches_en_http(client, conn, cfg, atelier):
    ecrire_config(atelier.config, lambda c: c["services"]["meshy"].update({"credits_mensuels": 10}))
    d = _nouveau(client)
    tid = client.post(f"/api/styles/{d['id']}/planche").json()["tache_id"]
    assert [t["id"] for t in client.get("/api/taches", params={"file": "meshy"}).json()["taches"]] == [tid]
    assert client.post(f"/api/taches/{tid}/relancer").status_code == 409  # en attente : rien à relancer
    assert client.post(f"/api/taches/{tid}/annuler").json()["etat"] == "annulee"
    assert client.post(f"/api/taches/{tid}/annuler").status_code == 409
    t = client.post(f"/api/taches/{tid}/relancer").json()
    assert t["etat"] == "en_attente" and t["tentatives"] == 0
    from api import config as cfgmod
    _worker_tourne(cfgmod.charger())  # 10 crédits pour 18 : échec définitif
    assert client.get("/api/taches", params={"etat": "echouee"}).json()["taches"][0]["id"] == tid
    assert client.get("/api/taches/999").status_code == 404
    assert client.post("/api/taches/999/annuler").status_code == 404
