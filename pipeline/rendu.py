"""Rendus (bpy) : les 5 vues standard du LOD0 sous une lumière et une caméra fixes (cahier des charges, Revue humaine).

Chaque vue est cadrée sur la sphère englobante de l'objet : un petit et un grand objet remplissent l'image de la
même façon. EEVEE par défaut (rapide sur la carte graphique) ; Cycles sur le processeur quand EEVEE n'a pas de
carte graphique utilisable. La planche de contact et la vignette sont assemblées hors de Blender (pipeline/planche.py).
"""
from __future__ import annotations

import math
from pathlib import Path
from typing import Any

import bpy
from mathutils import Vector

from pipeline._bpy import boite

# Direction de la caméra vers l'objet (depuis le centre), avant normalisation. Face avant = -Y.
VUES = {
    "face": (0.0, -1.0, 0.12),
    "dos": (0.0, 1.0, 0.12),
    "profil": (1.0, 0.0, 0.12),
    "trois_quarts": (0.8, -1.0, 0.6),
    "dessus": (0.0, -0.02, 1.0),
}
TAILLE_PX = 512
OBJECTIF_MM = 50.0
FOND = (0.62, 0.62, 0.60, 1.0)  # gris neutre de la planche de revue (pas une couleur du style)


def _lumieres(scene: bpy.types.Scene) -> None:
    """Éclairage fixe pour tous les assets : une lumière principale, un contre-jour, un fond gris."""
    for nom, rotation, energie in (("principale", (0.9, 0.15, -0.6), 3.5), ("contre", (2.3, 0.0, 2.6), 1.2)):
        soleil = bpy.data.objects.new(nom, bpy.data.lights.new(nom, "SUN"))
        soleil.rotation_euler = rotation
        soleil.data.energy = energie
        scene.collection.objects.link(soleil)
    monde = bpy.data.worlds.new("fond")
    monde.use_nodes = True
    monde.node_tree.nodes["Background"].inputs[0].default_value = FOND
    monde.node_tree.nodes["Background"].inputs[1].default_value = 0.8
    scene.world = monde


def _moteur(scene: bpy.types.Scene, moteur: str, taille_px: int) -> None:
    if moteur == "cycles":
        scene.render.engine = "CYCLES"
        scene.cycles.device = "CPU"
        scene.cycles.samples = 32
        scene.cycles.use_denoising = True
    else:
        scene.render.engine = "BLENDER_EEVEE"
        scene.eevee.taa_render_samples = 32
    scene.render.resolution_x = scene.render.resolution_y = taille_px
    scene.render.film_transparent = False
    scene.render.image_settings.file_format = "PNG"


def _photographier(scene: bpy.types.Scene, obj: bpy.types.Object, sorties: dict[str, Path], moteur: str,
                   taille_px: int) -> None:
    """Lumières, moteur et caméra cadrée sur la sphère englobante de `obj`, puis une image par vue demandée."""
    _lumieres(scene)
    _moteur(scene, moteur, taille_px)
    mini, maxi = boite(obj)
    centre = Vector(((mini[0] + maxi[0]) / 2, (mini[1] + maxi[1]) / 2, (mini[2] + maxi[2]) / 2))
    rayon = max(0.05, (Vector(maxi) - Vector(mini)).length / 2)
    camera = bpy.data.objects.new("camera", bpy.data.cameras.new("camera"))
    camera.data.lens = OBJECTIF_MM
    scene.collection.objects.link(camera)
    scene.camera = camera
    demi_champ = camera.data.angle / 2
    distance = rayon / math.sin(demi_champ) * 1.08
    camera.data.clip_end = distance * 4
    for nom, chemin in sorties.items():
        d = Vector(VUES[nom]).normalized()
        camera.location = centre + d * distance
        camera.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()
        chemin.parent.mkdir(parents=True, exist_ok=True)
        scene.render.filepath = str(chemin)
        bpy.ops.render.render(write_still=True)


def rendre(blend: str | Path, dossier: str | Path, id_asset: str, moteur: str = "eevee",
           taille_px: int = TAILLE_PX) -> dict[str, Any]:
    bpy.ops.wm.open_mainfile(filepath=str(blend))
    scene = bpy.context.scene
    lod0 = bpy.data.objects.get(f"{id_asset}_LOD0")
    if lod0 is None:
        raise ValueError(f"{id_asset}_LOD0 absent du fichier : la finition n'a pas été faite")
    for o in scene.objects:
        o.hide_render = o is not lod0
    sortie = Path(dossier)
    _photographier(scene, lod0, {nom: sortie / f"{nom}.png" for nom in VUES}, moteur, taille_px)
    return {"moteur": moteur, "vues": {nom: f"{nom}.png" for nom in VUES}, "taille_px": taille_px}


def apercu(obj: bpy.types.Object, fichier: str | Path, moteur: str = "eevee", taille_px: int = 384,
           vue: str = "trois_quarts") -> None:
    """Une seule vue de l'objet tel que le générateur l'a construit (variantes des Références)."""
    scene = bpy.context.scene
    for o in scene.objects:
        o.hide_render = o is not obj
    _photographier(scene, obj, {vue: Path(fichier)}, moteur, taille_px)
