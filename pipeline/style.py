"""Chargement et validation d'un style (style.yaml).

C'est la seule source des seuils : budgets de triangles, tolérances, palette, matériaux,
dimensions réelles par type d'objet. Aucun script ne doit recopier ces valeurs en dur.

Ce module ne dépend pas de bpy : il tourne dans l'API, le worker, les tests et Blender.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

CHAMPS_OBLIGATOIRES = (
    "style", "theme", "version", "direction", "units", "conventions", "texel_density_px_per_m",
    "palette", "materiaux", "budgets_tris", "lod_ratios", "tolerances", "dimensions_m",
)
CATEGORIES = ("petit_prop", "prop_moyen", "grand_prop", "module_archi")
_HEX = re.compile(r"^#[0-9A-Fa-f]{6}$")


class StyleInvalide(ValueError):
    """Le style.yaml ne respecte pas le schéma."""


@dataclass
class Style:
    """Un style chargé et validé. `brut` garde le dictionnaire d'origine."""

    brut: dict[str, Any]
    chemin: Path | None = None
    _rgb: dict[str, tuple[float, float, float]] = field(default_factory=dict, repr=False)

    # --- identité -------------------------------------------------------
    @property
    def nom(self) -> str:
        return str(self.brut["style"])

    @property
    def theme(self) -> str:
        return str(self.brut["theme"])

    @property
    def version(self) -> int:
        return int(self.brut["version"])

    @property
    def direction(self) -> str:
        return str(self.brut["direction"])

    # --- valeurs numériques ----------------------------------------------
    @property
    def texel_density(self) -> float:
        return float(self.brut["texel_density_px_per_m"])

    @property
    def budgets_tris(self) -> dict[str, int]:
        return {k: int(v) for k, v in self.brut["budgets_tris"].items()}

    @property
    def textures_px(self) -> dict[str, int]:
        return {k: int(v) for k, v in self.brut.get("textures_px", {}).items()}

    @property
    def lod_ratios(self) -> list[float]:
        return [float(r) for r in self.brut["lod_ratios"]]

    @property
    def tolerances(self) -> dict[str, float]:
        return {k: float(v) for k, v in self.brut["tolerances"].items()}

    @property
    def usure(self) -> dict[str, float]:
        return {k: float(v) for k, v in self.brut.get("usure", {}).items()}

    @property
    def palette(self) -> dict[str, str]:
        return dict(self.brut["palette"])

    @property
    def materiaux(self) -> dict[str, dict[str, Any]]:
        return dict(self.brut["materiaux"])

    @property
    def dimensions_m(self) -> dict[str, list[float]]:
        return {k: [float(x) for x in v] for k, v in self.brut["dimensions_m"].items()}

    @property
    def conventions(self) -> dict[str, str]:
        return dict(self.brut["conventions"])

    @property
    def pivot(self) -> dict[str, str]:
        return dict(self.brut.get("pivot", {"defaut": "sol_centre"}))

    @property
    def prompts_reference(self) -> dict[str, str]:
        return dict(self.brut.get("prompts_reference", {}))

    # --- helpers ---------------------------------------------------------
    def budget(self, categorie: str) -> int:
        try:
            return self.budgets_tris[categorie]
        except KeyError as e:
            raise StyleInvalide(f"catégorie inconnue dans budgets_tris : {categorie}") from e

    def texture_px(self, categorie: str) -> int:
        return self.textures_px.get(categorie, 1024)

    def dimensions(self, type_objet: str) -> list[float] | None:
        return self.dimensions_m.get(type_objet)

    def couleur_rgb(self, nom: str) -> tuple[float, float, float]:
        """Couleur de la palette en RGB linéaire 0-1 (approximation sRGB -> linéaire)."""
        if nom not in self._rgb:
            hexa = self.palette.get(nom)
            if hexa is None:
                raise StyleInvalide(f"couleur inconnue dans la palette : {nom}")
            srgb = tuple(int(hexa[i:i + 2], 16) / 255.0 for i in (1, 3, 5))
            self._rgb[nom] = tuple(
                c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in srgb
            )
        return self._rgb[nom]

    def materiau(self, nom: str) -> dict[str, Any]:
        """Paramètres d'un matériau partagé, couleur résolue en RGB linéaire."""
        try:
            m = dict(self.materiaux[nom])
        except KeyError as e:
            raise StyleInvalide(f"matériau inconnu : {nom}") from e
        m["rgb"] = self.couleur_rgb(m["base"])
        return m

    def pivot_pour(self, categorie_objet: str | None) -> str:
        return self.pivot.get(categorie_objet or "", self.pivot.get("defaut", "sol_centre"))


