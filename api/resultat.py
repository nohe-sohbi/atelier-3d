"""Forme commune du résultat d'un test de connexion ou d'outil (écran Réglages).

Module sans dépendance : importable par dev.py avant que tout soit installé.
"""
from __future__ import annotations


def resultat_test(ok: bool, etat: str, message: str, details: dict | None = None) -> dict:
    """{"ok", "etat", "message", "details"}. `etat` : Connecté, Détecté, Joignable, Introuvable, Erreur."""
    return {"ok": ok, "etat": etat, "message": message, "details": details or {}}
