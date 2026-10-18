"""Dépendances FastAPI : connexion SQLite par requête, config relue à chaque requête."""
from __future__ import annotations

from collections.abc import Iterator

from api import config as cfgmod
from api import db


def get_db() -> Iterator:
    conn = db.connexion()
    try:
        yield conn
    finally:
        conn.close()


def get_config() -> dict:
    return cfgmod.charger()
