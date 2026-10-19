"""Interface ComfyUI (local, carte graphique) : lancer un workflow, suivre, récupérer les fichiers."""
from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path


class ComfyUI(ABC):
    mode: str = ""

    @abstractmethod
    def tester_connexion(self) -> dict:
        """{"ok", "etat": "Joignable|Erreur", "message", "details": {"gpu", "vram_total_mo", ...}}"""

    @abstractmethod
    def lancer_workflow(self, workflow_json: dict) -> str:
        """Soumet un workflow (format API de ComfyUI) ; renvoie le prompt_id."""

    @abstractmethod
    def etat(self, prompt_id: str) -> dict:
        """{"prompt_id", "status": "en_attente|en_cours|termine|erreur", "progress": 0-100, "fichiers": [...]}"""

    @abstractmethod
    def recuperer_fichiers(self, prompt_id: str, dossier: str | Path) -> list[Path]:
        """Télécharge les sorties d'un workflow fini dans le dossier ; renvoie leurs chemins."""
