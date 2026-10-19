def test_sante(client):
    r = client.get("/api/sante")
    assert r.status_code == 200
    j = r.json()
    assert j["statut"] == "ok" and j["version"] == "0.1.0" and j["db"] == "ok"
    assert isinstance(j["blender"], bool)


def test_sante_aussi_hors_de_api(client):
    """Le plan demande « une route /sante qui répond ok »."""
    assert client.get("/sante").json()["statut"] == "ok"


def test_route_inconnue_en_json(client):
    r = client.get("/api/nexistepas")
    assert r.status_code == 404
    assert r.json() == {"erreur": "Not Found", "detail": None}


def test_methode_refusee_en_json(client):
    r = client.post("/api/sante")
    assert r.status_code == 405
    assert r.json() == {"erreur": "Method Not Allowed", "detail": None}
