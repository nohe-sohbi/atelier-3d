"""Pilum : javelot lourd du légionnaire.

Un seul maillage fermé en loft de sections polaires le long de Z : sabot (fer), longue hampe
(bois), lest pyramidal ou en boule (bronze), fine tige de fer et pointe. Symétrique en X (et Y).
Pivot à la poignée : milieu de la hampe.
"""
from __future__ import annotations

import math

from generators import _base as B

MANIFESTE = {
    "nom": "pilum",
    "titre": "Pilum (javelot)",
    "version": 1,
    "types": ["pilum", "javelot", "lance"],
    "categorie": "petit_prop",
    "famille": "armes",
    "dimensions_type": "pilum",
    "symetrique": "X",
    "pieces_declarees": 0,
    "parametres": {
        "longueur_m": {"type": "float", "defaut": 2.0, "min": 1.6, "max": 2.4, "style_dim": "z",
                       "aide": "Longueur totale (par défaut : style)"},
        "largeur_m": {"type": "float", "defaut": 0.06, "min": 0.04, "max": 0.09, "style_dim": "x",
                      "aide": "Largeur du lest = largeur hors tout (par défaut : style)"},
        "diametre_hampe_m": {"type": "float", "defaut": 0.028, "min": 0.02, "max": 0.04,
                             "aide": "Diamètre de la hampe en bois"},
        "longueur_fer_m": {"type": "float", "defaut": 0.60, "min": 0.4, "max": 0.9,
                           "aide": "Longueur de la tige de fer, pointe comprise"},
        "lest": {"type": "choix", "defaut": "pyramide", "choix": ["pyramide", "boule"],
                 "aide": "Forme du lest en bronze entre hampe et fer"},
        "segments": {"type": "int", "defaut": 32, "min": 16, "max": 40,
                     "aide": "Sommets par section (arrondi au multiple de 8)"},
    },
    "variantes": {
        "A": {"lest": "pyramide"},
        "B": {"lest": "boule", "longueur_fer_m": 0.7},
    },
}


def _sections(p: dict) -> tuple[list[tuple], dict[str, float]]:
    L, Lf = p["longueur_m"], p["longueur_fer_m"]
    rh = p["diametre_hampe_m"] / 2.0
    al = p["largeur_m"] / 2.0
    rf = min(0.007, rh * 0.5)
    S: list[tuple] = []
    # sabot de fer en bas
    S.append((0.012, "cercle", 0.006, 0.006))
    S.append((0.045, "cercle", rh, rh))
    z_sabot = 0.05
    S.append((z_sabot, "cercle", rh, rh))
    # lest
    h_lest = 0.12 if p["lest"] == "pyramide" else 2.0 * al
    z_l0 = L - Lf - h_lest
    if z_l0 < 0.6:
        raise B.ParametresInvalides("pilum : fer trop long pour la longueur totale")
    # ligature de cuir au tiers haut de la hampe
    for dz, k in ((-0.03, 1.0), (-0.02, 1.15), (0.02, 1.15), (0.03, 1.0)):
        S.append((z_l0 * 0.82 + dz, "cercle", rh * k, rh * k))
    S.append((z_l0, "cercle", rh, rh))
    if p["lest"] == "pyramide":
        S.append((z_l0 + 0.012, "rect", al, al))
        S.append((z_l0 + 0.04, "rect", al, al))
        S.append((z_l0 + h_lest - 0.01, "rect", al * 0.45, al * 0.45))
        S.append((z_l0 + h_lest, "cercle", rf * 1.3, rf * 1.3))
    else:
        zc = z_l0 + al
        for lat in (-70.0, -40.0, -10.0, 20.0, 50.0, 75.0):
            a = math.radians(lat)
            S.append((zc + al * math.sin(a), "cercle", al * math.cos(a), al * math.cos(a)))
        S.append((z_l0 + h_lest, "cercle", rf * 1.3, rf * 1.3))
    z_fer0 = z_l0 + h_lest
    # tige de fer puis pointe pyramidale
    S.append((z_fer0 + 0.02, "cercle", rf, rf))
    S.append((L - 0.09, "cercle", rf, rf))
    S.append((L - 0.075, "losange", rf * 1.9, rf * 1.9))
    S.append((L - 0.02, "losange", rf * 0.7, rf * 0.7))
    reperes = {"z_sabot": z_sabot, "z_l0": z_l0, "z_fer0": z_fer0, "L": L,
               "z_ligature": z_l0 * 0.82}
    return S, reperes


def build(params: dict, style, seed: int = 0):
    p = B.lire_params(MANIFESTE, params, style)
    n = int(round(p["segments"] / 8.0)) * 8
    n = max(16, n)
    sections, rep = _sections(p)
    anneaux = B.anneaux_depuis_sections(sections, n)
    obj = B.loft(anneaux, lisser=True, nom="pilum", pole_bas=(0.0, 0.0, 0.0),
                 pole_haut=(0.0, 0.0, rep["L"]))

    def choix(centre, normale):
        z = centre.z
        if z < rep["z_sabot"]:
            return "fer"
        if abs(z - rep["z_ligature"]) < 0.03:
            return "cuir"
        if z < rep["z_l0"] + 0.006:
            return "bois"
        if z < rep["z_fer0"] + 0.01:
            return "bronze"
        return "fer"

    B.assigner_materiaux(obj, style, choix)
    point_poignee = (0.0, 0.0, (rep["z_sabot"] + rep["z_l0"]) / 2.0)
    return B.finaliser(obj, MANIFESTE, style, p, point_poignee=point_poignee)
