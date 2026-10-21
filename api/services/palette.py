"""Palette tirée des images d'inspiration (Nouveau style) : les couleurs dominantes, nommées, à retoucher ensuite.

Calcul local avec Pillow, gratuit et instantané : chaque image est réduite, son fond uni (la couleur de ses bords,
quand ils sont unis) est écarté, puis l'ensemble est réduit à ses couleurs dominantes. Les couleurs proches sont
fusionnées ; chacune reçoit le nom de la couleur la plus proche d'une liste de noms courants. Le style exige 8 à
12 couleurs : s'il en manque, des nuances plus claires et plus foncées des couleurs principales complètent.
"""
from __future__ import annotations

import io

import numpy as np
from PIL import Image, UnidentifiedImageError

MIN_COULEURS, MAX_COULEURS = 8, 12
MAX_IMAGES = 10
COTE_PX = 160            # chaque image est réduite à ce côté avant le calcul
PART_MIN = 0.006         # une couleur sous 0,6 % des pixels ne compte pas
FUSION_LAB = 10.0        # deux couleurs plus proches que ça (écart perceptuel) n'en font qu'une
FOND_LAB = 6.0           # pixels écartés : à moins de ça de la couleur d'un fond uni (le bruit d'un JPEG en reste loin)

# Noms courants (français) et leur couleur de référence : la couleur trouvée prend le nom le plus proche.
NOMS = {
    "noir": "#1B1B1B", "anthracite": "#3A3D40", "ardoise": "#5A6470", "fer": "#5B5E63", "gris": "#8E8E8E",
    "pierre": "#A39F93", "gris perle": "#C9C7C2", "blanc cassé": "#EDEAE2", "ivoire": "#F4EFDC", "crème": "#F0E3C0",
    "lin": "#D9CBA8", "sable": "#D6C08E", "beige": "#C8B48F", "taupe": "#8B7D6B", "ocre": "#C8902A",
    "moutarde": "#D2A81E", "or": "#C9A13B", "citron": "#E8D93A", "abricot": "#F0A860", "orange": "#E07B24",
    "terre cuite": "#B5582E", "rouille": "#9A4A22", "brique": "#A2412F", "corail": "#E9725F", "saumon": "#F2A08A",
    "rouge": "#C62F2A", "bordeaux": "#6E1F2B", "pourpre": "#6B2D4C", "prune": "#5A2D50", "lavande": "#A99BD0",
    "violet": "#6F4BA0", "indigo": "#3B3F8C", "bleu nuit": "#1F2A4D", "bleu roi": "#2B50C8", "bleu": "#3C78C4",
    "ciel": "#8FC3E8", "turquoise": "#2FB2B2", "lagon": "#1F8A8C", "menthe": "#9FD8C0", "émeraude": "#1E8C5A",
    "vert forêt": "#2E5A35", "mousse": "#6E7F3A", "olive": "#7D7A3A", "sauge": "#9AAE8C", "kaki": "#8A8452",
    "vert pomme": "#7CC242", "bronze": "#8C6A2F", "cuivre": "#B0683A", "bois": "#8A5F3A", "noyer": "#5E4130",
    "chocolat": "#4A2E22", "cuir": "#6E4A2B", "rose poudré": "#E3B6B8", "rose": "#D9708F", "marbre": "#E8E3D8",
}


class ImagesIllisibles(ValueError):
    pass


def _hex(rgb) -> str:
    return "#{:02X}{:02X}{:02X}".format(*(min(255, max(0, round(float(c)))) for c in rgb))


def _rgb(hexa: str) -> np.ndarray:
    return np.array([int(hexa[i:i + 2], 16) for i in (1, 3, 5)], dtype=np.float64)


def lab(rgb: np.ndarray) -> np.ndarray:
    """sRGB (0-255, … × 3) vers CIELAB (D65) : des distances proches de ce que l'œil perçoit."""
    c = np.asarray(rgb, dtype=np.float64) / 255.0
    c = np.where(c > 0.04045, ((c + 0.055) / 1.055) ** 2.4, c / 12.92)
    m = np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]])
    xyz = c @ m.T / np.array([0.95047, 1.0, 1.08883])
    f = np.where(xyz > 0.008856, np.cbrt(xyz), 7.787 * xyz + 16 / 116)
    return np.stack([116 * f[..., 1] - 16, 500 * (f[..., 0] - f[..., 1]), 200 * (f[..., 1] - f[..., 2])], axis=-1)


_NOMS_LAB = {nom: lab(_rgb(h)) for nom, h in NOMS.items()}


