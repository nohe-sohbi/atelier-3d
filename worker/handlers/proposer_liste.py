"""Liste du brief proposée par Claude (simulé par défaut), puis routée par les règles."""
from __future__ import annotations

from api.services import brief

TYPE = brief.TYPE_TACHE_PROPOSITION


def run(tache: dict, ctx) -> dict:
    ctx.progression(10, "demande envoyée à Claude")
    resultat = brief.executer_proposition(ctx.db, ctx.claude, tache["params"], tache_id=tache["id"], cfg=ctx.config)
    ctx.progression(100, f"{len(resultat['objets'])} objets proposés")
    return resultat
