"""Construction du meta.json d'un asset (sans bpy), au format exact du cahier des charges.

Les 12 clés du modèle viennent d'abord, dans l'ordre du cahier des charges ; des champs
supplémentaires utiles (LOD, textures, style, seed, version de Blender) suivent.
"""
from __future__ import annotations

from datetime import date
from typing import Any

from pipeline._cli import commit_courant

CLES_META = (
    "id", "categorie", "voie", "generateur", "parametres", "sources", "outils_ia",
    "licence", "dimensions_m", "tris_lod0", "valide_par", "date",
)
CLES_SUPPLEMENTAIRES = (
    "tris_lod1", "tris_lod2", "tris_collision", "textures", "style", "version_style", "seed",
    "blender_version", "symetrique", "pieces_declarees", "dimensions_type", "variante",
)
VOIES = {"code": "B", "B": "B", "ia": "A", "A": "A", "mixte": "A+B", "A+B": "A+B", "cc0": "import", "import": "import"}

OUTILS_IA_CODE = {"geometrie": "code ecrit par Claude Code", "textures": "procedural"}


def reference_generateur(nom: str | None, commit: str | None = None) -> str:
    """'generators/<nom>.py@<commit>' ; commit lu via git, 'inconnu' sinon."""
    if not nom:
        return ""
    nom = nom.removesuffix(".py").split("/")[-1]
    return f"generators/{nom}.py@{commit or commit_courant()}"


def construire_meta(*, id: str, categorie: str, voie: str, generateur: str = "",
                    parametres: dict[str, Any] | None = None, sources: list[Any] | None = None,
                    outils_ia: dict[str, str] | None = None, licence: str = "CC0-1.0",
                    dimensions_m: list[float], tris_lod0: int, valide_par: str = "aucun",
                    date_iso: str | None = None, **supplements: Any) -> dict[str, Any]:
    """Le dictionnaire meta.json : les 12 clés du cahier des charges puis les suppléments."""
    voie_norm = VOIES.get(voie, voie)
    if outils_ia is None:
        outils_ia = dict(OUTILS_IA_CODE) if voie_norm == "B" else {}
    meta: dict[str, Any] = {
        "id": id,
        "categorie": categorie,
        "voie": voie_norm,
        "generateur": generateur,
        "parametres": dict(parametres or {}),
        "sources": list(sources or []),
        "outils_ia": dict(outils_ia),
        "licence": licence,
        "dimensions_m": [round(float(x), 4) for x in dimensions_m],
        "tris_lod0": int(tris_lod0),
        "valide_par": valide_par,
        "date": date_iso or date.today().isoformat(),
    }
    for cle in CLES_SUPPLEMENTAIRES:
        if cle in supplements and supplements[cle] is not None:
            meta[cle] = supplements[cle]
    for cle, val in supplements.items():
        if cle not in meta and val is not None:
            meta[cle] = val
    return meta


def verifier_meta(meta: dict[str, Any]) -> list[str]:
    """Liste des problèmes (vide si le meta.json est conforme au modèle)."""
    problemes = []
    cles = list(meta.keys())
    if cles[:len(CLES_META)] != list(CLES_META):
        manquantes = [c for c in CLES_META if c not in meta]
        problemes.append("clés manquantes ou désordonnées : " + (", ".join(manquantes) or "ordre"))
    if not isinstance(meta.get("parametres"), dict):
        problemes.append("parametres doit être un objet")
    if not isinstance(meta.get("sources"), list):
        problemes.append("sources doit être une liste")
    if not isinstance(meta.get("outils_ia"), dict):
        problemes.append("outils_ia doit être un objet")
    dims = meta.get("dimensions_m")
    if not (isinstance(dims, list) and len(dims) == 3 and all(isinstance(x, (int, float)) for x in dims)):
        problemes.append("dimensions_m doit être [x, y, z]")
    if not isinstance(meta.get("tris_lod0"), int):
        problemes.append("tris_lod0 doit être un entier")
    if meta.get("voie") not in ("A", "B", "A+B", "import"):
        problemes.append(f"voie inconnue : {meta.get('voie')!r}")
    return problemes
