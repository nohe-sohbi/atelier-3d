"""Finition commune (bpy) : du .blend de la génération au dossier d'asset livrable.

Normaliser (nom, orientation, échelle, pivot, nettoyage) → matériaux du style → LOD0 à 2 et collision convexe →
export `<id>.glb` (glTF 2.0, Y en haut comme le veut le format) et `<id>.fbx` → `<id>.blend`.
`rapport_interne.json` garde ce que les contrôles (hors Blender) ne peuvent pas mesurer sur le GLB.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import bpy

from pipeline import lod, materials, normalize
from pipeline._bpy import compter_tris, mode_objet, selectionner, supprimer_objet
from pipeline._cli import ecrire_json


def _objet(id_asset: str) -> bpy.types.Object:
    obj = bpy.data.objects.get(id_asset)
    if obj is None or obj.type != "MESH":
        maillages = [o for o in bpy.data.objects if o.type == "MESH"]
        if len(maillages) != 1:
            raise normalize.NormalisationImpossible(
                f"objet {id_asset} introuvable dans la génération ({len(maillages)} maillages)")
        obj = maillages[0]
    return obj


def exporter(objets: list[bpy.types.Object], glb: Path, fbx: Path) -> None:
    mode_objet()
    selectionner(objets)
    bpy.ops.export_scene.gltf(filepath=str(glb), export_format="GLB", use_selection=True, export_apply=True,
                              export_yup=True)
    selectionner(objets)
    bpy.ops.export_scene.fbx(filepath=str(fbx), use_selection=True, apply_scale_options="FBX_SCALE_UNITS",
                             axis_forward="-Z", axis_up="Y", mesh_smooth_type="FACE", add_leaf_bones=False,
                             bake_anim=False)


def finir(blend_entree: str | Path, dossier_asset: str | Path, id_asset: str, style, infos: dict[str, Any],
          voie: str = "code") -> dict[str, Any]:
    """infos : categorie, famille, dimensions_type, symetrique, pieces_declarees (le MANIFESTE pour la voie code)."""
    bpy.ops.wm.open_mainfile(filepath=str(blend_entree))
    obj = _objet(id_asset)
    rapport: dict[str, Any] = {"id": id_asset, "voie": voie, "categorie": infos["categorie"],
                               "dimensions_type": infos.get("dimensions_type"), "symetrique": infos.get("symetrique"),
                               "pieces_declarees": int(infos.get("pieces_declarees") or 1),
                               "tris_generation": compter_tris(obj)}
    rapport["normalisation"] = normalize.normaliser(obj, style, infos, id_asset, voie)
    if "reparation" in rapport["normalisation"]:  # voie IA, import : les pièces sont celles gardées par la finition
        rapport["pieces_declarees"] = int(rapport["normalisation"]["reparation"]["pieces"])
    rapport["materiaux"] = materials.appliquer_style(obj, style, voie, id_asset,
                                                     taille_max=style.texture_px(infos["categorie"]))
    lods = lod.generer_lods(obj, style, infos["categorie"], id_asset)
    col = lod.collision(lods[0], id_asset)
    rapport.update(lod.rapport_lods(lods, col))
    supprimer_objet(obj)  # le LOD0 le remplace
    dossier = Path(dossier_asset)
    dossier.mkdir(parents=True, exist_ok=True)
    glb, fbx, blend = (dossier / f"{id_asset}{ext}" for ext in (".glb", ".fbx", ".blend"))
    exporter([*lods, col], glb, fbx)
    bpy.ops.wm.save_as_mainfile(filepath=str(blend))
    rapport["fichiers"] = {"glb": glb.name, "fbx": fbx.name, "blend": blend.name}
    # Voie code : couleurs du style, sans texture cuite (A-TRANCHER 5.4) ; voie IA, import : les textures reçues.
    rapport["textures"] = [{"role": i["role"], "px": i.get("px")} for i in rapport["materiaux"].get("images", [])
                           if i.get("px")]
    ecrire_json(dossier / "rapport_interne.json", rapport)
    return rapport
