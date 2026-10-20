"""Normalisation d'un objet (bpy) : transformations, nom, orientation, échelle, pivot, nettoyage.

Voie code : le générateur a déjà posé échelle et pivot, la normalisation le vérifie. Voie IA et import (étape 7) :
`importer_glb` puis `normaliser` redressent, mettent à l'échelle et placent le pivot.
"""
from __future__ import annotations

import math
from pathlib import Path
from typing import Any

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector

from api.services.style_yaml import Style
from pipeline._bpy import (
    appliquer_transformations,
    boite,
    lier,
    mode_objet,
    selectionner,
    supprimer_objet,
)

DIST_FUSION = 1e-4            # fusion des sommets confondus : 0,1 mm (précision numérique, pas un seuil de style)
ATTRIBUTS_GARDES = {"position", "material_index", "sharp_face", "sharp_edge"}
SUFFIXES_SECONDAIRES = ("_LOD1", "_LOD2", "_COL")


class NormalisationImpossible(RuntimeError):
    pass


# ---------------------------------------------------------------------------
# Import GLB (voie IA / CC0 / re-finition)
# ---------------------------------------------------------------------------
def importer_glb(chemin: str | Path, nom: str | None = None) -> bpy.types.Object:
    """Importe un GLB, ne garde que les maillages utiles (LOD0 si l'asset a déjà des LOD),
    les joint en un seul objet et applique les transformations."""
    chemin = Path(chemin)
    if not chemin.is_file():
        raise NormalisationImpossible(f"fichier introuvable : {chemin}")
    mode_objet()
    avant = {o.name for o in bpy.data.objects}
    bpy.ops.import_scene.gltf(filepath=str(chemin))
    nouveaux = [o for o in bpy.data.objects if o.name not in avant]
    maillages = [o for o in nouveaux if o.type == "MESH" and len(o.data.polygons) > 0]
    if any(o.name.endswith("_LOD0") for o in maillages):
        maillages = [o for o in maillages if not any(o.name.endswith(s) for s in SUFFIXES_SECONDAIRES)]
    if not maillages:
        for o in nouveaux:
            supprimer_objet(o)
        raise NormalisationImpossible(f"aucun maillage dans {chemin.name}")
    for o in maillages:
        appliquer_transformations(o)
        o.parent = None
        o.matrix_world = Matrix.Identity(4)
        if o.data.uv_layers and o.data.uv_layers[0].name != "UVMap":
            o.data.uv_layers[0].name = "UVMap"
    obj = maillages[0]
    if len(maillages) > 1:
        selectionner(maillages, actif=obj)
        with bpy.context.temp_override(active_object=obj, selected_objects=maillages,
                                       selected_editable_objects=maillages):
            bpy.ops.object.join()
    for o in nouveaux:
        if o.name != obj.name and o.name in bpy.data.objects:
            supprimer_objet(o)
    if nom:
        obj.name = nom
        obj.data.name = nom
    lier(obj)
    return obj


# ---------------------------------------------------------------------------
# Normalisation
# ---------------------------------------------------------------------------
def _infos(infos: dict[str, Any] | None) -> dict[str, Any]:
    """Accepte un MANIFESTE de générateur ou un dict d'infos."""
    infos = dict(infos or {})
    return {
        "dimensions_type": infos.get("dimensions_type") or infos.get("type")
        or (infos.get("types") or [None])[0],
        "famille": infos.get("famille"),
        "dimensions_m": infos.get("dimensions_m"),
    }


def _extents(obj: bpy.types.Object) -> np.ndarray:
    mn, mx = boite(obj)
    return mx - mn


def _erreur_dimensions(ext: np.ndarray, attendu: np.ndarray) -> float:
    """Erreur minimax en log après la meilleure mise à l'échelle uniforme."""
    r = attendu / np.maximum(ext, 1e-9)
    return float(np.log(r.max()) - np.log(r.min()))


def verifier_orientation(obj: bpy.types.Object, attendu: list[float] | None) -> str:
    """Redresse l'objet si une rotation de 90° fait clairement mieux coller ses proportions
    aux dimensions réelles (objet importé Y vers le haut, ou couché). Renvoie ce qui a été fait."""
    if not attendu:
        return "non vérifiée (pas de dimensions de référence) ; convention +Z haut / -Y face supposée"
    att = np.asarray(attendu, dtype=float)
    ext = _extents(obj)
    if ext.min() <= 0:
        return "objet plat : orientation non vérifiable"
    candidats = {
        "identité": (Matrix.Identity(4), ext),
        "rotation X +90° (Y était le haut)": (Matrix.Rotation(math.radians(90), 4, "X"), ext[[0, 2, 1]]),
        "rotation Z +90° (X et Y échangés)": (Matrix.Rotation(math.radians(90), 4, "Z"), ext[[1, 0, 2]]),
    }
    erreurs = {k: _erreur_dimensions(e, att) for k, (_, e) in candidats.items()}
    meilleur = min(erreurs, key=erreurs.get)
    if meilleur != "identité" and erreurs[meilleur] < 0.7 * erreurs["identité"] and erreurs["identité"] > 0.1:
        obj.data.transform(candidats[meilleur][0])
        obj.data.update()
        return f"redressée : {meilleur}"
    return "conforme (+Z haut ; face -Y supposée par convention)"


