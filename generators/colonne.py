"""Colonne : module d'architecture (ordre toscan / dorique romain).

Un seul maillage fermé en loft de sections polaires : plinthe carrée, tore de base, fût à
entasis (cannelures optionnelles creusées par _base.cannelures), chapiteau toscan simple
(astragale, échine en quart-de-rond, abaque carré). `chapiteau: "aucun"` laisse le fût monter
à pleine hauteur avec un dessus plat, pour recevoir un chapiteau orné venu de la voie IA
(objet mixte). Symétrique en X. Pivot au sol.
"""
from __future__ import annotations

import math

from generators import _base as B

MANIFESTE = {
    "nom": "colonne",
    "titre": "Colonne",
    "version": 1,
    "types": ["colonne", "colonne toscane", "colonne dorique", "pilier"],
    "categorie": "module_archi",
    "famille": "archi",
    "dimensions_type": "colonne",
    "symetrique": "X",
    "pieces_declarees": 0,
    "parametres": {
        "hauteur_m": {"type": "float", "defaut": 4.5, "min": 2.0, "max": 8.0, "style_dim": "z",
                      "aide": "Hauteur totale, plinthe et chapiteau compris (par défaut : style)"},
        "diametre_m": {"type": "float", "defaut": 0.60, "min": 0.3, "max": 1.2, "style_dim": "x",
                       "aide": "Côté de la plinthe et de l'abaque = largeur hors tout"},
        "chapiteau": {"type": "choix", "defaut": "toscan", "choix": ["toscan", "aucun"],
                      "aide": "Toscan : échine et abaque ; aucun : fût à pleine hauteur (chapiteau IA)"},
        "cannelures": {"type": "int", "defaut": 0, "min": 0, "max": 24,
                       "aide": "Nombre de cannelures du fût (0 = lisse ; arrondi au pair)"},
        "profondeur_cannelure_m": {"type": "float", "defaut": 0.012, "min": 0.004, "max": 0.03,
                                   "aide": "Profondeur des cannelures"},
        "entasis_m": {"type": "float", "defaut": 0.015, "min": 0.0, "max": 0.06,
                      "aide": "Renflement du fût à mi-hauteur"},
        "materiau": {"type": "choix", "defaut": "marbre", "choix": ["marbre", "pierre"],
                     "aide": "Matériau du style appliqué à toute la colonne"},
        "segments": {"type": "int", "defaut": 48, "min": 16, "max": 96,
                     "aide": "Sommets par anneau du fût lisse (arrondi au multiple de 8)"},
    },
    "variantes": {
        "A": {"chapiteau": "toscan", "cannelures": 0, "materiau": "marbre"},
        "B": {"chapiteau": "toscan", "cannelures": 20, "materiau": "marbre"},
        "C": {"chapiteau": "aucun", "cannelures": 0, "materiau": "pierre"},
    },
}


def _sections(p: dict) -> tuple[list[tuple], dict[str, float]]:
    H, W = p["hauteur_m"], p["diametre_m"]
    ap = W / 2.0                  # demi-côté de la plinthe et de l'abaque
    rb = 0.40 * W                 # rayon du fût en bas
    rt = 0.34 * W                 # rayon du fût en haut
    h_base = 0.40 * W
    h_cap = 0.40 * W if p["chapiteau"] == "toscan" else 0.0
    S: list[tuple] = []
    # plinthe carrée
    S.append((0.0, "rect", ap, ap))
    S.append((0.18 * h_base, "rect", ap, ap))
    # tore de base puis congé vers le fût
    S.append((0.18 * h_base, "cercle", 0.95 * ap, 0.95 * ap))
    for frac, k in ((0.32, 1.0), (0.50, 1.05), (0.68, 0.98), (0.84, 0.88), (1.0, 0.84)):
        r = rb * k
        S.append((frac * h_base, "cercle", r, r))
    z_f0 = h_base
    z_f1 = H - h_cap
    Lf = z_f1 - z_f0
    ent = p["entasis_m"]
    n_anneaux = 14
    for k in range(n_anneaux + 1):
        t = k / n_anneaux
        r = rb - (rb - rt) * t ** 1.6 + ent * math.sin(math.pi * t)
        S.append((z_f0 + Lf * t, "cercle", r, r))
    if p["chapiteau"] == "toscan":
        z = z_f1
        S.append((z + 0.08 * h_cap, "cercle", rt, rt))
        S.append((z + 0.14 * h_cap, "cercle", rt * 1.08, rt * 1.08))      # astragale
        S.append((z + 0.24 * h_cap, "cercle", rt * 1.08, rt * 1.08))
        S.append((z + 0.30 * h_cap, "cercle", rt, rt))
        r_ech = 0.92 * ap                                                # échine (quart-de-rond)
        for k in range(1, 6):
            a = math.radians(90.0 * k / 5)
            S.append((z + 0.30 * h_cap + 0.38 * h_cap * math.sin(a), "cercle",
                      rt + (r_ech - rt) * (1 - math.cos(a)), rt + (r_ech - rt) * (1 - math.cos(a))))
        S.append((z + 0.68 * h_cap, "rect", ap, ap))                      # abaque
        S.append((H, "rect", ap, ap))
    reperes = {"z_f0": z_f0, "z_f1": z_f1}
    return S, reperes


def build(params: dict, style, seed: int = 0):
    p = B.lire_params(MANIFESTE, params, style)
    n_can = p["cannelures"] + (p["cannelures"] % 2)
    if n_can:
        n = 4 * n_can
    else:
        n = max(16, int(round(p["segments"] / 8.0)) * 8)
    sections, rep = _sections(p)
    anneaux = B.anneaux_depuis_sections(sections, n)
    obj = B.loft(anneaux, lisser=True, nom="colonne", materiau=B.materiau(style, p["materiau"]))
    if n_can:
        fondu = 0.08 * (rep["z_f1"] - rep["z_f0"])
        B.cannelures(obj, n_can, p["profondeur_cannelure_m"], z_min=rep["z_f0"] + 0.02,
                     z_max=rep["z_f1"] - 0.02, fondu=fondu)
    # les faces planes (plinthe, abaque, dessus) restent nettes
    for poly in obj.data.polygons:
        if abs(poly.normal.z) > 0.99:
            poly.use_smooth = False
    return B.finaliser(obj, MANIFESTE, style, p)
