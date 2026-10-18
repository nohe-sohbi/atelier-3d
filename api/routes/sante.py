from __future__ import annotations

from fastapi import APIRouter, Depends

from api import VERSION
from api.dependances import get_config, get_db
from api.services import outils

router = APIRouter(tags=["sante"])


@router.get("/sante")
def sante(conn=Depends(get_db), cfg: dict = Depends(get_config)) -> dict:
    try:
        conn.execute("SELECT 1")
        etat_db = "ok"
    except Exception as e:  # pragma: no cover
        etat_db = f"erreur : {type(e).__name__}"
    return {"statut": "ok", "version": VERSION, "blender": outils.blender_disponible(cfg), "db": etat_db}
