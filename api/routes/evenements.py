from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from api.dependances import get_db
from api.services import evenements

router = APIRouter(tags=["evenements"])


@router.get("/evenements")
def journal(limit: int = Query(100, ge=1, le=1000), lot_id: int | None = None, conn=Depends(get_db)) -> dict:
    return {"evenements": evenements.lister(conn, limit=limit, lot_id=lot_id)}
