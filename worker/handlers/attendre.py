"""Handler de test : dort params.secondes (par pas, avec progression) puis renvoie {"ok": true}."""
from __future__ import annotations

import time

TYPE = "attendre"


def run(tache: dict, ctx) -> dict:
    secondes = float(tache["params"].get("secondes", 0))
    pas = max(1, int(tache["params"].get("pas", 4)))
    for i in range(pas):
        if ctx.arret_demande():
            raise InterruptedError("arrêt demandé")
        time.sleep(secondes / pas)
        ctx.progression(100 * (i + 1) / pas, f"attente {i + 1}/{pas}")
    return {"ok": True, "secondes": secondes}
