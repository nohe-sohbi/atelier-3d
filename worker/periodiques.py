"""Travaux périodiques du worker, hors file : courts, idempotents, sans tâche en base.

- scanner_generateurs (30 s) : un generators/<type>.py demandé à Claude Code est apparu ? Les objets
  « à créer » passent en voie code et un événement le dit.
"""
from __future__ import annotations

import logging
import time
from collections.abc import Callable

log = logging.getLogger("worker.periodiques")


def scanner_generateurs(conn) -> list[str]:
    from api.services import demandes
    return demandes.scanner(conn)


PERIODIQUES: dict[str, tuple[float, Callable]] = {
    "scanner_generateurs": (30.0, scanner_generateurs),
}


class Periodiques:
    """Exécute chaque travail quand sa période est écoulée ; une erreur est journalisée, jamais propagée."""

    def __init__(self, travaux: dict[str, tuple[float, Callable]] | None = None, horloge=time.monotonic) -> None:
        self.travaux = travaux if travaux is not None else PERIODIQUES
        self._horloge = horloge
        self._derniers: dict[str, float] = {}

    def tour(self, conn, forcer: bool = False) -> list[str]:
        faits = []
        maintenant = self._horloge()
        for nom, (periode, fn) in self.travaux.items():
            dernier = self._derniers.get(nom)
            if not forcer and dernier is not None and maintenant - dernier < periode:
                continue
            self._derniers[nom] = maintenant
            try:
                fn(conn)
                faits.append(nom)
            except Exception:
                log.exception("périodique %s en erreur", nom)
        return faits
