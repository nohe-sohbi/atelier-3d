"""Scutum : bouclier rectangulaire courbe des légionnaires.

Coque en bois (grille avant + grille arrière + chant, épaisseur réelle, courbure cylindrique
paramétrée), face avant peinte en pourpre avec un motif en léger relief (ailes, foudre ou uni)
dans un second matériau, bordure et umbo en bronze, poignée en cuir au dos. Trois pièces fermées : la coque, l'umbo et
la poignée (les deux dernières pénètrent la coque). Symétrique en X.
Pivot à la poignée (dos, centre), famille armes.
"""
from __future__ import annotations

import itertools
import math

from generators import _base as B

MANIFESTE = {
    "nom": "scutum",
    "titre": "Scutum (bouclier)",
    "version": 1,
    "types": ["scutum", "bouclier", "bouclier rectangulaire", "bouclier courbe"],
    "categorie": "prop_moyen",
    "famille": "armes",
    "dimensions_type": "scutum",
    "symetrique": "X",
    "pieces_declarees": 3,  # coque, umbo et poignée (CONTRAT.md : toutes les pièces séparées)
    "parametres": {
        "hauteur_m": {"type": "float", "defaut": 1.10, "min": 0.8, "max": 1.4, "style_dim": "z",
                      "aide": "Hauteur totale (par défaut : dimension du style)"},
        "largeur_m": {"type": "float", "defaut": 0.65, "min": 0.4, "max": 0.9, "style_dim": "x",
                      "aide": "Largeur hors tout (par défaut : dimension du style)"},
        "profondeur_m": {"type": "float", "defaut": 0.20, "min": 0.12, "max": 0.30,
                         "style_dim": "y",
                         "aide": "Profondeur hors tout, umbo et poignée compris"},
        "courbure": {"type": "float", "defaut": 0.5, "min": 0.0, "max": 0.8,
                     "aide": "Part minimale de la profondeur prise par la courbure (augmentée si l'umbo ne suffit pas à atteindre la profondeur)"},
        "epaisseur_m": {"type": "float", "defaut": 0.012, "min": 0.006, "max": 0.03,
                        "aide": "Épaisseur du bois de la coque"},
        "umbo_rayon_m": {"type": "float", "defaut": 0.09, "min": 0.05, "max": 0.14,
                         "aide": "Rayon du dôme de l'umbo"},
        "motif": {"type": "choix", "defaut": "ailes", "choix": ["ailes", "foudre", "uni"],
                  "aide": "Motif peint en léger relief sur la face avant"},
        "relief_m": {"type": "float", "defaut": 0.003, "min": 0.0, "max": 0.01,
                     "aide": "Relief du motif peint"},
        "finesse": {"type": "int", "defaut": 20, "min": 8, "max": 30,
                    "aide": "Nombre de cases de la grille sur la largeur (pair)"},
    },
    "variantes": {
        "A": {"motif": "ailes", "courbure": 0.5},
        "B": {"motif": "foudre", "courbure": 0.35},
        "C": {"motif": "uni", "courbure": 0.6, "umbo_rayon_m": 0.11},
    },
}

_MAT_CORPS_AVANT = "pourpre"
_MAT_CORPS_ARRIERE = "bois"
_MAT_BORDURE = "bronze"
_MAT_UMBO = "bronze"
_MAT_MOTIF = "ocre"
_MAT_POIGNEE = "cuir"


def _masque_motif(motif: str, x: float, dz: float, largeur: float, hauteur: float) -> bool:
    """Le point (x, dz) (dz relatif au centre) est-il dans le motif ? Symétrique en X."""
    if motif == "uni":
        return False
    s = 1.0 if x >= 0 else -1.0
    kx, kz = largeur / 0.65, hauteur / 1.10  # le motif suit les proportions du bouclier
    demi = 0.026 * min(kx, kz)
    if motif == "ailes":
        depart = (s * 0.11 * kx, -0.02 * kz)
        for angle in (12.0, 36.0, 60.0):
            a = math.radians(angle)
            fin = (depart[0] + s * 0.19 * kx * math.cos(a), depart[1] + 0.21 * kz * math.sin(a))
            if B.distance_point_segment((x, dz), depart, fin) < demi:
                return True
        return False
    if motif == "foudre":
        pts = [(0.17, 0.40), (0.235, 0.24), (0.15, 0.08), (0.235, -0.09), (0.15, -0.26),
               (0.215, -0.42)]
        pts = [(s * px * kx, pz * kz) for px, pz in pts]
        for a, b in itertools.pairwise(pts):
            if B.distance_point_segment((x, dz), a, b) < demi:
                return True
        return False
    return False


