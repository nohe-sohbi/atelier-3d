"""Gladius : glaive court du légionnaire.

Un seul maillage fermé construit en loft de sections polaires le long de Z : pommeau sphérique
(bronze), poignée cannelée (bois), garde rectangulaire (bronze), lame losange à deux tranchants
et arête centrale (fer), pointe. Type « pompeii » (tranchants parallèles, pointe courte) ou
« mainz » (lame cintrée, longue pointe). Symétrique en X ; pivot au milieu de la poignée.
"""
from __future__ import annotations

import math

from generators import _base as B

MANIFESTE = {
    "nom": "gladius",
    "titre": "Gladius (glaive)",
    "version": 1,
    "types": ["gladius", "glaive", "epee courte", "epee"],
    "categorie": "petit_prop",
    "famille": "armes",
    "dimensions_type": "gladius",
    "symetrique": "X",
    "pieces_declarees": 0,
    "parametres": {
        "longueur_m": {"type": "float", "defaut": 0.65, "min": 0.5, "max": 0.85, "style_dim": "z",
                       "aide": "Longueur totale, pommeau compris (par défaut : style)"},
        "largeur_garde_m": {"type": "float", "defaut": 0.08, "min": 0.06, "max": 0.12,
                            "style_dim": "x", "aide": "Largeur de la garde (par défaut : style)"},
        "epaisseur_m": {"type": "float", "defaut": 0.04, "min": 0.03, "max": 0.06, "style_dim": "y",
                        "aide": "Diamètre du pommeau = épaisseur hors tout (par défaut : style)"},
        "largeur_lame_m": {"type": "float", "defaut": 0.05, "min": 0.035, "max": 0.065,
                           "aide": "Largeur de la lame au talon"},
        "longueur_poignee_m": {"type": "float", "defaut": 0.095, "min": 0.07, "max": 0.13,
                               "aide": "Longueur de la poignée (entre pommeau et garde)"},
        "type": {"type": "choix", "defaut": "pompeii", "choix": ["pompeii", "mainz"],
                 "aide": "Pompeii : tranchants parallèles ; Mainz : lame cintrée, longue pointe"},
        "segments": {"type": "int", "defaut": 24, "min": 12, "max": 32,
                     "aide": "Sommets par section (pair)"},
    },
    "variantes": {
        "A": {"type": "pompeii"},
        "B": {"type": "mainz", "largeur_lame_m": 0.055},
    },
}


def _sections(p: dict) -> tuple[list[tuple], dict[str, float]]:
    L = p["longueur_m"]
    rp = p["epaisseur_m"] / 2.0                 # rayon du pommeau
    rg = min(0.0125, rp * 0.65)                 # rayon de la poignée
    ag = p["largeur_garde_m"] / 2.0             # demi-largeur de la garde
    bg = min(rp * 0.8, 0.016)                   # demi-épaisseur de la garde
    wl = p["largeur_lame_m"] / 2.0              # demi-largeur de la lame
    el = 0.004                                  # demi-épaisseur de la lame (arête centrale)
    S: list[tuple] = []
    # pommeau : calotte sphérique jusqu'à la latitude où le rayon rejoint la poignée
    for lat in (-65.0, -35.0, -5.0, 25.0, 50.0):
        a = math.radians(lat)
        S.append((rp + rp * math.sin(a), "cercle", rp * math.cos(a), rp * math.cos(a)))
    zg0 = rp * (1.0 + math.sin(math.radians(50.0))) + 0.004
    S.append((zg0, "cercle", rg, rg))
    # poignée : quatre renflements pour les doigts
    Lg = p["longueur_poignee_m"]
    for k in range(1, 9):
        z = zg0 + Lg * k / 8.0
        r = rg * (1.16 if k % 2 else 1.0)
        S.append((z, "cercle", r, r))
    zg1 = zg0 + Lg
    # garde
    S.append((zg1 + 0.004, "rect", ag - 0.006, bg - 0.004))
    S.append((zg1 + 0.009, "rect", ag, bg))
    S.append((zg1 + 0.022, "rect", ag, bg))
    S.append((zg1 + 0.027, "rect", ag - 0.006, bg - 0.004))
    zb0 = zg1 + 0.030
    Lb = L - zb0
    if Lb <= 0.1:
        raise B.ParametresInvalides("gladius : longueur trop courte pour la poignée demandée")
    if p["type"] == "pompeii":
        lame = [(0.0, 1.0, 1.0), (0.45, 1.0, 1.0), (0.82, 1.0, 0.9), (0.91, 0.55, 0.7)]
    else:
        lame = [(0.0, 1.0, 1.0), (0.28, 0.92, 1.0), (0.52, 0.88, 1.0), (0.70, 0.98, 0.95),
                (0.84, 0.62, 0.75), (0.93, 0.30, 0.55)]
    for t, kw, ke in lame:
        S.append((zb0 + Lb * t, "losange", wl * kw, el * ke))
    reperes = {"zg0": zg0, "zg1": zg1, "zb0": zb0, "L": L}
    return S, reperes


def build(params: dict, style, seed: int = 0):
    p = B.lire_params(MANIFESTE, params, style)
    n = p["segments"] + (p["segments"] % 2)
    sections, rep = _sections(p)
    anneaux = B.anneaux_depuis_sections(sections, n)
    obj = B.loft(anneaux, lisser=True, nom="gladius", pole_bas=(0.0, 0.0, 0.0),
                 pole_haut=(0.0, 0.0, rep["L"]))

    def choix(centre, normale):
        z = centre.z
        if z < rep["zg0"]:
            return "bronze"
        if z < rep["zg1"] + 0.002:
            return "bois"
        if z < rep["zb0"]:
            return "bronze"
        return "fer"

    B.assigner_materiaux(obj, style, choix)
    point_poignee = (0.0, 0.0, (rep["zg0"] + rep["zg1"]) / 2.0)
    return B.finaliser(obj, MANIFESTE, style, p, point_poignee=point_poignee)
