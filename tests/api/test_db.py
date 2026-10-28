import sqlite3
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
    assert db.versions_appliquees(conn) == [0, 10, 20, 30, 50, 60]
    assert db.appliquer_migrations(conn) == []
    assert db.versions_appliquees(conn) == [0, 10, 20, 30, 50, 60]
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


def _sauvegardes(atelier):
    return sorted((atelier.db.parent / "sauvegardes").glob("*.db")) if (atelier.db.parent / "sauvegardes").exists() else []


def test_une_base_neuve_n_est_pas_sauvegardee_avant_sa_premiere_migration(atelier):
    assert _sauvegardes(atelier) == []


def test_une_migration_en_attente_copie_la_base_avant_de_la_changer(atelier, conn, monkeypatch, tmp_path):
    conn.execute("INSERT INTO lots(nom, theme, etat, cree_le, maj_le) VALUES ('Précieux', 'T', 'brouillon', 'x', 'x')")
    nouvelle = tmp_path / "migrations"
    nouvelle.mkdir()
    for v, nom, f in db.lister_migrations():
        (nouvelle / f.name).write_text(f.read_text(encoding="utf-8"), encoding="utf-8")
    (nouvelle / "999_essai.sql").write_text("CREATE TABLE IF NOT EXISTS essai_sauvegarde (id INTEGER PRIMARY KEY);", encoding="utf-8")
    monkeypatch.setattr(db, "DOSSIER_MIGRATIONS", nouvelle)
    assert db.appliquer_migrations(conn) == [999]
    copies = _sauvegardes(atelier)
    assert [c.name.split("-v")[0] for c in copies] == ["atelier-avant-migration"] and copies[0].name.split("-v")[1].startswith("999-")
    # La copie est lisible et contient les données d'avant la migration, sans la nouvelle table.
    c = sqlite3.connect(str(copies[0]))
    try:
        assert c.execute("SELECT nom FROM lots").fetchone()[0] == "Précieux"
        assert c.execute("SELECT 1 FROM sqlite_master WHERE name = 'essai_sauvegarde'").fetchone() is None
    finally:
        c.close()
    assert db.appliquer_migrations(conn) == []
    assert len(_sauvegardes(atelier)) == 1  # rien d'en attente : pas de nouvelle copie


def test_la_sauvegarde_quotidienne_n_est_faite_qu_une_fois_par_jour_et_les_anciennes_sont_effacees(atelier, conn):
    premiere = db.sauvegarde_quotidienne(conn)
    assert premiere is not None and premiere.parent == atelier.db.parent / "sauvegardes"
    assert db.sauvegarde_quotidienne(conn) is None  # déjà une copie de moins de 20 h
    # Les anciennes copies sont supprimées au-delà du nombre gardé.
    dossier = premiere.parent
    for i in range(20):
        (dossier / f"atelier-quotidienne-20200101-0000{i:02d}.db").write_bytes(b"")
    db.sauvegarder_base(conn, "quotidienne")
    assert len(list(dossier.glob("atelier-quotidienne-*.db"))) == db.SAUVEGARDES_GARDEES["quotidienne"]


def test_le_worker_fait_la_sauvegarde_quotidienne(atelier, conn):
    from worker.periodiques import Periodiques

    faits = Periodiques().tour(conn, forcer=True)
    assert "sauvegarde_quotidienne" in faits and any("quotidienne" in c.name for c in _sauvegardes(atelier))
