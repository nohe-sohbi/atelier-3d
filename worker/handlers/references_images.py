"""Images de référence d'un objet IA (étape 6) : 4 images Meshy (simulées par défaut), rangées avec l'objet."""
from __future__ import annotations

from api.services import references

TYPE = references.TYPE_IMAGES


def run(tache: dict, ctx) -> dict:
    return references.executer_images(ctx.db, ctx.meshy, tache["params"], tache_id=tache["id"],
                                      progression=ctx.progression, arret=ctx.arret_demande)