def valider(brut: dict[str, Any]) -> None:
    """Lève StyleInvalide si le dictionnaire ne respecte pas le schéma."""
    if not isinstance(brut, dict):
        raise StyleInvalide("le style doit être un dictionnaire")
    manquants = [c for c in CHAMPS_OBLIGATOIRES if c not in brut]
    if manquants:
        raise StyleInvalide(f"champs manquants : {', '.join(manquants)}")
    if brut["units"] != "meters":
        raise StyleInvalide("units doit valoir 'meters' (1 unité = 1 m)")
    if brut["direction"] not in ("stylise", "semi_realiste"):
        raise StyleInvalide("direction doit valoir 'stylise' ou 'semi_realiste'")
    conv = brut["conventions"]
    if conv.get("haut") != "+Z" or conv.get("face_avant") != "-Y":
        raise StyleInvalide("conventions : haut doit être +Z et face_avant -Y")
    palette = brut["palette"]
    if not (8 <= len(palette) <= 12):
        raise StyleInvalide(f"la palette doit avoir 8 à 12 couleurs (ici {len(palette)})")
    for nom, hexa in palette.items():
        if not isinstance(hexa, str) or not _HEX.match(hexa):
            raise StyleInvalide(f"couleur {nom} : attendu '#RRGGBB', reçu {hexa!r}")
    for nom, m in brut["materiaux"].items():
        if m.get("base") not in palette:
            raise StyleInvalide(f"matériau {nom} : base {m.get('base')!r} absente de la palette")
        for champ in ("roughness", "metallic"):
            v = m.get(champ)
            if not isinstance(v, (int, float)) or not 0 <= v <= 1:
                raise StyleInvalide(f"matériau {nom} : {champ} doit être entre 0 et 1")
    for cat in CATEGORIES:
        if cat not in brut["budgets_tris"]:
            raise StyleInvalide(f"budgets_tris : catégorie manquante {cat}")
        if int(brut["budgets_tris"][cat]) <= 0:
            raise StyleInvalide(f"budgets_tris : {cat} doit être positif")
    ratios = brut["lod_ratios"]
    if len(ratios) != 3 or ratios[0] != 1.0 or any(ratios[i] <= ratios[i + 1] for i in range(2)):
        raise StyleInvalide("lod_ratios doit être [1.0, r1, r2] décroissant")
    tol = brut["tolerances"]
    for champ in ("dimensions_pct", "texel_pct", "symetrie_m", "lod_pct"):
        if champ not in tol:
            raise StyleInvalide(f"tolerances : {champ} manquant")
    for t, dims in brut["dimensions_m"].items():
        if len(dims) != 3 or any(float(d) <= 0 for d in dims):
            raise StyleInvalide(f"dimensions_m.{t} : attendu [x, y, z] positifs")
    if float(brut["texel_density_px_per_m"]) <= 0:
        raise StyleInvalide("texel_density_px_per_m doit être positif")


def charger(chemin: str | Path) -> Style:
    """Charge et valide un style.yaml."""
    chemin = Path(chemin)
    with chemin.open("r", encoding="utf-8") as f:
        brut = yaml.safe_load(f)
    valider(brut)
    return Style(brut=brut, chemin=chemin)


def depuis_dict(brut: dict[str, Any]) -> Style:
    valider(brut)
    return Style(brut=brut)


def style_par_defaut() -> Path:
    """Le style du thème pilote, livré avec le dépôt."""
    return Path(__file__).resolve().parent.parent / "style" / "style.yaml"
