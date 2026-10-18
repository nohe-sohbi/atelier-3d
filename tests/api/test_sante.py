def test_sante(client):
    r = client.get("/api/sante")
    assert r.status_code == 200
    j = r.json()
    assert j["statut"] == "ok" and j["version"] == "0.1.0" and j["db"] == "ok"
    assert isinstance(j["blender"], bool)


def test_route_inconnue_en_json(client):
    r = client.get("/api/nexistepas")
    assert r.status_code == 404
    assert "erreur" in r.json()
