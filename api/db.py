"""Connexion SQLite (atelier.db), migrations versionnées et petits helpers.

- WAL, clés étrangères activées, lignes renvoyées comme des dict.
- Les migrations sont les fichiers api/migrations/NNN_nom.sql, appliqués dans l'ordre
  et consignés dans la table `migrations`. Elles sont idempotentes : une version déjà
  consignée n'est pas rejouée.
"""
from __future__ import annotations

import re
import sqlite3
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path

from api import chemins

DOSSIER_MIGRATIONS = Path(__file__).resolve().parent / "migrations"
_NOM_MIGRATION = re.compile(r"^(\d{3})_([a-z0-9_]+)\.sql$")
_verrou_migrations = threading.Lock()


def maintenant() -> str:
    """Date ISO 8601 UTC, à la seconde."""
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _dict_factory(cursor: sqlite3.Cursor, row: tuple) -> dict:
    return {col[0]: row[i] for i, col in enumerate(cursor.description)}


def connexion(chemin: Path | None = None) -> sqlite3.Connection:
    """Ouvre une connexion (une par thread : ne pas la partager)."""
    chemin = chemin or chemins.chemin_db()
    chemin.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(chemin), timeout=30, isolation_level=None)
    conn.row_factory = _dict_factory
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA busy_timeout=30000")
    return conn


@contextmanager
def transaction(conn: sqlite3.Connection) -> Iterator[sqlite3.Connection]:
    """BEGIN IMMEDIATE … COMMIT (ROLLBACK si exception)."""
    conn.execute("BEGIN IMMEDIATE")
    try:
        yield conn
    except BaseException:
        conn.execute("ROLLBACK")
        raise
    else:
        conn.execute("COMMIT")


def lister_migrations() -> list[tuple[int, str, Path]]:
    out = []
    for f in sorted(DOSSIER_MIGRATIONS.glob("*.sql")):
        m = _NOM_MIGRATION.match(f.name)
        if not m:
            raise ValueError(f"nom de migration invalide : {f.name} (attendu NNN_nom.sql)")
        out.append((int(m.group(1)), m.group(2), f))
    return out


class FTS5Absent(RuntimeError):
    """Le SQLite de cette machine n'a pas FTS5 : la recherche globale ne peut pas être créée."""


def verifier_fts5(conn: sqlite3.Connection) -> None:
    r = conn.execute("SELECT sqlite_compileoption_used('ENABLE_FTS5') AS fts5").fetchone()
    if not r or not r["fts5"]:
        raise FTS5Absent(
            f"SQLite {sqlite3.sqlite_version} sans FTS5 : la recherche globale ne peut pas être créée. "
            "Utilise un Python 3.12 de python.org (Windows) ou le paquet sqlite3 de ta distribution.")


def appliquer_migrations(conn: sqlite3.Connection) -> list[int]:
    """Applique les migrations manquantes ; renvoie les versions appliquées.

    Sûr quand deux processus démarrent en même temps : la vérification « déjà appliquée » se fait
    DANS la transaction BEGIN IMMEDIATE (verrou d'écriture), donc le second attend puis constate que
    la version est consignée et passe. Le verrou de thread couvre les threads d'un même processus.
    """
    verifier_fts5(conn)
    with _verrou_migrations:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS migrations ("
            " version INTEGER PRIMARY KEY, nom TEXT NOT NULL, applique_le TEXT NOT NULL)"
        )
        appliquees = []
        for version, nom, fichier in lister_migrations():
            conn.execute("BEGIN IMMEDIATE")
            try:
                if conn.execute("SELECT 1 FROM migrations WHERE version = ?", (version,)).fetchone():
                    conn.execute("ROLLBACK")
                    continue
                _executer_script(conn, fichier.read_text(encoding="utf-8"))
                conn.execute(
                    "INSERT INTO migrations(version, nom, applique_le) VALUES (?, ?, ?)",
                    (version, nom, maintenant()),
                )
            except BaseException:
                conn.execute("ROLLBACK")
                raise
            conn.execute("COMMIT")
            appliquees.append(version)
        return appliquees


def _executer_script(conn: sqlite3.Connection, sql: str) -> None:
    """Exécute un script SQL instruction par instruction, dans la transaction courante.

    (sqlite3.executescript ferait un COMMIT implicite avant de commencer.)
    """
    for instruction in _decouper(sql):
        conn.execute(instruction)


def _decouper(sql: str) -> list[str]:
    """Découpe un script en instructions complètes (gère les triggers BEGIN … END)."""
    instructions, courant = [], ""
    for ligne in sql.splitlines():
        if ligne.strip().startswith("--"):
            continue
        courant += ligne + "\n"
        if sqlite3.complete_statement(courant):
            if courant.strip():
                instructions.append(courant.strip())
            courant = ""
    if courant.strip():
        instructions.append(courant.strip())
    return instructions


def versions_appliquees(conn: sqlite3.Connection) -> list[int]:
    return [r["version"] for r in conn.execute("SELECT version FROM migrations ORDER BY version")]


def initialiser(chemin: Path | None = None) -> None:
    """Crée la base et applique les migrations (au démarrage de l'API et du worker)."""
    conn = connexion(chemin)
    try:
        appliquer_migrations(conn)
    finally:
        conn.close()


def une(conn: sqlite3.Connection, sql: str, params: tuple = ()) -> dict | None:
    return conn.execute(sql, params).fetchone()


def toutes(conn: sqlite3.Connection, sql: str, params: tuple = ()) -> list[dict]:
    return conn.execute(sql, params).fetchall()


def inserer(conn: sqlite3.Connection, table: str, valeurs: dict) -> int:
    cols = ", ".join(valeurs)
    marques = ", ".join("?" for _ in valeurs)
    cur = conn.execute(f"INSERT INTO {table} ({cols}) VALUES ({marques})", tuple(valeurs.values()))
    return int(cur.lastrowid)
