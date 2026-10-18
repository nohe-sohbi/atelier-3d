"""dev.py : la config du premier lancement est un YAML valide, même avec un chemin Windows."""
import importlib

import yaml

from api import config as cfgmod
from api.services import outils

CHEMIN_WINDOWS = r"C:\Program Files\Blender Foundation\Blender 5.2\blender.exe"


def test_preparer_config_chemin_windows(atelier, monkeypatch):
    atelier.config.unlink()
    dev = importlib.import_module("dev")
    monkeypatch.setattr(outils, "detecter_blender", lambda *a, **k: CHEMIN_WINDOWS)
    chemin = dev.preparer_config()
    assert chemin == atelier.config
    assert yaml.safe_load(chemin.read_text(encoding="utf-8"))["blender"]["chemin"] == CHEMIN_WINDOWS
    assert cfgmod.charger()["blender"]["chemin"] == CHEMIN_WINDOWS
    assert "# Copie ce fichier" in chemin.read_text(encoding="utf-8")  # les commentaires de l'exemple sont gardés


def test_preparer_config_sans_blender(atelier, monkeypatch):
    atelier.config.unlink()
    dev = importlib.import_module("dev")
    monkeypatch.setattr(outils, "detecter_blender", lambda *a, **k: None)
    chemin = dev.preparer_config()
    assert yaml.safe_load(chemin.read_text(encoding="utf-8"))["blender"]["chemin"] == ""
    assert dev.preparer_config() == chemin  # déjà là : rien n'est réécrit
