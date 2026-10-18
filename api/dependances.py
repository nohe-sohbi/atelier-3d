"""Dépendances FastAPI : connexion SQLite par requête, config relue à chaque requête."""
from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from typing import Annotated

from fastapi import Depends

from api import config as cfgmod
from api import db


def get_db() -> Iterator[sqlite3.Connection]:
    conn = db.connexion()
    try:
        yield conn
    finally:
        conn.close()


def get_config() -> dict:
    return cfgmod.charger()


Db = Annotated[sqlite3.Connection, Depends(get_db)]
Config = Annotated[dict, Depends(get_config)]
