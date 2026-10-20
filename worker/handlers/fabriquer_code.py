"""Fabrication par code d'un objet (étape 5) : générer, finir, contrôler, rendre, dans Blender (file Blender)."""
from __future__ import annotations

from api.services import fabrication

TYPE = fabrication.TYPE_TACHE


def run(tache: dict, ctx) -> dict:
    return fabrication.executer(ctx.db, ctx.config, tache["params"], tache_id=tache["id"],
                                progression=ctx.progression, arret=ctx.arret_demande)
