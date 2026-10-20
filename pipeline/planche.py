"""Planche de contact et vignette d'un asset (Pillow, hors de Blender : son Python n'a pas Pillow)."""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

VUES = ("face", "dos", "profil", "trois_quarts", "dessus")
LIBELLES = {"face": "Face", "dos": "Dos", "profil": "Profil", "trois_quarts": "Trois-quarts", "dessus": "Dessus"}
TAILLE_VIGNETTE = 256
MARGE = 8
BANDEAU = 28
COULEUR_FOND = (245, 244, 241)   # fond clair de l'app
COULEUR_TEXTE = (29, 28, 26)


def assembler(dossier_rendus: str | Path, titre: str) -> dict[str, str]:
    """planche.png (les 5 vues côte à côte, nommées, sous le titre) et vignette.png (trois-quarts réduite)."""
    dossier = Path(dossier_rendus)
    vues = [Image.open(dossier / f"{v}.png").convert("RGB") for v in VUES]
    cote = vues[0].width
    largeur = len(vues) * cote + (len(vues) + 1) * MARGE
    hauteur = BANDEAU + cote + BANDEAU + 2 * MARGE
    planche = Image.new("RGB", (largeur, hauteur), COULEUR_FOND)
    dessin = ImageDraw.Draw(planche)
    dessin.text((MARGE, MARGE), titre, fill=COULEUR_TEXTE)
    for i, (nom, image) in enumerate(zip(VUES, vues, strict=True)):
        x = MARGE + i * (cote + MARGE)
        planche.paste(image.resize((cote, cote)), (x, BANDEAU + MARGE))
        dessin.text((x, BANDEAU + MARGE + cote + 6), LIBELLES[nom], fill=COULEUR_TEXTE)
    planche.save(dossier / "planche.png")
    vignette = vues[VUES.index("trois_quarts")].copy()
    vignette.thumbnail((TAILLE_VIGNETTE, TAILLE_VIGNETTE))
    vignette.save(dossier / "vignette.png")
    return {"planche": "planche.png", "vignette": "vignette.png"}
