from __future__ import annotations

from fastapi import APIRouter, HTTPException

from api.dependances import Db
from api.services import evenements

router = APIRouter(prefix="/notifications", tags=["notifications"])
CHAMPS = ("id", "date", "type", "niveau", "titre", "texte", "lien", "lu")


@router.get("")
def lister(conn: Db) -> dict:
    rows = evenements.lister(conn, limit=50, notification=True)
    return {"notifications": [{k: r[k] for k in CHAMPS} for r in rows],
            "non_lues": sum(1 for r in rows if not r["lu"])}


@router.post("/tout-lu")
def tout_lu(conn: Db) -> dict:
    return {"ok": True, "marquees": evenements.tout_lu(conn)}


@router.post("/{notification_id}/lu")
def lu(notification_id: int, conn: Db) -> dict:
    if not evenements.marquer_lu(conn, notification_id):
        raise HTTPException(404, f"notification {notification_id} introuvable")
    return {"ok": True, "id": notification_id}
