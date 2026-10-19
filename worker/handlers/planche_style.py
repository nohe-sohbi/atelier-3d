"""Planche de référence d'un style : images Meshy (simulées par défaut) rangées dans style/<code>/board/."""
from __future__ import annotations

from api.services import styles

TYPE = styles.TYPE_TACHE_PLANCHE


def run(tache: dict, ctx) -> dict:
    return styles.executer_planche(ctx.db, ctx.meshy, tache["params"], tache_id=tache["id"],
                                   progression=ctx.progression, arret=ctx.arret_demande)
