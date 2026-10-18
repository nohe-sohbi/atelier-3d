"""Registre des générateurs code.

Un générateur = un module `generators/<nom>.py` qui expose un MANIFESTE (dict) et une fonction
`build(params, style, seed=0)`. Ce registre se lit SANS bpy : l'API s'en sert pour le routage
(`trouver_pour_type`) et pour afficher les paramètres ; seul `build` a besoin de Blender.
"""
from __future__ import annotations

import importlib
import unicodedata
from pathlib import Path
from types import ModuleType
from typing import Any

MODULES_EXCLUS = {"__init__", "_base"}
CHAMPS_MANIFESTE = (
    "nom", "titre", "version", "types", "categorie", "famille", "dimensions_type",
    "symetrique", "pieces_declarees", "parametres", "variantes",
)
FAMILLES = ("armes", "outils", "props", "mobilier", "contenants", "archi")
TYPES_PARAMETRE = ("float", "int", "bool", "choix")


class ManifesteInvalide(ValueError):
    """Le MANIFESTE d'un générateur ne respecte pas le contrat."""


def normaliser_type(texte: str) -> str:
    """Minuscules, sans accent, espaces réduits : 'Bouclier' -> 'bouclier'."""
    sans_accent = unicodedata.normalize("NFKD", str(texte)).encode("ascii", "ignore").decode()
    return " ".join(sans_accent.lower().split())


def noms_disponibles() -> list[str]:
    """Noms des modules générateurs présents dans le dossier (sans les importer)."""
    dossier = Path(__file__).resolve().parent
    return sorted(
        f.stem for f in dossier.glob("*.py")
        if f.stem not in MODULES_EXCLUS and not f.stem.startswith("_")
    )


def charger(nom: str) -> ModuleType:
    """Importe le module d'un générateur (sans bpy : seul build() l'exige)."""
    if nom not in noms_disponibles():
        raise KeyError(f"générateur inconnu : {nom}")
    return importlib.import_module(f"generators.{nom}")


def valider_manifeste(m: dict[str, Any]) -> None:
    """Lève ManifesteInvalide si un champ manque ou si un paramètre n'a pas de défaut."""
    if not isinstance(m, dict):
        raise ManifesteInvalide("le MANIFESTE doit être un dictionnaire")
    manquants = [c for c in CHAMPS_MANIFESTE if c not in m]
    if manquants:
        raise ManifesteInvalide(f"champs manquants : {', '.join(manquants)}")
    if not isinstance(m["types"], (list, tuple)) or not m["types"]:
        raise ManifesteInvalide("types doit être une liste non vide")
    for t in m["types"]:
        if t != normaliser_type(t):
            raise ManifesteInvalide(f"type {t!r} : minuscules sans accent attendues")
    if m["famille"] not in FAMILLES:
        raise ManifesteInvalide(f"famille {m['famille']!r} inconnue (attendu {FAMILLES})")
    if m["symetrique"] not in ("X", "Y", None):
        raise ManifesteInvalide("symetrique doit valoir 'X', 'Y' ou None")
    if not isinstance(m["pieces_declarees"], int) or m["pieces_declarees"] < 0:
        raise ManifesteInvalide("pieces_declarees doit être un entier >= 0")
    if not isinstance(m["version"], int) or m["version"] < 1:
        raise ManifesteInvalide("version doit être un entier >= 1")
    params = m["parametres"]
    if not isinstance(params, dict):
        raise ManifesteInvalide("parametres doit être un dictionnaire")
    for nom, schema in params.items():
        if not isinstance(schema, dict) or "defaut" not in schema:
            raise ManifesteInvalide(f"paramètre {nom} : valeur par défaut manquante")
        typ = schema.get("type")
        if typ not in TYPES_PARAMETRE:
            raise ManifesteInvalide(f"paramètre {nom} : type {typ!r} inconnu")
        if typ == "choix":
            choix = schema.get("choix")
            if not choix or schema["defaut"] not in choix:
                raise ManifesteInvalide(f"paramètre {nom} : le défaut doit être dans choix")
        if typ in ("float", "int"):
            lo, hi = schema.get("min"), schema.get("max")
            if lo is not None and hi is not None and lo > hi:
                raise ManifesteInvalide(f"paramètre {nom} : min > max")
            if lo is not None and schema["defaut"] < lo or hi is not None and schema["defaut"] > hi:
                raise ManifesteInvalide(f"paramètre {nom} : le défaut sort de [min, max]")
    variantes = m["variantes"]
    if not isinstance(variantes, dict) or not (2 <= len(variantes) <= 4):
        raise ManifesteInvalide("variantes : 2 à 4 jeux de paramètres nommés attendus")
    for nom_v, jeu in variantes.items():
        if not isinstance(jeu, dict):
            raise ManifesteInvalide(f"variante {nom_v} : dictionnaire de paramètres attendu")
        inconnus = [p for p in jeu if p not in params]
        if inconnus:
            raise ManifesteInvalide(f"variante {nom_v} : paramètres inconnus {inconnus}")


def registre() -> dict[str, dict[str, Any]]:
    """{nom: MANIFESTE} de tous les générateurs du dossier, manifestes validés."""
    resultat: dict[str, dict[str, Any]] = {}
    for nom in noms_disponibles():
        module = charger(nom)
        manifeste = getattr(module, "MANIFESTE", None)
        if manifeste is None or not callable(getattr(module, "build", None)):
            raise ManifesteInvalide(f"{nom}.py : MANIFESTE et build(params, style, seed) requis")
        valider_manifeste(manifeste)
        if manifeste["nom"] != nom:
            raise ManifesteInvalide(f"{nom}.py : MANIFESTE['nom'] vaut {manifeste['nom']!r}")
        resultat[nom] = manifeste
    return resultat


def trouver_pour_type(type_objet: str) -> str | None:
    """Nom du générateur qui sait fabriquer ce type d'objet du brief, ou None."""
    cible = normaliser_type(type_objet)
    if not cible:
        return None
    for nom, manifeste in registre().items():
        if cible in manifeste["types"] or cible == nom:
            return nom
    return None
