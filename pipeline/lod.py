"""Niveaux de détail et collision (bpy).

- `generer_lods(obj, style, categorie)` -> [LOD0, LOD1, LOD2] : copies triangulées, décimées
  (Decimate collapse) aux ratios `style.lod_ratios` ; le LOD0 est lui-même décimé s'il dépasse
  le budget de la catégorie. Noms `<id>_LOD0/1/2`.
- `collision(obj)` : enveloppe convexe (bmesh.ops.convex_hull) ramenée à 64 triangles au plus,
  nommée `<id>_COL`.
- `compter_tris(obj)`.
"""
from __future__ import annotations

from typing import Any

import bmesh
import bpy

from api.services.style_yaml import Style
from pipeline._bpy import compter_tris, copier_objet, lier, maillage_evalue, supprimer_objet

__all__ = ["collision", "compter_tris", "decimer", "generer_lods", "trianguler"]

TRIS_COLLISION_MAX = 64
ESSAIS_DECIMATION = 8


def trianguler(obj: bpy.types.Object) -> None:
    me = obj.data
    bm = bmesh.new()
    bm.from_mesh(me)
    bmesh.ops.triangulate(bm, faces=bm.faces, quad_method="BEAUTY", ngon_method="BEAUTY")
    bm.to_mesh(me)
    bm.free()
    me.update()


def decimer(obj: bpy.types.Object, ratio: float) -> None:
    """Remplace le maillage de `obj` par sa version décimée (collapse) puis triangulée."""
    ratio = max(0.001, min(1.0, float(ratio)))
    mod = obj.modifiers.new("Decimate", "DECIMATE")
    mod.decimate_type = "COLLAPSE"
    mod.ratio = ratio
    mod.use_collapse_triangulate = True
    nouveau = maillage_evalue(obj)
    obj.modifiers.remove(mod)
    ancien = obj.data
    nom = ancien.name
    obj.data = nouveau
    if ancien.users == 0:
        bpy.data.meshes.remove(ancien)
    nouveau.name = nom
    trianguler(obj)


def _decimer_vers(obj: bpy.types.Object, source: bpy.types.Object, cible: int, tolerance: int,
                  au_plus: bool = False) -> int:
    """Décime une copie de `source` dans `obj` jusqu'à `cible` triangles (± tolérance), en
    corrigeant le ratio d'après le résultat obtenu. Renvoie le nombre de triangles final."""
    t_source = compter_tris(source)
    if t_source == 0:
        return 0
    ratio = cible / t_source
    meilleur: tuple[int, bpy.types.Mesh | None] = (10 ** 9, None)
    for _ in range(ESSAIS_DECIMATION):
        essai = copier_objet(source, obj.name + ".essai")
        decimer(essai, ratio)
        t = compter_tris(essai)
        ecart = abs(t - cible)
        acceptable = (t <= cible) if au_plus else True
        if acceptable and ecart < meilleur[0]:
            if meilleur[1] is not None:
                bpy.data.meshes.remove(meilleur[1])
            meilleur = (ecart, essai.data.copy())
        supprimer_objet(essai)
        if acceptable and ecart <= tolerance:
            break
        if t <= 0:
            break
        ratio = max(0.001, min(1.0, ratio * cible / t))
        if au_plus and t > cible:
            ratio *= 0.97
    if meilleur[1] is None:  # rien d'acceptable : on garde la dernière tentative la plus proche
        decimer(obj, cible / t_source)
        return compter_tris(obj)
    ancien = obj.data
    nom = ancien.name
    obj.data = meilleur[1]
    if ancien.users == 0:
        bpy.data.meshes.remove(ancien)
    obj.data.name = nom
    return compter_tris(obj)


