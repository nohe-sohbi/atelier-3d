from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query

from api.dependances import get_db
from api.services import taches

router = APIRouter(prefix="/taches", tags=["taches"])
Etat = Literal["en_attente", "en_cours", "terminee", "echouee", "annulee"]


@router.get("")
def lister(etat: Etat | None = None, lot_id: int | None = None, file: str | None = None,
           limit: int = Query(200, ge=1, le=1000), conn=Depends(get_db)) -> dict:
    return {"taches": taches.lister_taches(conn, etat=etat, lot_id=lot_id, file=file, limit=limit)}


@router.get("/{tache_id}")
def lire(tache_id: int, conn=Depends(get_db)) -> dict:
    try:
        return taches.lire_tache(conn, tache_id)
    except taches.TacheIntrouvable as e:
        raise HTTPException(404, str(e)) from e


@router.post("/{tache_id}/relancer")
def relancer(tache_id: int, conn=Depends(get_db)) -> dict:
    try:
        return taches.relancer_tache(conn, tache_id)
    except taches.TacheIntrouvable as e:
        raise HTTPException(404, str(e)) from e
    except taches.TransitionInterdite as e:
        raise HTTPException(409, str(e)) from e


@router.post("/{tache_id}/annuler")
def annuler(tache_id: int, conn=Depends(get_db)) -> dict:
    try:
        return taches.annuler_tache(conn, tache_id)
    except taches.TacheIntrouvable as e:
        raise HTTPException(404, str(e)) from e
    except taches.TransitionInterdite as e:
        raise HTTPException(409, str(e)) from e
