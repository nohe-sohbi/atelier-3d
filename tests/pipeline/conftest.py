"""Fixtures de la fabrication : un Blender réel quand la machine en a un (tests marqués `blender`)."""
from __future__ import annotations

import pytest

from api.services import outils


@pytest.fixture
def cfg_blender(cfg) -> dict:
    """La config de test avec le Blender de la machine ; le test est sauté s'il n'y en a pas."""
    chemin = outils.detecter_blender()
    if chemin is None:
        pytest.skip("Blender 5.2 introuvable sur cette machine")
    cfg["blender"]["chemin"] = chemin
    return cfg
