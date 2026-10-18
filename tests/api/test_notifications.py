from api.services import evenements


def test_notifications(client, conn):
    assert client.get("/api/notifications").json() == {"notifications": [], "non_lues": 0}
    evenements.ecrire(conn, "tache_creee", "pas une notification", niveau="debug")
    n1 = evenements.ecrire(conn, evenements.REVUE_PRETE, "Revue prête", "4 objets", lien="/lots/1/revue")
    n2 = evenements.ecrire(conn, "info_forcee", "Forcée", notification=True)
    j = client.get("/api/notifications").json()
    assert [n["id"] for n in j["notifications"]] == [n2, n1]
    assert j["non_lues"] == 2
    assert set(j["notifications"][1]) == {"id", "date", "type", "niveau", "titre", "texte", "lien", "lu"}
    assert j["notifications"][1]["lien"] == "/lots/1/revue" and j["notifications"][1]["lu"] is False

    assert client.post(f"/api/notifications/{n1}/lu").json() == {"ok": True, "id": n1}
    assert client.get("/api/notifications").json()["non_lues"] == 1
    assert client.post("/api/notifications/999/lu").status_code == 404
    assert client.post("/api/notifications/tout-lu").json() == {"ok": True, "marquees": 1}
    assert client.get("/api/notifications").json()["non_lues"] == 0

