"""Services externes : chaque dossier a base.py (interface), simule.py, reel.py.

`get_<service>(config)` renvoie l'adaptateur selon services.<service>.mode (simule par défaut).
"""
from __future__ import annotations

from api.adapters.claude import get_claude
from api.adapters.comfyui import get_comfyui
from api.adapters.itchio import get_itchio
from api.adapters.meshy import get_meshy

__all__ = ["get_meshy", "get_claude", "get_comfyui", "get_itchio"]
