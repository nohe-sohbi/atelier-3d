"""Interface Meshy : voie IA (image → 3D) et images de référence (texte ou images → image)."""
from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

# Tarif Meshy d'après le cahier des charges : 30 crédits par objet 3D texturé, 3 par image (modèle
# nano-banana de l'API image). Sert au simulateur et aux estimations ; ce ne sont pas des budgets de fabrication.
CREDITS_3D = 30
CREDITS_IMAGE = 3
IMAGES_REFERENCE_PAR_OBJET = 4

Images = str | Path | list[str | Path] | None


class RefusMeshy(RuntimeError):
    """Meshy refuse la demande (crédits insuffisants, clé absente ou refusée, demande invalide) :
    la relancer telle quelle n'y changera rien."""


def liste_images(images: Images) -> list[str | Path]:
    if images is None:
        return []
    return list(images) if isinstance(images, list | tuple) else [images]


class Meshy(ABC):
    mode: str = ""
    # Tarif de cet adaptateur : l'interface et les estimations n'affichent que ces chiffres.
    credits_image: int = CREDITS_IMAGE
    credits_3d: int = CREDITS_3D

    @abstractmethod
    def tester_connexion(self) -> dict:
        """{"ok": bool, "etat": "Connecté|Erreur", "message": str, "details": dict}"""

    @abstractmethod
    def solde(self) -> dict:
        """{"restants": int, "total": int}"""

    @abstractmethod
    def image_vers_3d(self, image: str | Path, options: dict | None = None) -> str:
        """Lance une tâche image → 3D texturée ; renvoie son id."""

    @abstractmethod
    def etat_tache(self, task_id: str) -> dict:
        """{"id", "status": PENDING|IN_PROGRESS|SUCCEEDED|FAILED|CANCELED, "progress": 0-100,
        "consumed_credits"?, "task_error"?, "model_urls" | "image_urls", ...}"""

    @abstractmethod
    def telecharger(self, task_id: str, dossier: str | Path) -> Path:
        """Télécharge le résultat d'une tâche finie ; renvoie le GLB (ou le dossier des images)."""

    @abstractmethod
    def image_vers_image(self, prompt: str, image: Images = None, n: int = 1) -> str:
        """Lance une tâche image d'après une consigne, guidée par 1 à 5 images de référence s'il y en a ;
        renvoie son id. Lève RefusMeshy quand Meshy refuse la demande."""
