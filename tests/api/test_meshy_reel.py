"""Adaptateur Meshy réel : solde et test de connexion sans réseau (transport simulé), cache du solde."""
import httpx

from api.adapters import _commun
from api.adapters.meshy import reel
from api.services import credits


def _meshy_repond(monkeypatch, handler):
    monkeypatch.setattr(_commun, "client_http", lambda timeout=None, **kw: httpx.Client(transport=httpx.MockTransport(handler), **kw))


def _cfg(cle="k-secret"):
    return {"services": {"meshy": {"mode": "reel", "cle_api": cle, "credits_mensuels": 1000}}}


def test_solde_et_test_de_connexion(monkeypatch):
    vu = {}

    def handler(req: httpx.Request):
        vu["auth"] = req.headers.get("Authorization")
        vu["url"] = str(req.url)
        return httpx.Response(200, json={"balance": 574})
    _meshy_repond(monkeypatch, handler)
    m = reel.MeshyReel(_cfg())
    assert m.solde() == {"restants": 574, "total": 1000}
    assert vu == {"auth": "Bearer k-secret", "url": "https://api.meshy.ai/openapi/v1/balance"}
    assert m.tester_connexion()["etat"] == "Connecté"


def test_cle_refusee_sans_fuite(monkeypatch):
    _meshy_repond(monkeypatch, lambda req: httpx.Response(401, json={"message": "invalid"}))
    r = reel.MeshyReel(_cfg()).tester_connexion()
    assert r["ok"] is False and "HTTP 401" in r["message"] and "secret" not in str(r)
    assert reel.MeshyReel(_cfg(cle="")).tester_connexion()["message"].startswith("Meshy : RuntimeError")


def test_solde_en_cache_une_minute_en_mode_reel(monkeypatch, conn, cfg):
    appels = {"n": 0}

    def handler(req: httpx.Request):
        appels["n"] += 1
        return httpx.Response(200, json={"balance": 500})
    _meshy_repond(monkeypatch, handler)
    credits.oublier_cache()
    cfg["services"]["meshy"].update({"mode": "reel", "cle_api": "k-secret"})
    assert credits.solde_meshy(conn, cfg) == {"restants": 500, "total": 1000, "utilises": 500, "mode": "reel"}
    assert credits.solde_meshy(conn, cfg)["restants"] == 500 and appels["n"] == 1  # servi par le cache
    cfg["services"]["meshy"]["cle_api"] = "autre-cle"
    credits.solde_meshy(conn, cfg)
    assert appels["n"] == 2  # autre clé : relu
    credits.oublier_cache()
