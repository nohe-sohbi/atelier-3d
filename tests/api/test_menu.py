from api.adapters import get_meshy


def test_menu_vide(client):
    j = client.get("/api/menu").json()
    assert j["badges"] == {"lots": 0, "bibliotheque": 0, "generateurs": 0}
    assert j["collections"] == []
    assert j["credits"] == {"utilises": 0, "total": 1000, "restants": 1000, "mode": "simule",
                            "renouvellement": j["credits"]["renouvellement"]}
    assert j["credits"]["renouvellement"].startswith("Renouvelés le 1er ")


def test_menu_depuis_la_base(client, conn, cfg):
    conn.execute("INSERT INTO lots(nom, theme, etat, cree_le, maj_le) VALUES ('A', 'ROM', 'en_cours', 'x', 'x')")
    conn.execute("INSERT INTO lots(nom, theme, etat, cree_le, maj_le) VALUES ('B', 'ROM', 'termine', 'x', 'x')")
    conn.execute("INSERT INTO assets(id, nom, theme, statut, cree_le, maj_le) VALUES ('ROM_PROP_Scutum_A', 'Scutum', 'ROM', 'garde', 'x', 'x')")
    conn.execute("INSERT INTO assets(id, nom, theme, statut, cree_le, maj_le) VALUES ('ROM_PROP_Pilum_A', 'Pilum', 'ROM', 'revue', 'x', 'x')")
    conn.execute("INSERT INTO bancs(nom, generateur_a, generateur_b, etat, cree_le) VALUES ('b', 'x', 'y', 'termine', 'x')")
    conn.execute("INSERT INTO collections(nom, couleur, epinglee) VALUES ('Armes', '#112233', 1)")
    conn.execute("INSERT INTO collections(nom, couleur, epinglee) VALUES ('Brouillon', '#000000', 0)")
    conn.execute("INSERT INTO collections_assets VALUES (1, 'ROM_PROP_Scutum_A')")
    get_meshy(cfg).image_vers_3d("reference.png")  # 30 crédits simulés, même source que le menu
    j = client.get("/api/menu").json()
    assert j["badges"] == {"lots": 1, "bibliotheque": 1, "generateurs": 1}
    assert j["collections"] == [{"id": 1, "nom": "Armes", "couleur": "#112233", "nombre": 1}]
    assert j["credits"]["utilises"] == 30 and j["credits"]["restants"] == 970
