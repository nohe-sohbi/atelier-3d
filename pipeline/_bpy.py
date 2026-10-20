"""Helpers bpy partagés par les scripts de finition (normalize, lod, bake, export, render).

Tout ce qui est ici suppose que `bpy` est importable : ce module ne tourne que dans Blender.
"""
from __future__ import annotations

from collections.abc import Iterable

import bpy
import numpy as np
from mathutils import Matrix


def scene_vide() -> bpy.types.Scene:
    """Repart d'un fichier vide (réglages d'usine), comme `blender --factory-startup`."""
    bpy.ops.wm.read_factory_settings(use_empty=True)
    return bpy.context.scene


def lier(obj: bpy.types.Object, scene: bpy.types.Scene | None = None) -> bpy.types.Object:
    scene = scene or bpy.context.scene
    if obj.name not in scene.collection.objects:
        scene.collection.objects.link(obj)
    return obj


def selectionner(objets: Iterable[bpy.types.Object] | bpy.types.Object,
                 actif: bpy.types.Object | None = None) -> None:
    """Sélectionne exactement ces objets ; le premier (ou `actif`) devient l'objet actif."""
    if isinstance(objets, bpy.types.Object):
        objets = [objets]
    objets = list(objets)
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    for o in objets:
        o.select_set(True)
    bpy.context.view_layer.objects.active = actif or (objets[0] if objets else None)


def mode_objet() -> None:
    if bpy.context.object is not None and bpy.context.object.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")


def appliquer_transformations(obj: bpy.types.Object) -> None:
    """Cuit position, rotation et échelle dans le maillage (sans opérateur)."""
    if obj.data.users > 1:
        obj.data = obj.data.copy()
    obj.data.transform(obj.matrix_world)
    obj.matrix_world = Matrix.Identity(4)
    obj.data.update()


def sommets_monde(obj: bpy.types.Object) -> np.ndarray:
    me = obj.data
    n = len(me.vertices)
    coords = np.empty(n * 3, dtype=np.float32)
    me.vertices.foreach_get("co", coords)
    coords = coords.reshape(n, 3).astype(np.float64)
    m = np.array(obj.matrix_world)
    return coords @ m[:3, :3].T + m[:3, 3]


def boite(obj: bpy.types.Object) -> tuple[np.ndarray, np.ndarray]:
    """(min, max) de la boîte englobante en coordonnées monde."""
    pts = sommets_monde(obj)
    if len(pts) == 0:
        return np.zeros(3), np.zeros(3)
    return pts.min(axis=0), pts.max(axis=0)


def boite_groupe(objets: Iterable[bpy.types.Object]) -> tuple[np.ndarray, np.ndarray]:
    mins, maxs = [], []
    for o in objets:
        a, b = boite(o)
        mins.append(a)
        maxs.append(b)
    if not mins:
        return np.zeros(3), np.zeros(3)
    return np.min(mins, axis=0), np.max(maxs, axis=0)


def compter_tris(obj: bpy.types.Object) -> int:
    me = obj.data
    return sum(max(len(p.vertices) - 2, 0) for p in me.polygons)


def maillage_evalue(obj: bpy.types.Object) -> bpy.types.Mesh:
    """Nouveau maillage = l'objet avec ses modificateurs appliqués."""
    deps = bpy.context.evaluated_depsgraph_get()
    ev = obj.evaluated_get(deps)
    return bpy.data.meshes.new_from_object(ev, preserve_all_data_layers=True, depsgraph=deps)


def appliquer_modificateurs(obj: bpy.types.Object) -> None:
    if not obj.modifiers:
        return
    nouveau = maillage_evalue(obj)
    ancien = obj.data
    nouveau.name = ancien.name + ".tmp"
    obj.data = nouveau
    obj.modifiers.clear()
    nom = ancien.name
    if ancien.users == 0:
        bpy.data.meshes.remove(ancien)
    nouveau.name = nom


def copier_objet(obj: bpy.types.Object, nom: str) -> bpy.types.Object:
    nouveau = obj.copy()
    nouveau.data = obj.data.copy()
    nouveau.name = nom
    nouveau.data.name = nom
    lier(nouveau)
    return nouveau


def supprimer_objet(obj: bpy.types.Object) -> None:
    data = obj.data
    bpy.data.objects.remove(obj, do_unlink=True)
    if data is not None and data.users == 0 and isinstance(data, bpy.types.Mesh):
        bpy.data.meshes.remove(data)


def principled(mat: bpy.types.Material) -> bpy.types.ShaderNodeBsdfPrincipled | None:
    if mat is None or mat.node_tree is None:
        return None
    for n in mat.node_tree.nodes:
        if n.type == "BSDF_PRINCIPLED":
            return n
    return None


def sortie_materiau(mat: bpy.types.Material) -> bpy.types.ShaderNodeOutputMaterial | None:
    for n in mat.node_tree.nodes:
        if n.type == "OUTPUT_MATERIAL" and n.is_active_output:
            return n
    for n in mat.node_tree.nodes:
        if n.type == "OUTPUT_MATERIAL":
            return n
    return None


def regler_cycles_cpu(scene: bpy.types.Scene, echantillons: int, seed: int = 0) -> None:
    """Cycles sur CPU, peu d'échantillons, sans débruitage : le seul moteur qui marche
    en module bpy sans OpenGL (EEVEE et Workbench avortent faute de libEGL)."""
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = int(echantillons)
    scene.cycles.preview_samples = int(echantillons)
    scene.cycles.use_denoising = False
    scene.cycles.use_adaptive_sampling = False
    scene.cycles.seed = int(seed)
    scene.cycles.max_bounces = 4
    scene.render.use_persistent_data = False
