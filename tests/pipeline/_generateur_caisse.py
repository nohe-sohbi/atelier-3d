"""Générateur de test minimal, au contrat des générateurs code (MANIFESTE + build).

Une caisse en bois cerclée de fer : un seul maillage fermé, deux matériaux du style,
UV sans chevauchement, pivot sol-centre, symétrique en X. Sert aux tests du pipeline
tant que generators/ n'est pas là, et comme référence du contrat.
"""
from __future__ import annotations

MANIFESTE = {
    "nom": "caisse_test",
    "titre": "Caisse de test",
    "version": 1,
    "types": ["caisse"],
    "categorie": "petit_prop",
    "famille": "contenants",
    "dimensions_type": "caisse",
    "symetrique": "X",
    "pieces_declarees": 1,
    "parametres": {
        "largeur_m": {"type": "float", "defaut": 0.60, "min": 0.3, "max": 1.2, "aide": "largeur X"},
        "profondeur_m": {"type": "float", "defaut": 0.40, "min": 0.3, "max": 1.0, "aide": "profondeur Y"},
        "hauteur_m": {"type": "float", "defaut": 0.40, "min": 0.2, "max": 1.0, "aide": "hauteur Z"},
        "arrondi_m": {"type": "float", "defaut": 0.02, "min": 0.0, "max": 0.05, "aide": "rayon des arêtes"},
        "cerclage": {"type": "float", "defaut": 0.08, "min": 0.0, "max": 0.3,
                     "aide": "largeur relative des bandes de fer (0 = sans)"},
        "subdivisions": {"type": "int", "defaut": 1, "min": 0, "max": 3, "aide": "densité du maillage"},
    },
    "variantes": {"A": {}, "B": {"hauteur_m": 0.5, "cerclage": 0.12}},
}


def parametres_effectifs(params: dict | None) -> dict:
    p = {k: v["defaut"] for k, v in MANIFESTE["parametres"].items()}
    p.update(params or {})
    return p


def build(params: dict, style, seed: int = 0):
    import bmesh
    import bpy

    from pipeline._bpy import lier, selectionner
    from pipeline.materials import materiau_style

    p = parametres_effectifs(params)
    me = bpy.data.meshes.new("caisse")
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co.x *= p["largeur_m"]
        v.co.y *= p["profondeur_m"]
        v.co.z *= p["hauteur_m"]
        v.co.z += p["hauteur_m"] / 2  # pivot sol-centre
    if p["arrondi_m"] > 0:
        bmesh.ops.bevel(bm, geom=list(bm.edges), offset=p["arrondi_m"], segments=2, profile=0.5,
                        affect="EDGES", clamp_overlap=True)
    for _ in range(int(p["subdivisions"])):
        bmesh.ops.subdivide_edges(bm, edges=list(bm.edges), cuts=1, use_grid_fill=True)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    # bandes de fer : les faces dont le centre tombe dans deux bandes verticales
    demi = p["cerclage"] * p["largeur_m"] / 2
    for f in bm.faces:
        cx = f.calc_center_median().x
        f.material_index = 1 if demi > 0 and (abs(abs(cx) - p["largeur_m"] * 0.3) < demi) else 0
        f.smooth = True
    bm.to_mesh(me)
    bm.free()
    obj = bpy.data.objects.new("caisse", me)
    lier(obj)
    obj.data.materials.append(materiau_style(style, "bois"))
    obj.data.materials.append(materiau_style(style, "fer"))
    # UV : projection intelligente, îlots espacés
    selectionner(obj)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=1.15, island_margin=0.02, correct_aspect=True, scale_to_bounds=False)
    bpy.ops.object.mode_set(mode="OBJECT")
    return obj
