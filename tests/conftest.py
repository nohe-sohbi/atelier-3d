"""Fixtures communes : base SQLite temporaire, config temporaire copiée de l'exemple, client HTTP."""
from __future__ import annotations

import shutil
from types import SimpleNamespace

import pytest
import yaml

from api import chemins, db
from api import config as cfgmod


@pytest.fixture
def atelier(tmp_path, monkeypatch):
    """Environnement isolé : ATELIER_DB, ATELIER_CONFIG, ATELIER_LOTS, ATELIER_STYLES, ATELIER_GENERATEURS dans tmp_path."""
    config = tmp_path / "config.local.yaml"
    shutil.copy(chemins.chemin_config_exemple(), config)
    lots = tmp_path / "lots"
    lots.mkdir()
    styles = tmp_path / "style"
    shutil.copytree(chemins.racine() / "style" / "rome-stylise-v0", styles / "rome-stylise-v0")
    generateurs = tmp_path / "generators"
    generateurs.mkdir()
    monkeypatch.setenv("ATELIER_GENERATEURS", str(generateurs))
    monkeypatch.setenv("ATELIER_DB", str(tmp_path / "atelier.db"))
    monkeypatch.setenv("ATELIER_CONFIG", str(config))
    monkeypatch.setenv("ATELIER_LOTS", str(lots))
    monkeypatch.setenv("ATELIER_STYLES", str(styles))
    db.initialiser()
    return SimpleNamespace(racine=tmp_path, config=config, lots=lots, styles=styles, generateurs=generateurs,
                           db=tmp_path / "atelier.db")


@pytest.fixture
def conn(atelier):
    c = db.connexion()
    yield c
    c.close()


@pytest.fixture
def cfg(atelier) -> dict:
    return cfgmod.charger()


@pytest.fixture
def client(atelier):
    from fastapi.testclient import TestClient

    from api.main import create_app

    with TestClient(create_app()) as c:
        yield c



def ecrire_config(chemin, modif):
    """Modifie la config temporaire : modif(dict) -> None."""
    cfg = yaml.safe_load(chemin.read_text(encoding="utf-8")) or {}
    modif(cfg)
    chemin.write_text(yaml.safe_dump(cfg, allow_unicode=True, sort_keys=False), encoding="utf-8")
