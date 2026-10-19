"""Interface API Claude : liste du brief (JSON structuré) et avis IA sur les rendus.

L'usage renvoyé : {"tokens_entree": int, "tokens_sortie": int, "modele": str}.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path


class Claude(ABC):
    mode: str = ""

    @abstractmethod
    def tester_connexion(self) -> dict:
        """{"ok", "etat": "Connecté|Erreur", "message", "details": {"modeles": [...]}}"""

    @abstractmethod
    def completer_json(self, system: str, user: str, schema: dict) -> tuple[dict, dict]:
        """Réponse JSON conforme au schéma + usage."""

    @abstractmethod
    def avis_rendus(self, images: list[str | Path], contexte: str) -> tuple[str, dict]:
        """Avis texte sur des rendus + usage."""