def generer_lods(obj: bpy.types.Object, style: Style, categorie: str,
                 id_asset: str | None = None) -> list[bpy.types.Object]:
    """[LOD0, LOD1, LOD2] : copies de `obj`, triangulées, nommées `<id>_LODn`."""
    base = id_asset or obj.name
    budget = style.budget(categorie)
    ratios = style.lod_ratios
    tol_pct = style.tolerances["lod_pct"]

    lod0 = copier_objet(obj, f"{base}_LOD0")
    trianguler(lod0)
    if compter_tris(lod0) > budget:
        _decimer_vers(lod0, obj, budget, tolerance=max(1, budget // 50), au_plus=True)
        if compter_tris(lod0) > budget:
            # dernier recours : ratio volontairement sous le budget
            decimer(lod0, 0.9 * budget / compter_tris(obj))
    t0 = compter_tris(lod0)
    lods = [lod0]
    for i, r in enumerate(ratios[1:], start=1):
        cible = round(t0 * r)
        # tolérance en triangles : la moitié de la tolérance du style, pour garder de la marge
        tolerance = max(1, int(t0 * tol_pct / 100 * 0.5))
        lodi = copier_objet(lod0, f"{base}_LOD{i}")
        _decimer_vers(lodi, lod0, cible, tolerance)
        lods.append(lodi)
    for o in lods:
        lier(o)
    return lods


def collision(obj: bpy.types.Object, id_asset: str | None = None,
              tris_max: int = TRIS_COLLISION_MAX) -> bpy.types.Object:
    """Enveloppe convexe de `obj`, au plus `tris_max` triangles, nommée `<id>_COL`."""
    base = id_asset or obj.name.removesuffix("_LOD0")
    nom = f"{base}_COL"
    me = bpy.data.meshes.new(nom)
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    _enveloppe(bm)
    bm.to_mesh(me)
    bm.free()
    col = bpy.data.objects.new(nom, me)
    lier(col)
    trianguler(col)
    for _ in range(12):
        t = compter_tris(col)
        if t <= tris_max:
            break
        decimer(col, 0.9 * tris_max / t)
        bm = bmesh.new()
        bm.from_mesh(col.data)
        _enveloppe(bm)
        bm.to_mesh(col.data)
        bm.free()
        trianguler(col)
    if compter_tris(col) > tris_max:
        # enveloppe de la boîte englobante : toujours convexe et 12 triangles
        _boite_convexe(col, obj)
    col.display_type = "WIRE"
    col.data.update()
    return col


def _enveloppe(bm: bmesh.types.BMesh) -> None:
    res = bmesh.ops.convex_hull(bm, input=list(bm.verts), use_existing_faces=False)
    a_supprimer = [g for g in res.get("geom_interior", []) + res.get("geom_unused", [])
                   if isinstance(g, bmesh.types.BMVert)]
    if a_supprimer:
        bmesh.ops.delete(bm, geom=a_supprimer, context="VERTS")
    # faces d'origine éventuelles non membres de l'enveloppe
    enveloppe = {g.index for g in res.get("geom", []) if isinstance(g, bmesh.types.BMFace)}
    bm.faces.ensure_lookup_table()
    orphelines = [f for f in bm.faces if f.index not in enveloppe] if enveloppe else []
    if orphelines and len(orphelines) < len(bm.faces):
        bmesh.ops.delete(bm, geom=orphelines, context="FACES_ONLY")
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)


def _boite_convexe(col: bpy.types.Object, source: bpy.types.Object) -> None:
    from pipeline._bpy import boite
    mn, mx = boite(source)
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co = [mn[i] + (v.co[i] + 0.5) * (mx[i] - mn[i]) for i in range(3)]
    bm.to_mesh(col.data)
    bm.free()
    trianguler(col)


def rapport_lods(lods: list[bpy.types.Object], col: bpy.types.Object | None = None) -> dict[str, Any]:
    r: dict[str, Any] = {f"tris_lod{i}": compter_tris(o) for i, o in enumerate(lods)}
    if col is not None:
        r["tris_collision"] = compter_tris(col)
    return r
