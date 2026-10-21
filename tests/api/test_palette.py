"""Palette tirée des images d'inspiration (Nouveau style) : couleurs dominantes nommées, fond ignoré, 8 à 12."""
import io

import numpy as np
from PIL import Image, ImageDraw

from api.services import palette


def _image(couleurs, fond=(255, 255, 255), format_="PNG") -> bytes:
    im = Image.new("RGB", (400, 300), fond)
    d = ImageDraw.Draw(im)
    for i, c in enumerate(couleurs):
        d.rectangle((40 + i * 80, 60, 100 + i * 80, 240), fill=c)
    tampon = io.BytesIO()
    im.save(tampon, format_, **({"quality": 85} if format_ == "JPEG" else {}))
    return tampon.getvalue()


def _proche(hexa: str, rgb) -> bool:
    return float(np.linalg.norm(palette.lab(palette._rgb(hexa)) - palette.lab(np.array(rgb, dtype=float)))) < 4


def test_les_couleurs_des_images_sans_leur_fond_nommees_et_au_moins_8():
    vraies = [(181, 88, 46), (140, 106, 47), (107, 45, 76), (91, 94, 99), (232, 227, 216)]
    p = palette.depuis_images([_image(vraies[:3], format_="JPEG"), _image(vraies[3:], fond=(250, 250, 250))])
    assert palette.MIN_COULEURS <= len(p) <= palette.MAX_COULEURS
    for rgb in vraies:  # chaque vraie couleur est là, même la très claire posée sur un fond presque blanc
        assert any(_proche(c["hex"], rgb) for c in p), rgb
    assert not any(_proche(c["hex"], (255, 255, 255)) or _proche(c["hex"], (250, 250, 250)) for c in p)  # pas le fond
    noms = [c["nom"] for c in p]
    assert len(set(noms)) == len(noms)
    assert {"terre cuite", "bronze", "fer", "marbre"} <= set(noms)  # le nom courant le plus proche


def test_une_image_toute_unie_garde_sa_couleur():
    p = palette.depuis_images([_image([], fond=(46, 90, 53))])
    assert _proche(p[0]["hex"], (46, 90, 53)) and len(p) >= palette.MIN_COULEURS


def test_route_palette(client):
    r = client.post("/api/styles/palette", files=[("fichiers", ("a.png", _image([(181, 88, 46)]), "image/png")),
                                                 ("fichiers", ("b.jpg", _image([(107, 45, 76)], format_="JPEG"), "image/jpeg"))])
    assert r.status_code == 200 and r.json()["images"] == 2 and len(r.json()["palette"]) >= 8
    r = client.post("/api/styles/palette", files=[("fichiers", ("notes.png", b"pas une image", "image/png"))])
    assert r.status_code == 422 and "pas lisible" in r.json()["erreur"]
