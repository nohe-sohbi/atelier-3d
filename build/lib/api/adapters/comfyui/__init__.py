from __future__ import annotations

from pathlib import Path

from api.adapters.comfyui.base import ComfyUI
from api.adapters.comfyui.reel import ComfyUIReel
from api.adapters.comfyui.simule import ComfyUISimule


def get_comfyui(config: dict, dossier_simule: Path | None = None) -> ComfyUI:
    if config.get("services", {}).get("comfyui", {}).get("mode") == "reel":
        return ComfyUIReel(config)
    return ComfyUISimule(config, dossier_simule)


__all__ = ["ComfyUI", "ComfyUIReel", "ComfyUISimule", "get_comfyui"]
