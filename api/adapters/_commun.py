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


def _boite_uv(dims, centre, case: int, cases: int = 4, n: int = 1):
    """Une boîte à faces séparées, chaque face découpée en n × n carrés, chacune dans sa propre case d'une grille UV
    cases × cases (aucun chevauchement)."""
    import numpy as np

    dx, dy, dz = (d / 2 for d in dims)
    cx, cy, cz = centre
    # Chaque face : un coin et deux côtés (sens trigonométrique vu de l'extérieur).
    repere = {
        "+x": ((1, -1, -1), (0, 2, 0), (0, 0, 2)), "-x": ((-1, 1, -1), (0, -2, 0), (0, 0, 2)),
        "+y": ((1, 1, -1), (-2, 0, 0), (0, 0, 2)), "-y": ((-1, -1, -1), (2, 0, 0), (0, 0, 2)),
        "+z": ((-1, -1, 1), (2, 0, 0), (0, 2, 0)), "-z": ((-1, 1, -1), (2, 0, 0), (0, -2, 0)),
    }
    sommets, faces, uv = [], [], []
    m = 0.08 / cases
    for k, (o, a, b) in enumerate(repere.values()):
        u0, v0 = ((case + k) % cases) / cases, ((case + k) // cases) / cases
        base = len(sommets)
        for j in range(n + 1):
            for i in range(n + 1):
                s_, t_ = i / n, j / n
                x, y, z = (o[c] + a[c] * s_ + b[c] * t_ for c in range(3))
                sommets.append((cx + x * dx, cy + y * dy, cz + z * dz))
                uv.append((u0 + m + s_ * (1 / cases - 2 * m), v0 + m + t_ * (1 / cases - 2 * m)))
        for j in range(n):
            for i in range(n):
                q = base + j * (n + 1) + i
                faces += [(q, q + 1, q + n + 2), (q, q + n + 2, q + n + 1)]
    return np.array(sommets), np.array(faces), np.array(uv)


def ecrire_glb_simule(chemin: Path, graine: str) -> Path:
    """Un GLB comme en rend Meshy : Y en haut (glTF), taille arbitraire, quelques milliers de triangles, texture couleur
    2K, et un petit débris flottant (que la finition doit retirer seule). La forme est une boîte dont les dimensions
    dépendent de la graine."""
    import numpy as np
    import trimesh
    from PIL import Image, ImageDraw

    h = hashlib.sha1(graine.encode()).digest()
    dims = [0.4 + h[i] / 255 * 0.6 for i in range(3)]
    corps = _boite_uv(dims, (0, 0, dims[2] / 2), case=0, n=14)  # ≈ 2 400 triangles, comme un objet remaillé
    debris = _boite_uv([0.03, 0.03, 0.03], (dims[0] / 2 + 0.2, 0, 0.1), case=6)
    sommets = np.vstack([corps[0], debris[0]])
    faces = np.vstack([corps[1], debris[1] + len(corps[0])])
    uv = np.vstack([corps[2], debris[2]])
    sommets = sommets @ np.array([[1, 0, 0], [0, 0, -1], [0, 1, 0]], dtype=float)  # Z en haut -> Y en haut (glTF)
    texture = Image.new("RGB", (2048, 2048), (h[3], h[4], h[5]))
    d = ImageDraw.Draw(texture)
    for i in range(16):
        x, y = (i % 4) * 512, (i // 4) * 512
        d.rectangle((x + 40, y + 40, x + 472, y + 472), fill=(h[(6 + i) % 20], h[(7 + i) % 20], h[(8 + i) % 20]))
    maillage = trimesh.Trimesh(vertices=sommets, faces=faces, process=False)
    maillage.visual = trimesh.visual.TextureVisuals(
        uv=uv, material=trimesh.visual.material.PBRMaterial(baseColorTexture=texture, metallicFactor=0.0,
                                                             roughnessFactor=0.8, name="simule"))
    chemin.parent.mkdir(parents=True, exist_ok=True)
    chemin.write_bytes(maillage.export(file_type="glb"))
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

