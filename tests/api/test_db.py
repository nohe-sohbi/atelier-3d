from api import db

TABLES = {"styles", "lots", "objets", "essais", "assets", "versions", "collections", "collections_assets",
          "etiquettes", "etiquettes_assets", "generateurs", "regles_routage", "taches", "evenements",
          "couts", "bancs", "publications", "publications_versions", "recherche", "migrations"}


def test_migrations_appliquees_et_idempotentes(atelier, conn):
    assert db.versions_appliquees(conn) == [0]
    assert db.appliquer_migrations(conn) == []
    assert db.versions_appliquees(conn) == [0]
    noms = {r["name"] for r in conn.execute("SELECT name FROM sqlite_master WHERE type IN ('table')")}
    assert TABLES <= noms
    assert conn.execute("PRAGMA foreign_keys").fetchone()["foreign_keys"] == 1
    assert conn.execute("PRAGMA journal_mode").fetchone()["journal_mode"] == "wal"


def test_migration_consignee(conn):
    r = db.une(conn, "SELECT * FROM migrations WHERE version = 0")
    assert r["nom"] == "socle" and r["applique_le"].endswith("Z")


def test_cles_etrangeres(conn):
    import sqlite3

    import pytest

    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("INSERT INTO objets(lot_id, nom) VALUES (999, 'x')")
