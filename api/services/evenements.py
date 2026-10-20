"""Journal d'événements (table evenements) et notifications.

Chaque changement d'état de la file, chaque alerte, écrit ici. `notification=1` marque les
types qui remontent dans la cloche : références prêtes, revue prête, échec après N relances, banc terminé,
crédits à 80 %.
"""
from __future__ import annotations

import sqlite3
from datetime import UTC, datetime, timedelta

from api import db

# Types d'événements qui deviennent des notifications.
REVUE_PRETE = "revue_prete"
REFERENCES_PRETES = "references_pretes"
TACHE_ECHEC_FINAL = "tache_echec_final"
BANC_TERMINE = "banc_termine"
CREDITS_ALERTE = "credits_alerte"
TYPES_NOTIFIES = frozenset({REFERENCES_PRETES, REVUE_PRETE, TACHE_ECHEC_FINAL, BANC_TERMINE, CREDITS_ALERTE})

NIVEAUX = ("debug", "info", "succes", "alerte", "erreur")


def ecrire(
    conn: sqlite3.Connection,
    type: str,
    titre: str,
    texte: str = "",
    *,
    niveau: str = "info",
    lien: str | None = None,
    lot_id: int | None = None,
    objet_id: int | None = None,
    tache_id: int | None = None,
    notification: bool | None = None,
) -> int:
    """Écrit un événement ; renvoie son id. `notification` par défaut selon le type."""
    if niveau not in NIVEAUX:
        raise ValueError(f"niveau inconnu : {niveau}")
    if notification is None:
        notification = type in TYPES_NOTIFIES
    return db.inserer(conn, "evenements", {
        "date": db.maintenant(), "type": type, "niveau": niveau, "titre": titre,
        "texte": texte or "", "lien": lien, "lot_id": lot_id, "objet_id": objet_id,
        "tache_id": tache_id, "notification": 1 if notification else 0, "lu": 0,
    })


def recent_existe(conn: sqlite3.Connection, type: str, minutes: int = 10, titre: str | None = None) -> bool:
    """Vrai si un événement du même type (et titre) a été écrit dans les N dernières minutes."""
    depuis = (datetime.now(UTC) - timedelta(minutes=minutes)).replace(microsecond=0)
    depuis_iso = depuis.isoformat().replace("+00:00", "Z")
    if titre is None:
        r = db.une(conn, "SELECT 1 AS x FROM evenements WHERE type=? AND date>=? LIMIT 1", (type, depuis_iso))
    else:
        r = db.une(conn, "SELECT 1 AS x FROM evenements WHERE type=? AND titre=? AND date>=? LIMIT 1",
                   (type, titre, depuis_iso))
    return r is not None


def lister(conn: sqlite3.Connection, limit: int = 100, lot_id: int | None = None,
           notification: bool | None = None) -> list[dict]:
    sql = "SELECT * FROM evenements"
    clauses, params = [], []
    if lot_id is not None:
        clauses.append("lot_id = ?")
        params.append(lot_id)
    if notification is not None:
        clauses.append("notification = ?")
        params.append(1 if notification else 0)
    if clauses:
        sql += " WHERE " + " AND ".join(clauses)
    sql += " ORDER BY id DESC LIMIT ?"
    params.append(max(1, min(int(limit), 1000)))
    rows = db.toutes(conn, sql, tuple(params))
    for r in rows:
        r["notification"] = bool(r["notification"])
        r["lu"] = bool(r["lu"])
    return rows


def marquer_lu(conn: sqlite3.Connection, evenement_id: int) -> bool:
    cur = conn.execute("UPDATE evenements SET lu = 1 WHERE id = ? AND notification = 1", (evenement_id,))
    return cur.rowcount > 0


def tout_lu(conn: sqlite3.Connection) -> int:
    cur = conn.execute("UPDATE evenements SET lu = 1 WHERE notification = 1 AND lu = 0")
    return cur.rowcount
