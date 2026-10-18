"""Amphore : jarre de transport en terre cuite.

Corps de révolution (profil lissé : pied pointu ou base plate, panse, épaule, col, lèvre, puis
intérieur du col jusqu'au fond de la cavité : le maillage reste fermé), deux anses en secteur
de tore qui pénètrent le corps (2 pièces déclarées). Symétrique en X. Pivot au sol.
"""
from __future__ import annotations

import math

from generators import _base as B

MANIFESTE = {
    "nom": "amphore",
    "titre": "Amphore",
    "version": 1,
    "types": ["amphore", "jarre", "vase", "amphore de transport"],
    "categorie": "prop_moyen",
    "famille": "contenants",
    "dimensions_type": "amphore",
    "symetrique": "X",
    "pieces_declarees": 2,
    "parametres": {
        "hauteur_m": {"type": "float", "defaut": 0.90, "min": 0.4, "max": 1.4, "style_dim": "z",
                      "aide": "Hauteur totale (par défaut : style)"},
        "diametre_m": {"type": "float", "defaut": 0.35, "min": 0.2, "max": 0.6, "style_dim": "x",
                       "aide": "Diamètre de la panse = largeur hors tout (par défaut : style)"},
        "col_ratio": {"type": "float", "defaut": 0.32, "min": 0.2, "max": 0.5,
                      "aide": "Diamètre du col rapporté au diamètre de la panse"},
        "epaule": {"type": "float", "defaut": 0.62, "min": 0.45, "max": 0.8,
                   "aide": "Hauteur relative de la panse la plus large (0 = bas, 1 = haut)"},
        "pied": {"type": "choix", "defaut": "pointe", "choix": ["pointe", "plat"],
                 "aide": "Pied pointu (amphore de transport) ou base plate"},
        "anses": {"type": "choix", "defaut": "deux", "choix": ["deux", "aucune"],
                  "aide": "Anses en tore partiel entre col et épaule"},
        "segments": {"type": "int", "defaut": 40, "min": 16, "max": 64,
                     "aide": "Sommets par anneau (pair)"},
    },
    "variantes": {
        "A": {"pied": "pointe", "epaule": 0.62},
        "B": {"pied": "plat", "epaule": 0.55, "col_ratio": 0.38},
    },
}


def _profil(p: dict) -> tuple[list[tuple[float, float]], dict[str, float]]:
    H, R = p["hauteur_m"], p["diametre_m"] / 2.0
    rc = p["col_ratio"] * R
    z_panse = p["epaule"] * H
    if p["pied"] == "pointe":
        bas = [(0.0, 0.0), (0.03 * R, 0.04 * H), (0.12 * R, 0.11 * H), (0.40 * R, 0.25 * H),
               (0.78 * R, 0.42 * H)]
    else:
        bas = [(0.0, 0.0), (0.36 * R, 0.0), (0.40 * R, 0.035 * H), (0.34 * R, 0.07 * H),
               (0.62 * R, 0.18 * H), (0.88 * R, 0.36 * H)]
    z_epaule = z_panse + 0.11 * H
    z_col0 = z_panse + 0.18 * H
    z_levre = H - 0.045 * H
    controle = bas + [
        (R, z_panse), (0.92 * R, z_epaule), (0.68 * R, z_col0 - 0.02 * H),
        (rc, z_col0), (rc, z_levre - 0.01 * H), (1.3 * rc, z_levre), (1.35 * rc, H - 0.015 * H),
        (1.25 * rc, H),
    ]
    exterieur = B.profil_lisse(controle, subdivisions=2)
    interieur = [(0.9 * rc, H), (0.82 * rc, H - 0.04 * H), (0.8 * rc, z_col0),
                 (0.6 * rc, z_col0 - 0.05 * H), (0.0, z_col0 - 0.08 * H)]
    reperes = {"rc": rc, "z_col0": z_col0, "z_levre": z_levre, "z_epaule": z_epaule, "R": R,
               "H": H}
    return exterieur + interieur, reperes


