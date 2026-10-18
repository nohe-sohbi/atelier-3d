import copy

import yaml

from api import config as cfgmod

CLES_SERVICES = {"meshy", "claude", "comfyui", "itchio"}


def _cles_en_clair(obj) -> list:
    """Toute clé nommée exactement cle_api dans la réponse."""
    if isinstance(obj, dict):
        return [k for k in obj if k == "cle_api"] + [c for v in obj.values() for c in _cles_en_clair(v)]
    if isinstance(obj, list):
        return [c for v in obj for c in _cles_en_clair(v)]
    return []


def _base(client):
    r = client.get("/api/reglages")
    assert r.status_code == 200
    j = r.json()
    j.pop("etat")
    return j


def test_get_structure(client):
    j = client.get("/api/reglages").json()
    assert set(j["services"]) == CLES_SERVICES
    m = j["services"]["meshy"]
    assert m == {"mode": "simule", "cle_api_definie": False, "cle_api_apercu": "", "credits_mensuels": 1000,
                 "renouvellement_jour": 1, "alerte_pct": 80}
    assert j["services"]["claude"]["modele"] == "claude-sonnet-5-5"
    assert j["services"]["claude"]["plafond_mensuel_usd"] == 5.0
    assert j["services"]["comfyui"] == {"mode": "simule", "url": "http://127.0.0.1:8188"}
    assert j["services"]["itchio"]["canal"] == "assets"
    assert set(j["outils"]) == {"blender", "gltf_validator", "butler"}
    assert j["bibliotheque"] == {"dossier": "assets", "purge_rejets_jours": 30}
    assert j["files"] == {"gpu": 1, "meshy": 3, "blender": 2, "relances_max": 3}
    assert j["notifications"] == {"app": True, "bureau": False}
    assert j["etat"]["meshy_solde"] == {"restants": 1000, "total": 1000, "utilises": 0, "mode": "simule"}
    assert j["etat"]["claude_depense_mois"] is None  # suivi des coûts : étape 4
    assert not _cles_en_clair(j)


def test_put_masque_les_cles(client, atelier):
    corps = _base(client)
    corps["services"]["meshy"]["cle_api"] = "msy-secret-ab12"
    corps["services"]["claude"]["cle_api"] = "sk-ant-secret-zz99"
    r = client.put("/api/reglages", json=corps)
    assert r.status_code == 200, r.text
    j = r.json()
    attendu = {k: v for k, v in corps["services"]["meshy"].items() if k != "cle_api"}
    assert j["services"]["meshy"] == {**attendu, "cle_api_definie": True, "cle_api_apercu": "••••ab12"}
    assert not _cles_en_clair(j)
    assert "secret" not in r.text
    assert j["services"]["claude"]["cle_api_apercu"] == "••••zz99"
    local = yaml.safe_load(atelier.config.read_text(encoding="utf-8"))
    assert local["services"]["meshy"]["cle_api"] == "msy-secret-ab12"
    assert "secret" not in client.get("/api/reglages").text


def test_put_cle_absente_ou_vide_inchangee_null_efface(client, atelier):
    corps = _base(client)
    corps["services"]["itchio"]["cle_api"] = "itch-1234"
    client.put("/api/reglages", json=corps)

    sans = copy.deepcopy(corps)
    sans["services"]["itchio"].pop("cle_api")
    assert client.put("/api/reglages", json=sans).json()["services"]["itchio"]["cle_api_definie"] is True

    vide = copy.deepcopy(corps)
    vide["services"]["itchio"]["cle_api"] = ""
    assert client.put("/api/reglages", json=vide).json()["services"]["itchio"]["cle_api_definie"] is True
    assert yaml.safe_load(atelier.config.read_text())["services"]["itchio"]["cle_api"] == "itch-1234"

    nul = copy.deepcopy(corps)
    nul["services"]["itchio"]["cle_api"] = None
    j = client.put("/api/reglages", json=nul).json()["services"]["itchio"]
    assert j["cle_api_definie"] is False and j["cle_api_apercu"] == ""
    assert yaml.safe_load(atelier.config.read_text())["services"]["itchio"]["cle_api"] == ""


