def test_recherche_fts(client, conn):
    assert client.get("/api/recherche?q=").json() == {"resultats": []}
    conn.execute("INSERT INTO lots(nom, theme, besoin, cree_le, maj_le) VALUES ('Forum romain', 'ROM', 'un marché', 'x', 'x')")
    conn.execute("INSERT INTO assets(id, lot_id, nom, theme, notes, cree_le, maj_le) "
                 "VALUES ('ROM_PROP_Scutum_A', 1, 'Scutum', 'ROM', 'bouclier légionnaire', 'x', 'x')")
    conn.execute("INSERT INTO etiquettes(nom) VALUES ('bouclier')")
    conn.execute("INSERT INTO etiquettes_assets VALUES (1, 'ROM_PROP_Scutum_A')")
    conn.execute("INSERT INTO collections(nom) VALUES ('Armes')")

    r = client.get("/api/recherche?q=scut").json()["resultats"]
    assert r == [{"type": "asset", "id": "ROM_PROP_Scutum_A", "titre": "Scutum", "lien": "/assets/ROM_PROP_Scutum_A"}]
    types = {x["type"] for x in client.get("/api/recherche?q=bouclier").json()["resultats"]}
    assert types == {"asset", "etiquette"}
    assert client.get("/api/recherche?q=forum").json()["resultats"][0]["lien"] == "/lots/1"
    assert client.get("/api/recherche?q=marche").json()["resultats"][0]["type"] == "lot"  # sans accent
    assert client.get("/api/recherche?q=armes").json()["resultats"][0]["lien"] == "/bibliotheque?collection=1"
    assert client.get('/api/recherche?q="(').json()["resultats"] == []

    conn.execute("UPDATE assets SET nom = 'Grand bouclier' WHERE id = 'ROM_PROP_Scutum_A'")
    r = client.get("/api/recherche?q=scutum").json()["resultats"][0]
    assert r["id"] == "ROM_PROP_Scutum_A" and r["titre"] == "Grand bouclier"  # l'id reste indexé, le titre complet
    conn.execute("DELETE FROM assets WHERE id = 'ROM_PROP_Scutum_A'")
    assert client.get("/api/recherche?q=scutum").json()["resultats"] == []
