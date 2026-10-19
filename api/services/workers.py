"""Battement du worker : il note qu'il tourne toutes les quelques secondes ; l'API sait dire s'il est arrêté.

Sans ce battement, une tâche « en attente » ne dit pas si le worker est simplement occupé ou s'il ne tourne pas.
"""
from __future__ import annotations

import sqlite3
from datetime import UTC, datetime, timedelta

from api import db

BATTEMENT_S = 5.0
PERIME_S = 30


def battre(conn: sqlite3.Connection, verrou: str, hote: str = "", pid: int | None = None) -> None:
    maintenant = db.maintenant()
    conn.execute("""INSERT INTO workers(verrou, hote, pid, demarre_le, battu_le) VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(verrou) DO UPDATE SET battu_le = excluded.battu_le, arrete_le = NULL""",
                 (verrou, hote, pid, maintenant, maintenant))


def arreter(conn: sqlite3.Connection, verrou: str) -> None:
    conn.execute("UPDATE workers SET arrete_le = ? WHERE verrou = ?", (db.maintenant(), verrou))


def etat(conn: sqlite3.Connection) -> dict:
    """{"actif", "battu_le", "demarre_le", "en_cours", "en_attente"} : le worker le plus récent et la file."""
    w = db.une(conn, "SELECT * FROM workers ORDER BY battu_le DESC LIMIT 1")
    limite = (datetime.now(UTC) - timedelta(seconds=PERIME_S)).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    actif = bool(w and w["arrete_le"] is None and w["battu_le"] >= limite)
    files = db.une(conn, """SELECT COUNT(CASE WHEN etat = 'en_cours' THEN 1 END) AS en_cours,
                                   COUNT(CASE WHEN etat = 'en_attente' THEN 1 END) AS en_attente FROM taches""")
    return {"actif": actif, "battu_le": w["battu_le"] if w else None, "demarre_le": w["demarre_le"] if w else None,
            "arrete_le": w["arrete_le"] if w else None, "en_cours": int(files["en_cours"]),
            "en_attente": int(files["en_attente"])}
