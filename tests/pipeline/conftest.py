"""Fixtures des tests du pipeline. Les tests marqués `bpy` sautent si le module bpy est absent."""
from __future__ import annotations

import struct
import zlib
from pathlib import Path

import numpy as np
import pytest
import trimesh

from pipeline import style as st

RACINE = Path(__file__).resolve().parents[2]
GENERATEUR_TEST = Path(__file__).resolve().parent / "_generateur_caisse.py"


def pytest_configure(config):
    config.addinivalue_line("markers", "bpy: test qui a besoin du module bpy (Blender)")


def pytest_collection_modifyitems(config, items):
    try:
        import bpy  # noqa: F401
        present = True
    except Exception:  # noqa: BLE001
        present = False
    if present:
        return
    saut = pytest.mark.skip(reason="module bpy absent : lancer avec .venv-bpy/bin/pytest")
    for item in items:
        if "bpy" in item.keywords:
            item.add_marker(saut)


@pytest.fixture(scope="session")
def style():
    return st.charger(st.style_par_defaut())


@pytest.fixture(scope="session")
def config_sans_validator():
    return {"gltf_validator": {"chemin": "gltf_validator_absent_pour_le_test"}}


# ---------------------------------------------------------------------------
# Fabrique de dossiers d'assets avec trimesh (sans bpy)
# ---------------------------------------------------------------------------
def png_minimal(chemin: Path, taille: int = 4) -> Path:
    """Écrit un PNG RGB valide sans Pillow (utile pour simuler des rendus)."""
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
    faces = np.arange(len(tri)).reshape(-1, 3)
    return trimesh.Trimesh(vertices=tri, faces=faces, process=False)


def uv_grille(mesh: trimesh.Trimesh, cases: int = 8, retrait: float = 0.9) -> np.ndarray:
    """UV sans chevauchement : chaque triangle dans sa case d'une grille cases x cases."""
    n = len(mesh.faces)
    assert n <= cases * cases, "trop de triangles pour la grille UV"
    uv = np.zeros((len(mesh.vertices), 2))
    gabarit = np.array([[0.0, 0.0], [1.0, 0.0], [0.0, 1.0]])
    for i, f in enumerate(mesh.faces):
        cx, cy = i % cases, i // cases
        centre = np.array([0.5, 0.5])
        local = (gabarit - centre) * retrait + centre
        uv[f] = (np.array([cx, cy]) + local) / cases
    return uv


def avec_n_tris(base: trimesh.Trimesh, n: int) -> trimesh.Trimesh:
    """Subdivise des faces de `base` jusqu'à obtenir exactement n triangles (n = f + 3k)."""
    f = len(base.faces)
    assert n >= f and (n - f) % 3 == 0, f"{n} triangles inatteignables depuis {f}"
    k = (n - f) // 3
    if k == 0:
        return base.copy()
    assert k <= f
    return base.subdivide(face_index=np.arange(k))


def boite(extents=(0.6, 0.4, 0.4)) -> trimesh.Trimesh:
    m = trimesh.creation.box(extents=extents)
    m.apply_translation([0, 0, extents[2] / 2])
    return m


def dossier_asset(tmp_path: Path, id_asset: str, lod0: trimesh.Trimesh, lod1=None, lod2=None,
                  col=None, uv=None, texture_px: int | None = 1024, fbx: bool = True,
                  rendus: bool = True, meta: dict | None = None) -> Path:
    """Écrit <tmp>/<id>/ avec un GLB (LOD0/1/2/COL), un FBX factice, des rendus et un meta.json."""
    from PIL import Image

    dossier = tmp_path / id_asset
    dossier.mkdir(parents=True, exist_ok=True)
    lod0 = lod0.copy()
    if uv is None:
        uv = uv_grille(lod0)
    img = Image.new("RGB", (texture_px, texture_px), (181, 88, 46)) if texture_px else None
    mat = trimesh.visual.material.PBRMaterial(baseColorTexture=img, name=f"{id_asset}_MAT")
    lod0.visual = trimesh.visual.TextureVisuals(uv=uv, material=mat)
    if lod1 is None:
        lod1 = lod0
    if lod2 is None:
        lod2 = lod0
    if col is None:
        col = lod0.convex_hull
    scene = trimesh.Scene()
    for suffixe, m in (("_LOD0", lod0), ("_LOD1", lod1), ("_LOD2", lod2), ("_COL", col)):
        scene.add_geometry(m, node_name=id_asset + suffixe, geom_name=id_asset + suffixe)
    scene.export(dossier / f"{id_asset}.glb")
    if fbx:
        (dossier / f"{id_asset}.fbx").write_bytes(b"Kaydara FBX Binary  \x00" + b"\x00" * 64)
    if rendus:
        for v in ("face", "dos", "profil", "trois_quarts", "dessus", "vignette", "planche"):
            png_minimal(dossier / "rendus" / f"{v}.png")
    if meta is not None:
        import json
        (dossier / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    return dossier