def test_put_valeurs_conservees_et_relues(client, atelier):
    corps = _base(client)
    corps["services"]["meshy"].update({"renouvellement_jour": 15, "alerte_pct": 90, "credits_mensuels": 2000})
    corps["services"]["claude"].update({"modele": "claude-haiku-5-5", "plafond_mensuel_usd": 2.5, "mode": "reel"})
    corps["files"].update({"gpu": 1, "meshy": 5, "blender": 1, "relances_max": 1})
    corps["notifications"]["bureau"] = True
    corps["outils"]["blender"]["chemin"] = "/opt/blender/blender"
    corps["bibliotheque"]["purge_rejets_jours"] = 7
    assert client.put("/api/reglages", json=corps).status_code == 200
    j = client.get("/api/reglages").json()
    for section in ("services", "files", "notifications", "outils", "bibliotheque"):
        attendu = copy.deepcopy(corps[section])
        for s in attendu.values() if section == "services" else []:
            s.pop("cle_api", None)
        assert {k: {kk: vv for kk, vv in v.items() if not kk.startswith("cle_api")} for k, v in j[section].items()} \
            == {k: {kk: vv for kk, vv in v.items() if not kk.startswith("cle_api")} for k, v in attendu.items()} \
            if section == "services" else j[section] == attendu
    # Le reste de l'app relit la config : limites de files et relances.
    cfg = cfgmod.charger()
    assert cfgmod.limites_files(cfg) == {"gpu": 1, "meshy": 5, "blender": 1, "api": 4}
    assert cfgmod.relances_max(cfg) == 1


def test_put_validation_422(client):
    corps = _base(client)
    cas = [
        lambda c: c["services"]["meshy"].update(renouvellement_jour=7),
        lambda c: c["services"]["meshy"].update(alerte_pct=50),
        lambda c: c["services"]["claude"].update(modele="gpt-9"),
        lambda c: c["services"]["claude"].update(mode="peut-etre"),
        lambda c: c["services"]["comfyui"].update(url="pas une url"),
        lambda c: c["services"]["itchio"].update(canal=""),
        lambda c: c["files"].update(gpu=0),
        lambda c: c["files"].update(relances_max=9),
        lambda c: c["bibliotheque"].update(purge_rejets_jours=-1),
        lambda c: c.pop("files"),
    ]
    for modif in cas:
        c = copy.deepcopy(corps)
        modif(c)
        r = client.put("/api/reglages", json=c)
        assert r.status_code == 422, (modif, r.text)
        assert r.json()["erreur"] == "Valeurs invalides"
    # Rien n'a été écrit entre-temps.
    assert client.get("/api/reglages").json()["files"] == corps["files"]


def test_tester_services_simules(client):
    attendus = {"meshy": "Connecté", "claude": "Connecté", "comfyui": "Joignable", "itchio": "Connecté",
                "butler": "Connecté"}
    for service, etat in attendus.items():
        j = client.post(f"/api/reglages/tester/{service}").json()
        assert j["ok"] is True and j["etat"] == etat, (service, j)
        assert j["message"] and isinstance(j["details"], dict)
    assert client.post("/api/reglages/tester/meshy").json()["details"]["solde"] == {"restants": 1000, "total": 1000}
    assert "claude-sonnet-5-5" in client.post("/api/reglages/tester/claude").json()["details"]["modeles"]
    assert client.post("/api/reglages/tester/comfyui").json()["details"]["vram_total_mo"] > 0
    assert client.post("/api/reglages/tester/inconnu").status_code == 422


def test_tester_blender_sans_chemin(client):
    j = client.post("/api/reglages/tester/blender").json()
    assert j["ok"] is False and j["etat"] == "Introuvable" and "suggestion" in j["details"]
    assert client.get("/api/sante").json()["blender"] is False
    etat = client.get("/api/reglages").json()["etat"]["outils"]
    assert set(etat) == {"blender", "gltf_validator", "butler", "git_lfs"}
    assert etat["blender"]["present"] is False and "suggestion" in etat["blender"]


def test_tester_gltf_validator_introuvable(client):
    corps = _base(client)
    corps["outils"]["gltf_validator"]["chemin"] = "/chemin/qui/nexiste/pas"
    client.put("/api/reglages", json=corps)
    j = client.post("/api/reglages/tester/gltf_validator").json()
    assert j["ok"] is False and j["etat"] == "Introuvable" and "introuvable" in j["message"]


def test_reel_sans_cle_ne_casse_pas_la_route(client, conn):
    corps = _base(client)
    corps["services"]["meshy"]["mode"] = "reel"
    j = client.put("/api/reglages", json=corps).json()
    assert j["etat"]["meshy_solde"] is None
    assert client.post("/api/reglages/tester/meshy").json()["ok"] is False
    assert conn.execute("SELECT 1 FROM evenements WHERE type = 'meshy_injoignable'").fetchall()
    assert client.get("/api/menu").json()["credits"] is None  # même source que la jauge du menu
