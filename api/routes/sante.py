from __future__ import annotations

from fastapi import APIRouter

from api import VERSION
from api.dependances import Config, Db
from api.services import outils

router = APIRouter(tags=["sante"])


@router.get("/sante")
def sante(conn: Db, cfg: Config) -> dict:
    try:
        conn.execute("SELECT 1")
        etat_db = "ok"
    except Exception as e:  # noqa: BLE001
        etat_db = f"erreur : {type(e).__name__}"
    return {"statut": "ok", "version": VERSION, "blender": outils.blender_disponible(cfg), "db": etat_db}
