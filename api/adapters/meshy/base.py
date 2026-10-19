"""Interface Meshy : voie IA (image → 3D) et images de référence (image → image)."""
from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

# Tarif Meshy d'après le cahier des charges : 30 crédits par objet 3D texturé, 3 par image.
# Sert au simulateur et aux estimations du Brief ; ce ne sont pas des budgets de fabrication.
CREDITS_3D = 30
CREDITS_IMAGE = 3
IMAGES_REFERENCE_PAR_OBJET = 4


class Meshy(ABC):
    mode: str = ""

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
        """{"id", "status": PENDING|IN_PROGRESS|SUCCEEDED|FAILED, "progress": 0-100, "model_urls", ...}"""

    @abstractmethod
    def telecharger(self, task_id: str, dossier: str | Path) -> Path:
        """Télécharge le résultat d'une tâche finie ; renvoie le GLB (ou le dossier des images)."""

    @abstractmethod
    def image_vers_image(self, prompt: str, image: str | Path | None, n: int = 4) -> str:
        """Lance une tâche image de référence (n variantes) ; renvoie son id."""
