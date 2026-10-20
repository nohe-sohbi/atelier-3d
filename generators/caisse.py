"""Caisse : caisse de transport en planches.

Un seul maillage fermé : un pavé aux arêtes biseautées dont chaque face garde un cadre en
saillie autour d'un panneau en creux ; le panneau est fait de planches séparées par de fines
rainures (horizontales sur les côtés, le long de X dessus et dessous). Cadre en bois ou en fer,
planches en bois. Symétrique en X. Pivot au sol.
"""
from __future__ import annotations

from generators import _base as B

MANIFESTE = {
    "nom": "caisse",
    "titre": "Caisse en planches",
    "version": 1,
    "types": ["caisse", "caisse en bois", "caisse de transport", "coffre", "boite"],
    "categorie": "prop_moyen",
    "famille": "contenants",
    "dimensions_type": "caisse",
    "symetrique": "X",
    "pieces_declarees": 1,
    "parametres": {
        "largeur_m": {"type": "float", "defaut": 0.60, "min": 0.3, "max": 1.2, "style_dim": "x",
                      "aide": "Largeur hors tout (par défaut : style)"},
        "profondeur_m": {"type": "float", "defaut": 0.40, "min": 0.2, "max": 1.0, "style_dim": "y",
                         "aide": "Profondeur hors tout (par défaut : style)"},
        "hauteur_m": {"type": "float", "defaut": 0.40, "min": 0.2, "max": 1.0, "style_dim": "z",
                      "aide": "Hauteur hors tout (par défaut : style)"},
        "planches": {"type": "int", "defaut": 4, "min": 2, "max": 8,
                     "aide": "Nombre de planches par panneau"},
        "cadre_m": {"type": "float", "defaut": 0.045, "min": 0.02, "max": 0.08,
                    "aide": "Largeur du cadre autour de chaque panneau"},
        "creux_m": {"type": "float", "defaut": 0.012, "min": 0.006, "max": 0.025,
                    "aide": "Retrait des panneaux sous le cadre"},
        "cadre": {"type": "choix", "defaut": "bois", "choix": ["bois", "fer"],
                  "aide": "Matériau du cadre (les planches restent en bois)"},
    },
    "variantes": {
        "A": {"cadre": "bois", "planches": 4},
        "B": {"cadre": "fer", "planches": 3},
    },
}

_BISEAU_M = 0.006
_JEU_M = 0.004      # demi-largeur d'une rainure entre deux planches
_BOMBE_M = 0.003    # saillie d'une planche au-dessus du fond des rainures


def _normale_axe(face) -> int | None:
    """0, 1 ou 2 si la face regarde le long de X, Y ou Z ; None sinon (biseaux)."""
    for axe in range(3):
        if abs(face.normal[axe]) > 0.999:
            return axe
    return None


def build(params: dict, style, seed: int = 0):
    import bmesh

    p = B.lire_params(MANIFESTE, params, style)
    W, D, H = p["largeur_m"], p["profondeur_m"], p["hauteur_m"]
    cadre = min(p["cadre_m"], 0.25 * min(W, D, H))
    noms = list(dict.fromkeys((p["cadre"], "bois")))  # matériau du cadre puis des planches
    i_cadre, i_planche = noms.index(p["cadre"]), noms.index("bois")

    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=(W, D, H), verts=bm.verts)
    bmesh.ops.translate(bm, vec=(0.0, 0.0, H / 2.0), verts=bm.verts)
    bmesh.ops.bevel(bm, geom=bm.verts[:] + bm.edges[:], offset=_BISEAU_M, segments=1,
                    affect="EDGES", clamp_overlap=True)
    for f in bm.faces:
        f.material_index = i_cadre

    for face in [f for f in bm.faces if _normale_axe(f) is not None]:
        axe = _normale_axe(face)
        # cadre en saillie, puis panneau en retrait
        bmesh.ops.inset_individual(bm, faces=[face], thickness=cadre, depth=0.0, use_even_offset=True)
        bmesh.ops.inset_individual(bm, faces=[face], thickness=0.0, depth=-p["creux_m"])
        bm.normal_update()
        # le panneau est découpé en bandes : arêtes à couper le long de Z (côtés) ou de Y (dessus)
        long_de = 1 if axe == 2 else 2
        a_couper = [e for e in face.edges
                    if abs((e.verts[1].co - e.verts[0].co)[long_de]) > 0.5 * e.calc_length()]
        normale = face.normal.copy()
        niveau = face.calc_center_median().dot(normale)
        if p["planches"] > 1:
            bmesh.ops.subdivide_edges(bm, edges=a_couper, cuts=p["planches"] - 1, use_grid_fill=True)
            bm.normal_update()
        bandes = [f for f in bm.faces
                  if f.normal.dot(normale) > 0.999 and abs(f.calc_center_median().dot(normale) - niveau) < 1e-6]
        # chaque planche bombe légèrement : rainures en V entre elles
        res = bmesh.ops.inset_individual(bm, faces=bandes, thickness=_JEU_M, depth=_BOMBE_M,
                                         use_even_offset=True)
        for f in bandes + list(res["faces"]):
            f.material_index = i_planche

    materiaux = [B.materiau(style, n) for n in noms]
    obj = B.objet_depuis_bmesh(bm, "caisse", materiaux, lisser=False)
    return B.finaliser(obj, MANIFESTE, style, p)
