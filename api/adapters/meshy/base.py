"""Interface Meshy : voie IA (image → 3D) et images de référence (image → image)."""
from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path


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
