"""Fichiers servis à l'interface (planches de style, images d'inspiration…), toujours sous /api/fichiers."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from api.services import styles

router = APIRouter(prefix="/fichiers", tags=["fichiers"])


@router.get("/styles/{code}/{dossier}/{fichier}")
def fichier_style(code: str, dossier: str, fichier: str) -> FileResponse:
    try:
        return FileResponse(styles.fichier_public(code, dossier, fichier))
    except (FileNotFoundError, ValueError) as e:
        raise HTTPException(404, "fichier introuvable") from e
