"""Fichiers servis à l'interface (planches de style, images d'inspiration…), toujours sous /api/fichiers."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from api.services import fabrication, references, styles, validation

router = APIRouter(prefix="/fichiers", tags=["fichiers"])


@router.get("/styles/{code}/{dossier}/{fichier}")
def fichier_style(code: str, dossier: str, fichier: str) -> FileResponse:
    try:
        return FileResponse(styles.fichier_public(code, dossier, fichier))
    except (FileNotFoundError, ValueError) as e:
        raise HTTPException(404, "fichier introuvable") from e


@router.get("/essais/{essai_id}/modele.glb")
def modele_essai(essai_id: int) -> FileResponse:
    """Le fichier 3D d'un essai fini (LOD0, LOD1, LOD2 et collision dans un seul .glb), pour l'afficheur de la Validation."""
    try:
        return FileResponse(validation.modele_public(essai_id), media_type="model/gltf-binary")
    except FileNotFoundError as e:
        raise HTTPException(404, "fichier introuvable") from e


@router.get("/essais/{essai_id}/{fichier}")
def fichier_essai(essai_id: int, fichier: str) -> FileResponse:
    """Rendus d'un essai (vignette, planche, vues) : une liste fermée de noms."""
    try:
        return FileResponse(fabrication.fichier_public(essai_id, fichier))
    except FileNotFoundError as e:
        raise HTTPException(404, "fichier introuvable") from e


@router.get("/references/{proposition_id}")
def fichier_reference(proposition_id: int) -> FileResponse:
    """Une proposition de l'écran Références (image Meshy, variante Blender, image donnée)."""
    try:
        return FileResponse(references.fichier_public(proposition_id))
    except FileNotFoundError as e:
        raise HTTPException(404, "fichier introuvable") from e
