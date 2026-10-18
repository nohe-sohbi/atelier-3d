"""Handler de test : lève toujours, pour vérifier les relances."""
from __future__ import annotations

TYPE = "echec"


def run(tache: dict, ctx) -> dict:
    raise RuntimeError(tache["params"].get("message", "échec volontaire"))
