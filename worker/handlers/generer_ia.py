"""Fabrication IA, 1re moitié (étape 7) : l'image choisie part à Meshy (simulé par défaut), le GLB revient."""
from __future__ import annotations

from api.services import fabrication_ia

TYPE = fabrication_ia.TYPE_GENERATION


def run(tache: dict, ctx) -> dict:
    return fabrication_ia.executer_generation(ctx.db, ctx.meshy, ctx.config, tache["params"], tache_id=tache["id"],
                                              progression=ctx.progression, arret=ctx.arret_demande)
