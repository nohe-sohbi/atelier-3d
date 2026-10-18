"""Mode production : l'API sert web/dist/ avec repli SPA ; /api reste en JSON ; pas de traversée."""
from fastapi.testclient import TestClient


def test_repli_spa(atelier, monkeypatch, tmp_path):
    dist = tmp_path / "dist"
    (dist / "statique").mkdir(parents=True)
    (dist / "index.html").write_text("<!doctype html><title>Atelier 3D</title>", encoding="utf-8")
    (dist / "statique" / "app.js").write_text("console.log(1)", encoding="utf-8")
    monkeypatch.setenv("ATELIER_WEB_DIST", str(dist))
    from api.main import create_app

    with TestClient(create_app()) as client:
        assert client.get("/").text.startswith("<!doctype html>")
        assert client.get("/styles").text.startswith("<!doctype html>")  # route React : index.html
        assert client.get("/statique/app.js").text == "console.log(1)"
        assert client.get("/api").json() == {"erreur": "Not Found", "detail": None}
        assert client.get("/api/nexistepas").json() == {"erreur": "Not Found", "detail": None}
        assert client.get("/api/sante").json()["statut"] == "ok"
        assert client.get("/sante").json()["statut"] == "ok"
        assert client.get("/../pyproject.toml").status_code in (200, 404)
        assert "[project]" not in client.get("/..%2Fpyproject.toml").text
