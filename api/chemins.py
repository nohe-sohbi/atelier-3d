"""Chemins du projet, surchargeables par variables d'environnement (tests)."""
from __future__ import annotations

import os
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent


def racine() -> Path:
    return RACINE


def chemin_db() -> Path:
    return Path(os.environ.get("ATELIER_DB") or RACINE / "atelier.db")


def chemin_config() -> Path:
    return Path(os.environ.get("ATELIER_CONFIG") or RACINE / "config.local.yaml")


def chemin_config_exemple() -> Path:
    return RACINE / "config.local.example.yaml"


def dossier_lots() -> Path:
    return Path(os.environ.get("ATELIER_LOTS") or RACINE / "lots")


def dossier_styles() -> Path:
    """Un dossier par style : style/<code>/style.yaml, board/, inspiration/."""
    return Path(os.environ.get("ATELIER_STYLES") or RACINE / "style")


def dossier_generateurs() -> Path:
    """Générateurs code : generators/<nom>.py (MANIFESTE + build) et generators/demandes/<type>.md."""
    return Path(os.environ.get("ATELIER_GENERATEURS") or RACINE / "generators")


def dossier_simule() -> Path:
    """État des adaptateurs simulés (soldes, tâches)."""
    return dossier_lots() / ".simule"


def dossier_web_dist() -> Path:
    return Path(os.environ.get("ATELIER_WEB_DIST") or RACINE / "web" / "dist")
