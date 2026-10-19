"""Outils partagés par les adaptateurs : état simulé sur disque, fichiers factices, client HTTP."""
from __future__ import annotations

import hashlib
import json
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import httpx

from api import chemins
from api.resultat import resultat_test  # noqa: F401 - réexporté pour les adaptateurs

TIMEOUT_S = 30.0
_cadenas = threading.RLock()


def empreinte(*parties: Any, longueur: int = 12) -> str:
    """Identifiant déterministe à partir de ses entrées."""
    h = hashlib.sha1(json.dumps(parties, sort_keys=True, default=str).encode("utf-8")).hexdigest()
    return h[:longueur]


class EtatSimule:
    """Petit état JSON persistant dans lots/.simule/<nom>.json (soldes, tâches simulées)."""

    def __init__(self, nom: str, dossier: Path | None = None) -> None:
        self.chemin = (dossier or chemins.dossier_simule()) / f"{nom}.json"

    def charger(self) -> dict:
        with _cadenas:
            if not self.chemin.exists():
                return {}
            try:
                return json.loads(self.chemin.read_text(encoding="utf-8") or "{}")
            except json.JSONDecodeError:
                return {}

    def enregistrer(self, etat: dict) -> None:
        with _cadenas:
            self.chemin.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.chemin.with_suffix(".json.tmp")
            tmp.write_text(json.dumps(etat, ensure_ascii=False, indent=1), encoding="utf-8")
            tmp.replace(self.chemin)

    @contextmanager
    def modifier(self) -> Iterator[dict]:
        with _cadenas:
            etat = self.charger()
            yield etat
            self.enregistrer(etat)


def ecrire_glb_simule(chemin: Path, graine: str) -> Path:
    """Un petit GLB valide (boîte dont les dimensions dépendent de la graine), via trimesh."""
    import trimesh

    h = int(hashlib.sha1(graine.encode()).hexdigest(), 16)
    dims = [0.3 + (h >> (8 * i) & 0xFF) / 255 * 0.7 for i in range(3)]
    boite = trimesh.creation.box(extents=dims)
    boite.apply_translation([0, 0, dims[2] / 2])  # pivot au sol, +Z en haut
    chemin.parent.mkdir(parents=True, exist_ok=True)
    chemin.write_bytes(boite.export(file_type="glb"))
    return chemin


def ecrire_png_simule(chemin: Path, graine: str, taille: int = 64) -> Path:
    """Une image PNG unie dont la couleur dépend de la graine, via Pillow."""
    from PIL import Image

    h = hashlib.sha1(graine.encode()).digest()
    chemin.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (taille, taille), (h[0], h[1], h[2])).save(chemin, "PNG")
    return chemin


def client_http(timeout: float = TIMEOUT_S, **kwargs) -> httpx.Client:
    """Client httpx avec timeout ; les en-têtes d'authentification ne sont jamais journalisés."""
    return httpx.Client(timeout=timeout, follow_redirects=True, **kwargs)


def erreur_http(e: Exception) -> str:
    """Message lisible, sans jamais inclure une clé."""
    if isinstance(e, httpx.HTTPStatusError):
        return f"HTTP {e.response.status_code} sur {e.request.url.path}"
    if isinstance(e, httpx.TimeoutException):
        return "délai dépassé"
    if isinstance(e, httpx.RequestError):
        return f"injoignable ({type(e).__name__})"
    return f"{type(e).__name__}: {e}"

