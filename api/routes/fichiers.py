"""Fichiers servis à l'interface (planches de style, images d'inspiration…), toujours sous /api/fichiers."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from api.services import fabrication, styles

router = APIRouter(prefix="/fichiers", tags=["fichiers"])


@router.get("/styles/{code}/{dossier}/{fichier}")
def fichier_style(code: str, dossier: str, fichier: str) -> FileResponse:
    try:
        return FileResponse(styles.fichier_public(code, dossier, fichier))
    except (FileNotFoundError, ValueError) as e:
        raise HTTPException(404, "fichier introuvable") from e


@router.get("/essais/{essai_id}/{fichier}")
def fichier_essai(essai_id: int, fichier: str) -> FileResponse:
    """Rendus d'un essai (vignette, planche, vues) : une liste fermée de noms."""
    try:
        return FileResponse(fabrication.fichier_public(essai_id, fichier))
    except FileNotFoundError as e:
        raise HTTPException(404, "fichier introuvable") from e