def mettre_a_l_echelle(obj: bpy.types.Object, attendu: list[float] | None, tolerance_pct: float) -> dict[str, Any]:
    """Échelle uniforme vers les dimensions réelles si l'écart dépasse la tolérance (ratio gardé)."""
    if not attendu:
        return {"facteur": 1.0, "ecart_avant_pct": None, "ecart_apres_pct": None,
                "detail": "pas de dimensions de référence"}
    att = np.asarray(attendu, dtype=float)
    ext = _extents(obj)
    if ext.min() <= 0:
        raise NormalisationImpossible("objet sans volume : impossible de le mettre à l'échelle")
    ecart_avant = float((np.abs(ext / att - 1) * 100).max())
    r = att / ext
    facteur = float(math.sqrt(r.min() * r.max()))
    if ecart_avant <= tolerance_pct:
        return {"facteur": 1.0, "ecart_avant_pct": round(ecart_avant, 2), "ecart_apres_pct": round(ecart_avant, 2),
                "detail": "dans la tolérance, pas d'échelle appliquée"}
    obj.data.transform(Matrix.Scale(facteur, 4))
    obj.data.update()
    ecart_apres = float((np.abs(_extents(obj) / att - 1) * 100).max())
    return {"facteur": round(facteur, 6), "ecart_avant_pct": round(ecart_avant, 2),
            "ecart_apres_pct": round(ecart_apres, 2),
            "detail": f"échelle x{facteur:.4f} appliquée (écart {ecart_avant:.1f} % -> {ecart_apres:.1f} %)"
            + ("" if ecart_apres <= tolerance_pct else " ; proportions hors tolérance, l'échelle ne suffit pas")}


def placer_pivot(obj: bpy.types.Object, mode: str) -> dict[str, Any]:
    """sol_centre : origine au centre de la boîte au sol. poignee : on garde l'origine posée par
    le générateur si elle est dans la boîte, sinon bas-centre (la poignée d'une arme tenue debout)."""
    mn, mx = boite(obj)
    centre = (mn + mx) / 2
    if mode == "poignee":
        marge = (mx - mn) * 0.05
        origine = np.array(obj.matrix_world.translation)
        dedans = np.all(origine >= mn - marge) and np.all(origine <= mx + marge)
        if dedans and np.allclose(origine, 0):
            return {"mode": mode, "deplacement": [0.0, 0.0, 0.0], "detail": "origine déjà dans la boîte (poignée posée par le générateur)"}
    decalage = np.array([centre[0], centre[1], mn[2]])
    obj.data.transform(Matrix.Translation(Vector((-decalage).tolist())))
    obj.data.update()
    obj.matrix_world = Matrix.Identity(4)
    return {"mode": mode, "deplacement": [round(float(-d), 5) for d in decalage],
            "detail": "origine placée au sol, au centre de la boîte" if mode == "sol_centre"
            else "origine placée en bas au centre (poignée par défaut)"}


def nettoyer_maillage(obj: bpy.types.Object) -> dict[str, Any]:
    """Fusion par distance, normales vers l'extérieur, attributs inutiles supprimés."""
    me = obj.data
    nb_avant = len(me.vertices)
    bm = bmesh.new()
    bm.from_mesh(me)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=DIST_FUSION)
    bmesh.ops.dissolve_degenerate(bm, dist=DIST_FUSION, edges=bm.edges)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(me)
    bm.free()
    supprimes = []
    for attr in list(me.attributes):
        nom = attr.name
        if nom.startswith(".") or nom in ATTRIBUTS_GARDES or attr.is_internal or attr.is_required:
            continue
        if attr.domain == "CORNER" and attr.data_type == "FLOAT2":
            continue  # couche UV, traitée ci-dessous
        try:
            me.attributes.remove(attr)
            supprimes.append(nom)
        except RuntimeError:
            pass
    while len(me.uv_layers) > 1:
        supprimes.append(me.uv_layers[-1].name)
        me.uv_layers.remove(me.uv_layers[-1])
    if me.uv_layers and me.uv_layers[0].name != "UVMap":
        me.uv_layers[0].name = "UVMap"
    me.update()
    return {"sommets_fusionnes": nb_avant - len(me.vertices), "attributs_supprimes": supprimes}


def normaliser(obj: bpy.types.Object, style: Style, infos: dict[str, Any] | None, id_asset: str) -> dict[str, Any]:
    """Applique les transformations, nomme, vérifie l'orientation, met à l'échelle, place le
    pivot, nettoie. Renvoie un rapport (lisible, mis dans rapport_interne.json)."""
    mode_objet()
    if obj.type != "MESH":
        raise NormalisationImpossible(f"{obj.name} n'est pas un maillage")
    i = _infos(infos)
    attendu = i["dimensions_m"] or (style.dimensions(i["dimensions_type"]) if i["dimensions_type"] else None)
    appliquer_transformations(obj)
    obj.name = id_asset
    obj.data.name = id_asset
    rapport: dict[str, Any] = {"id": id_asset, "dimensions_type": i["dimensions_type"], "famille": i["famille"]}
    rapport["orientation"] = verifier_orientation(obj, attendu)
    rapport["echelle"] = mettre_a_l_echelle(obj, attendu, style.tolerances["dimensions_pct"])
    rapport["nettoyage"] = nettoyer_maillage(obj)
    rapport["pivot"] = placer_pivot(obj, style.pivot_pour(i["famille"]))
    mn, mx = boite(obj)
    rapport["dimensions_m"] = [round(float(x), 4) for x in (mx - mn)]
    rapport["dimensions_attendues_m"] = list(attendu) if attendu else None
    return rapport
