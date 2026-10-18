"""Solde Meshy : une seule source de vérité, l'adaptateur.

En mode réel il lit GET /openapi/v1/balance ; en mode simulé l'état local du simulateur.
Si Meshy est injoignable, on renvoie None et on écrit un événement (au plus un toutes les 10 min) :
l'interface affiche alors « solde non lu », jamais un chiffre inventé.
"""
from __future__ import annotations

import sqlite3

from api import config as cfgmod
from api.adapters import get_meshy
from api.services import evenements

MESHY_INJOIGNABLE = "meshy_injoignable"


def solde_meshy(conn: sqlite3.Connection, cfg: dict) -> dict | None:
    """{"restants", "total", "utilises", "mode"} ou None si le solde n'a pas pu être lu."""
    try:
        s = get_meshy(cfg).solde()
    except Exception as e:  # noqa: BLE001 - l'écran ne doit pas tomber si Meshy est injoignable
        if not evenements.recent_existe(conn, MESHY_INJOIGNABLE, minutes=10):
            evenements.ecrire(conn, MESHY_INJOIGNABLE, "Solde Meshy non lu",
                              f"{type(e).__name__}: {e}"[:300], niveau="alerte")
        return None
    total = int(s.get("total") or 0)
    restants = int(s.get("restants") or 0)
    return {"restants": restants, "total": total, "utilises": max(0, total - restants),
            "mode": cfgmod.mode(cfg, "meshy")}
