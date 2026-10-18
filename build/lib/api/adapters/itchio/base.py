"""Interface itch.io (butler) : vérifier l'outil et pousser un pack."""
from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path


class Itchio(ABC):
    mode: str = ""

    @abstractmethod
    def tester_butler(self) -> dict:
        """{"ok", "etat": "Connecté|Erreur", "message", "details": {"version", "compte"}}"""

    @abstractmethod
    def pousser(self, dossier: str | Path, cible: str, canal: str) -> dict:
        """Pousse le dossier sur compte/pack:canal ; renvoie {"ok", "cible", "canal", "fichiers", ...}."""
