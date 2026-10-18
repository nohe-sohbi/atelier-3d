from __future__ import annotations

from api.adapters.claude.base import Claude
from api.adapters.claude.reel import ClaudeReel
from api.adapters.claude.simule import ClaudeSimule


def get_claude(config: dict) -> Claude:
    if config.get("services", {}).get("claude", {}).get("mode") == "reel":
        return ClaudeReel(config)
    return ClaudeSimule(config)


__all__ = ["Claude", "ClaudeReel", "ClaudeSimule", "get_claude"]
