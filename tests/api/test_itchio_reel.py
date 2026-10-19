"""Adaptateur itch.io réel : test de butler et de la clé, sans réseau ni butler installé (fakes)."""
from subprocess import CompletedProcess

import httpx
import pytest

from api.adapters import _commun
from api.adapters.itchio import reel


@pytest.fixture
def butler(tmp_path, monkeypatch):
    """Un faux exécutable butler et un `subprocess.run` qui répond « butler version »."""
    exe = tmp_path / "butler"
    exe.write_text("")

    def run(args, **kwargs):
        assert args[0] == str(exe)
        if args[1:] == ["version"]:
            return CompletedProcess(args, 0, stdout="v15.24.0, built on …", stderr="")
        return CompletedProcess(args, 1, stdout="", stderr="inattendu")
    monkeypatch.setattr(reel.subprocess, "run", run)
    return exe


def _cfg(exe, cle="", compte=""):
    return {"services": {"itchio": {"mode": "reel", "cle_api": cle, "compte": compte, "canal": "assets"}},
            "butler": {"chemin": str(exe)}}


def _itchio_repond(monkeypatch, handler):
    monkeypatch.setattr(_commun, "client_http", lambda **kw: httpx.Client(transport=httpx.MockTransport(handler)))


def test_butler_introuvable(tmp_path):
    r = reel.ItchioReel(_cfg(tmp_path / "absent")).tester_butler()
    assert r["ok"] is False and r["etat"] == "Introuvable" and "introuvable" in r["message"]


def test_butler_sans_cle(butler):
    r = reel.ItchioReel(_cfg(butler)).tester_butler()
    assert r["ok"] is False and r["etat"] == "Erreur" and "aucune clé" in r["message"]
    assert r["details"]["version"].startswith("v15")


def test_butler_cle_refusee(butler, monkeypatch):
    _itchio_repond(monkeypatch, lambda req: httpx.Response(401, json={"errors": ["invalid key"]}))
    r = reel.ItchioReel(_cfg(butler, cle="secret-123")).tester_butler()
    assert r["ok"] is False and r["message"] == "clé API itch.io refusée"
    assert "secret" not in str(r)


def test_butler_cle_acceptee_et_compte(butler, monkeypatch):
    vu = {}

    def handler(req: httpx.Request):
        vu["auth"] = req.headers.get("Authorization")
        vu["url"] = str(req.url)
        return httpx.Response(200, json={"user": {"username": "Nohe", "id": 1}})
    _itchio_repond(monkeypatch, handler)
    r = reel.ItchioReel(_cfg(butler, cle="secret-123", compte="nohe")).tester_butler()
    assert r["ok"] is True and r["etat"] == "Connecté" and r["details"]["compte"] == "Nohe"
    assert vu == {"auth": "Bearer secret-123", "url": reel.URL_CLE}

    r = reel.ItchioReel(_cfg(butler, cle="secret-123", compte="autre")).tester_butler()
    assert r["ok"] is False and "autre" in r["message"] and r["details"]["compte_regle"] == "autre"


def test_butler_itchio_injoignable(butler, monkeypatch):
    def handler(req):
        raise httpx.ConnectError("refus", request=req)
    _itchio_repond(monkeypatch, handler)
    r = reel.ItchioReel(_cfg(butler, cle="k")).tester_butler()
    assert r["ok"] is False and "injoignable" in r["message"]
