from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, HTTPException, Query

from api.dependances import Db
from api.services import taches

router = APIRouter(prefix="/taches", tags=["taches"])
Etat = Literal["en_attente", "en_cours", "terminee", "echouee", "annulee"]


@router.get("")
def lister(conn: Db, etat: Etat | None = None, lot_id: int | None = None, file: str | None = None,
           limit: int = Query(200, ge=1, le=1000)) -> dict:
    return {"taches": taches.lister_taches(conn, etat=etat, lot_id=lot_id, file=file, limit=limit)}


@router.get("/{tache_id}")
def lire(tache_id: int, conn: Db) -> dict:
    try:
        return taches.lire_tache(conn, tache_id)
    except taches.TacheIntrouvable as e:
        raise HTTPException(404, str(e)) from e


@router.get("/{tache_id}/journal")
def journal(tache_id: int, conn: Db) -> dict:
    """Les événements d'une tâche, du plus ancien au plus récent : ses traces, lisibles depuis l'écran."""
    try:
        taches.lire_tache(conn, tache_id)
    except taches.TacheIntrouvable as e:
        raise HTTPException(404, str(e)) from e
    rows = conn.execute("SELECT id, date, type, niveau, titre, texte FROM evenements WHERE tache_id = ? "
                        "ORDER BY id DESC LIMIT 200", (tache_id,)).fetchall()
    return {"tache_id": tache_id, "evenements": list(reversed(rows))}


@router.post("/{tache_id}/relancer")
def relancer(tache_id: int, conn: Db) -> dict:
    try:
        return taches.relancer_tache(conn, tache_id)
    except taches.TacheIntrouvable as e:
        raise HTTPException(404, str(e)) from e
    except taches.TransitionInterdite as e:
        raise HTTPException(409, str(e)) from e


@router.post("/{tache_id}/annuler")
def annuler(tache_id: int, conn: Db) -> dict:
    try:
        return taches.annuler_tache(conn, tache_id)
    except taches.TacheIntrouvable as e:
        raise HTTPException(404, str(e)) from e
    except taches.TransitionInterdite as e:
        raise HTTPException(409, str(e)) from e
