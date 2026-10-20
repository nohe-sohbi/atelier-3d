"""Matériaux du style (bpy).

- `materiau_style(style, nom)` : le matériau Principled partagé d'un nom du style (bois, fer...).
  Si `generators._base.materiau` existe, c'est lui qui est utilisé (même matériau que les
  générateurs) ; sinon la copie locale ci-dessous.
- `appliquer_style(obj, style, voie)` :
  voie code : chaque matériau de l'objet doit être un matériau du style ; sinon il est remplacé
  par le plus proche de la palette (ou on lève si `strict`).
  voie ia / cc0 : on garde les textures cuites mais on renomme et range les images.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import bpy
import numpy as np

from api.services.style_yaml import Style, StyleInvalide
from pipeline._bpy import principled

PROP_STYLE = "style_materiau"   # propriété custom posée sur un matériau du style
ROLES_IMAGE = {
    "Base Color": "BaseColor", "Normal": "Normal", "Roughness": "Roughness",
    "Metallic": "Metallic", "Emission Color": "Emission", "Alpha": "Alpha",
}


class MateriauHorsStyle(ValueError):
    pass


# ---------------------------------------------------------------------------
# Matériau du style
# ---------------------------------------------------------------------------
def _materiau_local(style: Style, nom: str) -> bpy.types.Material:
    """Copie locale de generators._base.materiau : un Principled par matériau du style."""
    params = style.materiau(nom)  # lève StyleInvalide si inconnu
    mat = bpy.data.materials.get(nom)
    if mat is None:
        mat = bpy.data.materials.new(nom)
    if mat.node_tree is None:  # anciennes versions : il faut activer les nœuds
        mat.use_nodes = True
    bsdf = principled(mat)
    if bsdf is None:
        bsdf = mat.node_tree.nodes.new("ShaderNodeBsdfPrincipled")
        sortie = next((n for n in mat.node_tree.nodes if n.type == "OUTPUT_MATERIAL"), None) \
            or mat.node_tree.nodes.new("ShaderNodeOutputMaterial")
        mat.node_tree.links.new(bsdf.outputs["BSDF"], sortie.inputs["Surface"])
    r, g, b = params["rgb"]
    bsdf.inputs["Base Color"].default_value = (r, g, b, 1.0)
    bsdf.inputs["Roughness"].default_value = float(params["roughness"])
    bsdf.inputs["Metallic"].default_value = float(params["metallic"])
    mat.diffuse_color = (r, g, b, 1.0)
    mat.roughness = float(params["roughness"])
    mat.metallic = float(params["metallic"])
    mat[PROP_STYLE] = nom
    return mat


def materiau_style(style: Style, nom: str) -> bpy.types.Material:
    try:
        from generators._base import materiau as _materiau_generateurs  # type: ignore
    except Exception:  # noqa: BLE001 - generators/ absent ou sans _base : copie locale
        _materiau_generateurs = None
    if _materiau_generateurs is not None:
        mat = _materiau_generateurs(style, nom)
        if mat is not None:
            mat[PROP_STYLE] = nom
            return mat
    return _materiau_local(style, nom)


def nom_style_du_materiau(mat: bpy.types.Material | None, style: Style) -> str | None:
    """Le nom du matériau du style que représente `mat`, ou None."""
    if mat is None:
        return None
    nom = mat.get(PROP_STYLE)
    if nom in style.materiaux:
        return str(nom)
    base = mat.name.split(".")[0].lower()
    for prefixe in (style.theme.lower() + "_", "mat_", "m_"):
        base = base.removeprefix(prefixe)
    return base if base in style.materiaux else None


def couleur_de_base(mat: bpy.types.Material) -> tuple[float, float, float] | None:
    bsdf = principled(mat)
    if bsdf is not None:
        c = bsdf.inputs["Base Color"].default_value
        return (float(c[0]), float(c[1]), float(c[2]))
    if mat is not None:
        c = mat.diffuse_color
        return (float(c[0]), float(c[1]), float(c[2]))
    return None


def plus_proche_du_style(style: Style, rgb: tuple[float, float, float], metallic: float | None = None) -> str:
    """Le matériau du style dont la couleur (RGB linéaire) est la plus proche."""
    cible = np.asarray(rgb, dtype=float)
    meilleur, distance = None, float("inf")
    for nom in style.materiaux:
        m = style.materiau(nom)
        d = float(np.linalg.norm(np.asarray(m["rgb"]) - cible))
        if metallic is not None:
            d += 0.25 * abs(float(m["metallic"]) - metallic)
        if d < distance:
            meilleur, distance = nom, d
    if meilleur is None:
        raise StyleInvalide("style sans matériaux")
    return meilleur


# ---------------------------------------------------------------------------
# Application à un objet
# ---------------------------------------------------------------------------
def appliquer_style(obj: bpy.types.Object, style: Style, voie: str = "code", id_asset: str | None = None,
                    dossier_textures: str | Path | None = None, strict: bool = False) -> dict[str, Any]:
    """Voie code : remplace tout matériau hors style par le plus proche de la palette (ou lève si strict).
    Voie ia / cc0 : garde les textures, renomme matériaux et images, range les images."""
    if voie in ("code", "B"):
        return _appliquer_voie_code(obj, style, strict)
    return _ranger_textures(obj, id_asset or obj.name, dossier_textures)


def _appliquer_voie_code(obj: bpy.types.Object, style: Style, strict: bool) -> dict[str, Any]:
    if not obj.material_slots:
        raise MateriauHorsStyle(f"{obj.name} n'a aucun matériau : un générateur doit assigner ceux du style")
    gardes, remplaces = [], []
    for slot in obj.material_slots:
        mat = slot.material
        nom = nom_style_du_materiau(mat, style)
        if nom is None:
            rgb = couleur_de_base(mat) if mat is not None else None
            if rgb is None or strict:
                raise MateriauHorsStyle(
                    f"matériau {mat.name if mat else '(vide)'} hors style sur {obj.name}")
            bsdf = principled(mat)
            metallic = float(bsdf.inputs["Metallic"].default_value) if bsdf else None
            nom = plus_proche_du_style(style, rgb, metallic)
            remplaces.append({"avant": mat.name, "apres": nom})
        else:
            gardes.append(nom)
        slot.material = materiau_style(style, nom)
    return {"voie": "code", "materiaux": [s.material.name for s in obj.material_slots],
            "gardes": gardes, "remplaces": remplaces}


def _ranger_textures(obj: bpy.types.Object, id_asset: str, dossier: str | Path | None) -> dict[str, Any]:
    images: list[dict[str, Any]] = []
    dossier = Path(dossier) if dossier else None
    if dossier:
        dossier.mkdir(parents=True, exist_ok=True)
    for i, slot in enumerate(obj.material_slots):
        mat = slot.material
        if mat is None:
            continue
        mat.name = f"{id_asset}_MAT" if len(obj.material_slots) == 1 else f"{id_asset}_MAT{i}"
        if mat.node_tree is None:
            continue
        bsdf = principled(mat)
        for n in mat.node_tree.nodes:
            if n.type != "TEX_IMAGE" or n.image is None:
                continue
            role = _role_image(n, bsdf, mat)
            img = n.image
            nouveau_nom = f"{id_asset}_{role}"
            if img.name != nouveau_nom:
                img.name = nouveau_nom
            if dossier:
                cible = dossier / f"{nouveau_nom}.png"
                try:
                    img.file_format = "PNG"
                    img.filepath_raw = str(cible)
                    img.save()
                    img.filepath = str(cible)
                except RuntimeError as e:  # image sans pixels (lien cassé) : on le signale
                    images.append({"image": img.name, "role": role, "erreur": str(e)})
                    continue
            images.append({"image": img.name, "role": role, "px": int(img.size[0]) if img.size[0] else None,
                           "fichier": str(dossier / f"{nouveau_nom}.png") if dossier else img.filepath})
    return {"voie": "ia", "materiaux": [s.material.name for s in obj.material_slots if s.material], "images": images}


def _role_image(noeud: bpy.types.Node, bsdf, mat: bpy.types.Material) -> str:
    """Devine le rôle d'une image d'après le socket du Principled qu'elle alimente."""
    for lien in mat.node_tree.links:
        if lien.from_node != noeud:
            continue
        vers = lien.to_node
        if bsdf is not None and vers == bsdf:
            return ROLES_IMAGE.get(lien.to_socket.name, lien.to_socket.name.replace(" ", ""))
        if vers.type == "NORMAL_MAP":
            return "Normal"
        if vers.type in ("SEPARATE_COLOR", "SEPRGB"):
            return "ORM"
    return "Texture"