def _rayon_a(profil: list[tuple[float, float]], z: float) -> float:
    """Rayon extérieur du profil à la hauteur z (interpolation sur la partie montante)."""
    meilleur = 0.0
    for (r0, z0), (r1, z1) in zip(profil, profil[1:]):
        if z1 <= z0:
            continue
        if z0 <= z <= z1:
            t = (z - z0) / (z1 - z0)
            meilleur = max(meilleur, r0 + t * (r1 - r0))
    return meilleur


def _anse(profil, rep, style, signe: float):
    """Secteur de tore de la lèvre du col à l'épaule, dans le plan XZ, côté `signe` (±1)."""
    from mathutils import Matrix, Vector

    H = rep["H"]
    za = rep["z_levre"] - 0.03 * H
    zb = rep["z_epaule"] - 0.02 * H
    r_mineur = max(0.010, 0.04 * rep["R"])
    A = Vector((_rayon_a(profil, za) - 0.4 * r_mineur, 0.0, za))
    Bp = Vector((_rayon_a(profil, zb) - 0.4 * r_mineur, 0.0, zb))
    corde = (A - Bp).length
    e1 = (Bp - A).normalized()
    e2 = Vector((e1.z, 0.0, -e1.x))
    if e2.x < 0:
        e2 = -e2
    # l'anse ne doit pas dépasser la panse : on aplatit l'arc, puis on rentre les attaches
    limite = 0.98 * rep["R"] - r_mineur
    for angle in (95.0, 80.0, 65.0, 50.0, 40.0, 30.0):
        rayon_majeur = corde / (2.0 * math.sin(math.radians(angle / 2.0)))
        bombe = rayon_majeur * (1.0 - math.cos(math.radians(angle / 2.0)))
        exces = (A.x + Bp.x) / 2.0 + bombe * e2.x - limite
        if exces <= 0:
            break
    if exces > 0:
        A.x -= exces
        Bp.x -= exces
    obj = B.tore(rayon_majeur, r_mineur, segments_majeur=12, segments_mineur=12, angle_deg=angle,
                 nom="amphore_anse", materiau=B.materiau(style, "terre_cuite"))
    # repère local du secteur : corde (u), direction de l'apex (w), normale (n), milieu (M)
    P0 = Vector((rayon_majeur, 0.0, 0.0))
    P1 = Vector((rayon_majeur * math.cos(math.radians(angle)),
                 rayon_majeur * math.sin(math.radians(angle)), 0.0))
    M = (P0 + P1) / 2.0
    u = (P1 - P0).normalized()
    w = Vector((math.cos(math.radians(angle / 2.0)), math.sin(math.radians(angle / 2.0)), 0.0))
    n = u.cross(w)
    local = Matrix((u, w, n)).transposed().to_4x4()
    local.translation = M
    # repère monde : corde A->B, bombé vers l'extérieur (+X), épaisseur selon Y
    e3 = e1.cross(e2)
    monde = Matrix((e1, e2, e3)).transposed().to_4x4()
    monde.translation = (A + Bp) / 2.0
    T = monde @ local.inverted()
    if signe < 0:
        T = Matrix.Scale(-1.0, 4, Vector((1.0, 0.0, 0.0))) @ T
    B.transformer(obj, T)
    return obj


def build(params: dict, style, seed: int = 0):
    p = B.lire_params(MANIFESTE, params, style)
    n = p["segments"] + (p["segments"] % 2)
    profil, rep = _profil(p)
    corps = B.revolution(profil, n, lisser=True, nom="amphore",
                         materiau=B.materiau(style, "terre_cuite"))
    pieces = [corps]
    if p["anses"] == "deux":
        pieces.append(_anse(profil, rep, style, +1.0))
        pieces.append(_anse(profil, rep, style, -1.0))
    obj = B.joindre(pieces, "amphore")
    return B.finaliser(obj, MANIFESTE, style, p)