def _pixels_utiles(contenu: bytes) -> np.ndarray:
    """Les pixels d'une image, sans son fond uni (la couleur de ses bords quand ils sont unis)."""
    try:
        with Image.open(io.BytesIO(contenu)) as im:
            im = im.convert("RGBA")
            im.thumbnail((COTE_PX, COTE_PX))
            a = np.asarray(im, dtype=np.float64)
    except (UnidentifiedImageError, OSError, SyntaxError) as e:
        raise ImagesIllisibles("une des images n'est pas lisible (.png, .jpg, .webp attendus)") from e
    visibles = a[..., 3] > 128
    rgb = a[..., :3]
    bord = np.concatenate([rgb[0], rgb[-1], rgb[:, 0], rgb[:, -1]])
    garder = visibles
    bord_lab = lab(bord)
    if np.linalg.norm(bord_lab - bord_lab.mean(axis=0), axis=1).mean() < 6:  # bords unis : un fond
        fond = bord_lab.mean(axis=0)
        loin = np.linalg.norm(lab(rgb) - fond, axis=-1) > FOND_LAB
        if (garder & loin).sum() > 0.05 * garder.sum():  # pas une image toute unie
            garder = garder & loin
    return rgb[garder]


def _nommer(couleurs: list[np.ndarray]) -> list[str]:
    """Le nom courant le plus proche ; deux couleurs du même nom : la plus claire « clair », l'autre « foncé »."""
    noms = []
    for c in couleurs:
        cl = lab(c)
        noms.append(min(_NOMS_LAB, key=lambda n: float(np.linalg.norm(_NOMS_LAB[n] - cl))))
    final = list(noms)
    for nom in set(noms):
        idx = [i for i, n in enumerate(noms) if n == nom]
        if len(idx) < 2:
            continue
        idx.sort(key=lambda i: -float(lab(couleurs[i])[0]))
        suffixes = ["clair", "foncé"] if len(idx) == 2 else ["clair"] + [f"{k}" for k in range(2, len(idx))] + ["foncé"]
        for i, s in zip(idx, suffixes, strict=True):
            final[i] = f"{nom} {s}"
    return final


def depuis_images(contenus: list[bytes]) -> list[dict]:
    """8 à 12 couleurs nommées [{nom, hex}], des plus présentes aux moins présentes."""
    if not contenus:
        raise ImagesIllisibles("aucune image")
    pixels = np.concatenate([_pixels_utiles(c) for c in contenus[:MAX_IMAGES]])
    if len(pixels) == 0:
        raise ImagesIllisibles("aucune couleur trouvée dans ces images")
    cote = int(np.ceil(np.sqrt(len(pixels))))
    tableau = np.zeros((cote * cote, 3), dtype=np.uint8)
    tableau[:len(pixels)] = pixels.astype(np.uint8)
    im = Image.fromarray(tableau.reshape(cote, cote, 3), "RGB")
    reduite = im.quantize(colors=24, method=Image.Quantize.MEDIANCUT)
    pal = np.array(reduite.getpalette()[: 24 * 3], dtype=np.float64).reshape(-1, 3)
    comptes = np.bincount(np.asarray(reduite).ravel()[: len(pixels)], minlength=len(pal)).astype(np.float64)
    # Les couleurs proches fusionnent (moyenne pondérée), des plus présentes aux moins présentes.
    groupes: list[list[float | np.ndarray]] = []  # [rgb, compte]
    for i in np.argsort(-comptes):
        if comptes[i] == 0:
            continue
        for g in groupes:
            if np.linalg.norm(lab(g[0]) - lab(pal[i])) < FUSION_LAB:
                n = g[1] + comptes[i]
                g[0] = (g[0] * g[1] + pal[i] * comptes[i]) / n
                g[1] = n
                break
        else:
            groupes.append([pal[i].copy(), comptes[i]])
    total = float(comptes.sum())
    groupes.sort(key=lambda g: -g[1])
    couleurs = [g[0] for g in groupes if g[1] / total >= PART_MIN][:MAX_COULEURS]
    # Moins de 8 couleurs : des nuances graduées des couleurs principales (plus claires, plus foncées), puis des gris.
    nuances = [c + (255 - c) * f for f in (0.35, 0.6, 0.8) for c in couleurs[:3]]
    nuances += [c * f for f in (0.65, 0.4) for c in couleurs[:3]]
    nuances += [_rgb(NOMS[n]) for n in ("gris perle", "pierre", "gris", "ardoise", "anthracite", "ivoire", "noir")]
    for variante in nuances:
        if len(couleurs) >= MIN_COULEURS:
            break
        if all(np.linalg.norm(lab(variante) - lab(x)) >= FUSION_LAB for x in couleurs):
            couleurs.append(variante)
    return [{"nom": nom, "hex": _hex(c)} for nom, c in zip(_nommer(couleurs), couleurs, strict=True)]
