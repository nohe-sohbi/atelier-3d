"""Connexion SQLite (atelier.db), migrations versionnées et petits helpers.

- WAL, clés étrangères activées, lignes renvoyées comme des dict.
- Les migrations sont les fichiers api/migrations/NNN_nom.sql, appliqués dans l'ordre
  et consignés dans la table `migrations`. Elles sont idempotentes : une version déjà
  consignée n'est pas rejouée.
"""
from __future__ import annotations

import logging
import re
import sqlite3
import threading
import time
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path

from api import chemins

DOSSIER_MIGRATIONS = Path(__file__).resolve().parent / "migrations"
_NOM_MIGRATION = re.compile(r"^(\d{3})_([a-z0-9_]+)\.sql$")
_verrou_migrations = threading.Lock()
log = logging.getLogger("api.db")

#: Copies gardées par motif : les plus anciennes sont supprimées.
SAUVEGARDES_GARDEES = {"avant-migration": 10, "quotidienne": 14}


def maintenant() -> str:
    """Date ISO 8601 UTC, à la seconde."""
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _dict_factory(cursor: sqlite3.Cursor, row: tuple) -> dict:
    return {col[0]: row[i] for i, col in enumerate(cursor.description)}


def connexion(chemin: Path | None = None) -> sqlite3.Connection:
    """Ouvre une connexion (une par thread : ne pas la partager)."""
    chemin = chemin or chemins.chemin_db()
    chemin.parent.mkdir(parents=True, exist_ok=True)
    # check_same_thread=False : FastAPI exécute une dépendance synchrone dans un pool de threads et
    # peut la fermer dans un autre thread que celui qui l'a ouverte. Une connexion ne sert qu'à une
    # requête à la fois : aucun partage concurrent.
    conn = sqlite3.connect(str(chemin), timeout=30, isolation_level=None, check_same_thread=False)
    conn.row_factory = _dict_factory
    _passer_en_wal(conn, delai_s=30)
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA busy_timeout=30000")
    return conn


def _passer_en_wal(conn: sqlite3.Connection, delai_s: float) -> None:
    """PRAGMA journal_mode=WAL, en réessayant tant qu'un autre processus tient la base.

    Pour ce changement de mode, SQLite ne passe pas par le busy_timeout (il éviterait un interblocage) :
    quand l'API et le worker créent la même base neuve au premier lancement, l'un des deux reçoit
    « database is locked » tout de suite.
    """
    limite = time.monotonic() + delai_s
    while True:
        try:
            conn.execute("PRAGMA journal_mode=WAL")
            return
        except sqlite3.OperationalError as e:
            occupee = (getattr(e, "sqlite_errorcode", 0) & 0xFF) == sqlite3.SQLITE_BUSY
            if not occupee or time.monotonic() >= limite:
                raise
            time.sleep(0.05)


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


def dossier_sauvegardes(conn: sqlite3.Connection) -> Path | None:
    """Le dossier `sauvegardes/` à côté de la base ; None pour une base en mémoire."""
    fichier = next((r["file"] for r in conn.execute("PRAGMA database_list").fetchall() if r["name"] == "main"), "")
    return Path(fichier).parent / "sauvegardes" if fichier else None


def sauvegarder_base(conn: sqlite3.Connection, motif: str) -> Path | None:
    """Copie cohérente de la base (API de sauvegarde de SQLite, sûre même en cours d'écriture) dans `sauvegardes/`.

    Le nom dit le motif et la date : `atelier-<motif>-<AAAAMMJJ-HHMMSS>.db`. Seules les copies les plus récentes de
    chaque motif sont gardées. Renvoie None pour une base en mémoire.
    """
    dossier = dossier_sauvegardes(conn)
    if dossier is None:
        return None
    dossier.mkdir(parents=True, exist_ok=True)
    cible = dossier / f"atelier-{motif}-{datetime.now(UTC).strftime('%Y%m%d-%H%M%S')}.db"
    copie = sqlite3.connect(str(cible))
    try:
        conn.backup(copie)
    finally:
        copie.close()
    gardees = SAUVEGARDES_GARDEES.get(motif.split("-v", 1)[0], 10)
    for ancienne in sorted(dossier.glob(f"atelier-{motif.split('-v', 1)[0]}*-*.db"))[:-gardees]:
        ancienne.unlink(missing_ok=True)
    log.info("sauvegarde de la base : %s", cible.name)
    return cible


def sauvegarde_quotidienne(conn: sqlite3.Connection, heures: float = 20.0) -> Path | None:
    """Une sauvegarde `quotidienne` si la dernière a plus de `heures` (le worker l'appelle à chaque lancement et chaque jour)."""
    dossier = dossier_sauvegardes(conn)
    if dossier is None:
        return None
    recentes = [f for f in dossier.glob("atelier-quotidienne-*.db") if time.time() - f.stat().st_mtime < heures * 3600]
    return None if recentes else sauvegarder_base(conn, "quotidienne")


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
        deja = {r["version"] for r in conn.execute("SELECT version FROM migrations").fetchall()}
        en_attente = [v for v, _, _ in lister_migrations() if v not in deja]
        # Une base qui a déjà vécu est copiée avant d'être changée : une migration ratée ne coûte jamais les données.
        if en_attente and deja:
            try:
                sauvegarder_base(conn, "avant-migration-v" + "-".join(str(v) for v in en_attente))
            except sqlite3.OperationalError:
                # Un autre processus migre la même base en ce moment (premier lancement de l'API et du worker) :
                # c'est lui qui la copie ; on n'attend pas son verrou pour rien.
                log.warning("sauvegarde avant migration ignorée : la base est occupée par une autre migration")
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
