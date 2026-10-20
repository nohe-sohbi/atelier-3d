"""Dossiers d'assets fabriqués avec trimesh, sans Blender, pour tester les contrôles (repris de l'archive)."""
from __future__ import annotations

import json
import os
import shutil
import struct
import sys
import zlib
from pathlib import Path

import numpy as np
import trimesh

from pipeline.validate import GLTF_VERS_APP

APP_VERS_GLTF = np.linalg.inv(GLTF_VERS_APP)


def png_minimal(chemin: Path, taille: int = 4) -> Path:
    """Un PNG RGB valide, sans Pillow (rendus simulés)."""
    def chunk(tag: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
    raw = b"".join(b"\x00" + bytes([120, 120, 120] * taille) for _ in range(taille))
    donnees = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", taille, taille, 8, 2, 0, 0, 0)) \
        + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b"")
    chemin.parent.mkdir(parents=True, exist_ok=True)
    chemin.write_bytes(donnees)
    return chemin


def eclater(mesh: trimesh.Trimesh) -> trimesh.Trimesh:
    """Un sommet par coin de triangle (comme un export glTF avec coutures)."""
    tri = mesh.triangles.reshape(-1, 3)
    return trimesh.Trimesh(vertices=tri, faces=np.arange(len(tri)).reshape(-1, 3), process=False)


def uv_grille(mesh: trimesh.Trimesh, cases: int = 8, retrait: float = 0.9) -> np.ndarray:
    """UV sans chevauchement : chaque triangle dans sa case d'une grille cases x cases."""
    assert len(mesh.faces) <= cases * cases, "trop de triangles pour la grille UV"
    uv = np.zeros((len(mesh.vertices), 2))
    gabarit = np.array([[0.0, 0.0], [1.0, 0.0], [0.0, 1.0]])
    centre = np.array([0.5, 0.5])
    for i, f in enumerate(mesh.faces):
        uv[f] = (np.array([i % cases, i // cases]) + (gabarit - centre) * retrait + centre) / cases
    return uv


def avec_n_tris(base: trimesh.Trimesh, n: int) -> trimesh.Trimesh:
    """Subdivise des faces de `base` jusqu'à exactement n triangles (n = f + 3k)."""
    f = len(base.faces)
    assert n >= f and (n - f) % 3 == 0, f"{n} triangles inatteignables depuis {f}"
    k = (n - f) // 3
    return base.copy() if k == 0 else base.subdivide(face_index=np.arange(k))


def boite(extents=(0.6, 0.4, 0.4)) -> trimesh.Trimesh:
    m = trimesh.creation.box(extents=extents)
    m.apply_translation([0, 0, extents[2] / 2])
    return m


def dossier_asset(racine: Path, id_asset: str, lod0: trimesh.Trimesh, lod1=None, lod2=None, col=None, uv=None,
                  texture_px: int | None = 1024, fbx: bool = True, rendus: bool = True, meta: dict | None = None) -> Path:
    """<racine>/<id>/ : GLB (LOD0/1/2/COL, en convention glTF : Y en haut), FBX factice, rendus, meta.json.
    Les maillages sont donnés dans la convention de l'app (Z en haut)."""
    from PIL import Image

    dossier = racine / id_asset
    shutil.rmtree(dossier, ignore_errors=True)  # un dossier neuf : rien ne reste d'un appel précédent
    dossier.mkdir(parents=True)
    lod0 = lod0.copy()
    if uv is None:
        uv = uv_grille(lod0)
    img = Image.new("RGB", (texture_px, texture_px), (181, 88, 46)) if texture_px else None
    mat = trimesh.visual.material.PBRMaterial(baseColorTexture=img, name=f"{id_asset}_MAT")
    lod0.visual = trimesh.visual.TextureVisuals(uv=uv, material=mat)
    lod1 = lod0 if lod1 is None else lod1
    lod2 = lod0 if lod2 is None else lod2
    col = lod0.bounding_box.to_mesh() if col is None else col
    scene = trimesh.Scene()
    for suffixe, m in (("_LOD0", lod0), ("_LOD1", lod1), ("_LOD2", lod2), ("_COL", col)):
        m = m.copy()
        m.apply_transform(APP_VERS_GLTF)
        scene.add_geometry(m, node_name=id_asset + suffixe, geom_name=id_asset + suffixe)
    scene.export(dossier / f"{id_asset}.glb")
    if fbx:
        (dossier / f"{id_asset}.fbx").write_bytes(b"Kaydara FBX Binary  \x00" + b"\x00" * 64)
    if rendus:
        for v in ("face", "dos", "profil", "trois_quarts", "dessus", "vignette", "planche"):
            png_minimal(dossier / "rendus" / f"{v}.png")
    if meta is not None:
        (dossier / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    return dossier


def validateur_factice(dossier: Path, erreurs: int = 0) -> str:
    """Un faux glTF-Validator : avec -o, écrit un rapport JSON sur sa sortie (comme le vrai)."""
    rapport = json.dumps({"issues": {"numErrors": erreurs, "numWarnings": 0,
                                     "messages": [{"severity": 0, "message": "erreur factice"}] * erreurs}})
    script = dossier / "gltf_validator_factice.py"
    script.write_text(f"print({rapport!r})\n", encoding="utf-8")
    if os.name == "nt":
        lanceur = dossier / "gltf_validator_factice.cmd"
        lanceur.write_text(f'@"{sys.executable}" "{script}"\n', encoding="utf-8")
    else:
        lanceur = dossier / "gltf_validator_factice"
        lanceur.write_text(f"#!/bin/sh\nexec '{sys.executable}' '{script}'\n", encoding="utf-8")
        lanceur.chmod(0o755)
    return str(lanceur)
