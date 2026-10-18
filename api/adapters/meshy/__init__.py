from __future__ import annotations

from pathlib import Path

from api.adapters.meshy.base import Meshy
from api.adapters.meshy.reel import MeshyReel
from api.adapters.meshy.simule import MeshySimule


def get_meshy(config: dict, dossier_simule: Path | None = None) -> Meshy:
    if config.get("services", {}).get("meshy", {}).get("mode") == "reel":
        return MeshyReel(config)
    return MeshySimule(config, dossier_simule)


__all__ = ["Meshy", "MeshyReel", "MeshySimule", "get_meshy"]