def _coque(p: dict, style, geo: dict):
    """Grille avant + grille arrière + chant : une seule coque fermée."""
    import bmesh

    W, H, e = p["largeur_m"], p["hauteur_m"], p["epaisseur_m"]
    sag = geo["sag"]
    nx = p["finesse"] + (p["finesse"] % 2)
    nz = max(2, round(nx * H / W))
    zc = H / 2.0

    def y_avant(x: float) -> float:
        return sag * (2.0 * x / W) ** 2 - sag

    bm = bmesh.new()
    avant, arriere = [], []
    for j in range(nz + 1):
        z = H * j / nz
        ra, rb = [], []
        for i in range(nx + 1):
            x = -W / 2.0 + W * i / nx
            ra.append(bm.verts.new((x, y_avant(x), z)))
            rb.append(bm.verts.new((x, y_avant(x) + e, z)))
        avant.append(ra)
        arriere.append(rb)

    mats = {"pourpre": 0, "bois": 1, "bronze": 2, "ocre": 3}
    faces_avant = {}
    r_exclusion = p["umbo_rayon_m"] * 1.45
    for j in range(nz):
        for i in range(nx):
            f = bm.faces.new((avant[j][i], avant[j][i + 1], avant[j + 1][i + 1], avant[j + 1][i]))
            bord = i == 0 or i == nx - 1 or j == 0 or j == nz - 1
            cx = -W / 2.0 + W * (i + 0.5) / nx
            cz = H * (j + 0.5) / nz - zc
            if bord:
                f.material_index = mats["bronze"]
            elif math.hypot(cx, cz) > r_exclusion and _masque_motif(p["motif"], cx, cz, W, H):
                f.material_index = mats["ocre"]
            else:
                f.material_index = mats["pourpre"]
            faces_avant[(i, j)] = f
            g = bm.faces.new((arriere[j][i], arriere[j + 1][i], arriere[j + 1][i + 1],
                              arriere[j][i + 1]))
            g.material_index = mats["bois"]
    # chant (bordure) : bas, haut, gauche, droite
    for i in range(nx):
        bm.faces.new((avant[0][i + 1], avant[0][i], arriere[0][i], arriere[0][i + 1])).material_index = mats["bronze"]
        bm.faces.new((avant[nz][i], avant[nz][i + 1], arriere[nz][i + 1], arriere[nz][i])).material_index = mats["bronze"]
    for j in range(nz):
        bm.faces.new((avant[j][0], avant[j + 1][0], arriere[j + 1][0], arriere[j][0])).material_index = mats["bronze"]
        bm.faces.new((avant[j + 1][nx], avant[j][nx], arriere[j][nx], arriere[j + 1][nx])).material_index = mats["bronze"]

    # relief du motif : un sommet dont toutes les faces avant voisines sont du motif avance
    relief = p["relief_m"]
    if relief > 0:
        for j in range(nz + 1):
            for i in range(nx + 1):
                voisines = [faces_avant[(a, b)] for a in (i - 1, i) for b in (j - 1, j)
                            if (a, b) in faces_avant]
                if voisines and all(f.material_index == mats["ocre"] for f in voisines):
                    v = avant[j][i]
                    v.co.y -= relief
    for f in bm.faces:
        f.smooth = True
    materiaux = [B.materiau(style, n) for n in ("pourpre", "bois", "bronze", "ocre")]
    return B.objet_depuis_bmesh(bm, "scutum_coque", materiaux, lisser=True)


def _umbo(p: dict, style, geo: dict):
    r = p["umbo_rayon_m"]
    h = geo["umbo_h"]
    rf = r * 1.3
    profil = [(0.0, -0.03), (rf, -0.03), (rf, 0.004), (r, 0.004)]
    n_dome = 6
    for k in range(1, n_dome + 1):
        t = k / n_dome
        a = t * math.pi / 2.0
        profil.append((r * math.cos(a), 0.004 + h * math.sin(a)))
    # le dernier point est un pôle (rayon 0)
    profil[-1] = (0.0, 0.004 + h)
    obj = B.revolution(profil, 28, lisser=True, nom="scutum_umbo", materiau=B.materiau(style, _MAT_UMBO))
    B.tourner(obj, "X", 90.0)  # +Z local -> -Y : le dôme pointe vers l'avant
    B.deplacer(obj, 0.0, -geo["sag"], p["hauteur_m"] / 2.0)
    return obj


def _poignee(p: dict, style, geo: dict):
    e = p["epaisseur_m"]
    y_dos = -geo["sag"] + e
    prof = geo["poignee_h"]
    obj = B.boite((0.16, prof + 0.01, 0.032), biseau=0.004, segments_biseau=2, nom="scutum_poignee",
                  materiau=B.materiau(style, _MAT_POIGNEE),
                  centre=(0.0, y_dos - 0.01 + (prof + 0.01) / 2.0, p["hauteur_m"] / 2.0))
    return obj


def geometrie(p: dict) -> dict:
    """Répartit la profondeur totale entre courbure, umbo et poignée.

    La profondeur hors tout est garantie : l'umbo complète ce que la courbure laisse (au plus
    une demi-sphère) ; s'il n'y suffit pas, la coque se courbe davantage que demandé."""
    D, e, r_u = p["profondeur_m"], p["epaisseur_m"], p["umbo_rayon_m"]
    poignee_h = 0.035
    h_min = 0.02
    flasque = 0.004  # épaisseur de la collerette de l'umbo
    sag = p["courbure"] * D

    def arriere(s: float) -> float:  # saillie derrière le plan des bords (coque ou poignée)
        return e + max(0.0, poignee_h - s)

    umbo_h = D - sag - arriere(sag) - flasque
    if umbo_h > r_u:
        umbo_h = r_u
        sag = D - umbo_h - flasque - e
        poignee_h = min(poignee_h, sag)  # bouclier très plat : la poignée ne doit pas dépasser la coque
    elif umbo_h < h_min:
        umbo_h = h_min
        sag = D - umbo_h - flasque - arriere(sag)
    return {"sag": sag, "umbo_h": umbo_h, "poignee_h": poignee_h}


def build(params: dict, style, seed: int = 0):
    p = B.lire_params(MANIFESTE, params, style)
    geo = geometrie(p)
    coque = _coque(p, style, geo)
    umbo = _umbo(p, style, geo)
    poignee = _poignee(p, style, geo)
    obj = B.joindre([coque, umbo, poignee], "scutum")
    point_poignee = (0.0, -geo["sag"] + p["epaisseur_m"] + geo["poignee_h"] / 2.0, p["hauteur_m"] / 2.0)
    return B.finaliser(obj, MANIFESTE, style, p, point_poignee=point_poignee)
