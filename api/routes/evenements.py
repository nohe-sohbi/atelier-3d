from __future__ import annotations

from fastapi import APIRouter, Query

from api.dependances import Db
from api.services import evenements

router = APIRouter(tags=["evenements"])


@router.get("/evenements")
def journal(conn: Db, limit: int = Query(100, ge=1, le=1000), lot_id: int | None = None) -> dict:
    return {"evenements": evenements.lister(conn, limit=limit, lot_id=lot_id)}
