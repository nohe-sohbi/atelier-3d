from __future__ import annotations

from pathlib import Path

from api.adapters.itchio.base import Itchio
from api.adapters.itchio.reel import ItchioReel
from api.adapters.itchio.simule import ItchioSimule


def get_itchio(config: dict, dossier_simule: Path | None = None) -> Itchio:
    if config.get("services", {}).get("itchio", {}).get("mode") == "reel":
        return ItchioReel(config)
    return ItchioSimule(config, dossier_simule)


__all__ = ["Itchio", "ItchioReel", "ItchioSimule", "get_itchio"]
