"""État du worker (battement en base) : actif ou arrêté, et ce qui attend dans la file."""
from __future__ import annotations

from fastapi import APIRouter

from api.dependances import Db
from api.services import generation, workers

router = APIRouter(prefix="/worker", tags=["worker"])


@router.get("")
def etat(conn: Db) -> dict:
    return workers.etat(conn)


@router.get("/taches")
def taches_recentes(conn: Db) -> dict:
    """Réglages · File de tâches : l'état du worker et les tâches actives ou récentes, tous lots et styles confondus."""
    return {"worker": workers.etat(conn), "taches": generation.taches_recentes(conn)}
