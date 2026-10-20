from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from api import db


def _initialiser(chemin: str) -> list[int]:
    """Au niveau du module : indispensable pour le démarrage « spawn » de Windows."""
    conn = db.connexion(Path(chemin))
    try:
        return db.appliquer_migrations(conn)
    finally:
        conn.close()

TABLES = {"styles", "lots", "objets", "essais", "assets", "versions", "collections", "collections_assets",
          "etiquettes", "etiquettes_assets", "generateurs", "regles_routage", "taches", "evenements",
          "couts", "bancs", "publications", "publications_versions", "recherche", "migrations",
          "planche_images", "pieces", "demandes_generateurs", "workers"}


def test_migrations_appliquees_et_idempotentes(atelier, conn):
    assert db.versions_appliquees(conn) == [0, 10, 20, 30, 50]
    assert db.appliquer_migrations(conn) == []
    assert db.versions_appliquees(conn) == [0, 10, 20, 30, 50]
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


def test_initialisation_concurrente(tmp_path):
    """Quatre processus migrent la même base neuve en même temps (API et worker au premier lancement)."""
    chemin = str(tmp_path / "atelier.db")
    with ProcessPoolExecutor(4) as pool:
        resultats = list(pool.map(_initialiser, [chemin] * 4))
    n_migrations = len(list((Path(db.__file__).parent / "migrations").glob("*.sql")))
    # Un seul processus applique toutes les migrations ; les trois autres n'en appliquent aucune.
    assert sorted(len(r) for r in resultats) == [0, 0, 0, n_migrations], resultats
    conn = db.connexion(Path(chemin))
    try:
        assert db.versions_appliquees(conn) == [v for v, _, _ in db.lister_migrations()]
        assert conn.execute("SELECT COUNT(*) AS n FROM migrations").fetchone()["n"] == n_migrations
    finally:
        conn.close()


def test_fts5_present(conn):
    db.verifier_fts5(conn)


def test_connexion_utilisable_depuis_un_autre_thread(atelier):
    """FastAPI ouvre et ferme la connexion d'une requête dans des threads différents."""
    import threading

    conn = db.connexion()
    erreurs = []

    def fermer():
        try:
            conn.execute("SELECT 1").fetchone()
            conn.close()
        except Exception as e:  # noqa: BLE001
            erreurs.append(e)
    t = threading.Thread(target=fermer)
    t.start()
    t.join()
    assert erreurs == []
