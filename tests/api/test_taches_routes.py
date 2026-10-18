from api.services import taches


def test_routes_taches(client, conn, cfg):
    assert client.get("/api/taches").json() == {"taches": []}
    assert client.get("/api/taches/1").status_code == 404
    conn.execute("INSERT INTO lots(nom, theme, cree_le, maj_le) VALUES ('L', 'ROM', 'x', 'x')")
    t1 = taches.creer_tache(conn, "attendre", "api", {"secondes": 0}, lot_id=1, cfg=cfg)
    t2 = taches.creer_tache(conn, "attendre", "gpu", {}, cfg=cfg)

    j = client.get("/api/taches").json()["taches"]
    assert [t["id"] for t in j] == [t2, t1] and j[1]["params"] == {"secondes": 0}
    assert [t["id"] for t in client.get("/api/taches?lot_id=1").json()["taches"]] == [t1]
    assert [t["id"] for t in client.get("/api/taches?etat=en_attente&file=gpu").json()["taches"]] == [t2]
    assert client.get("/api/taches?etat=bidon").status_code == 422

    assert client.post(f"/api/taches/{t1}/relancer").status_code == 409  # pas échouée
    assert client.post(f"/api/taches/{t1}/annuler").json()["etat"] == "annulee"
    assert client.post(f"/api/taches/{t1}/annuler").status_code == 409
    assert client.post(f"/api/taches/{t1}/relancer").json()["etat"] == "en_attente"
    assert client.get(f"/api/taches/{t1}").json()["tentatives"] == 0
    assert client.post("/api/taches/999/annuler").status_code == 404
