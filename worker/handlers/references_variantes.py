"""Variantes d'un objet code (étape 6) : 4 réglages du générateur, une image Blender chacun (file Blender)."""
from __future__ import annotations

from api.services import references

TYPE = references.TYPE_VARIANTES


def run(tache: dict, ctx) -> dict:
    return references.executer_variantes(ctx.db, ctx.config, tache["params"], tache_id=tache["id"],
                                         progression=ctx.progression, arret=ctx.arret_demande)
