"""Fabrication IA, 2e moitié (étape 7) : import du GLB reçu, finition, contrôles, rendus (file Blender)."""
from __future__ import annotations

from api.services import fabrication, fabrication_ia

TYPE = fabrication_ia.TYPE_FINITION


def run(tache: dict, ctx) -> dict:
    return fabrication.executer(ctx.db, ctx.config, tache["params"], tache_id=tache["id"],
                                progression=ctx.progression, arret=ctx.arret_demande)
