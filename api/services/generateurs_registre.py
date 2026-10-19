"""Registre des générateurs code (generators/<nom>.py), lu SANS bpy.

L'API s'en sert pour le routage du Brief (« un générateur sait-il faire ce type ? ») et pour détecter
qu'un script demandé à Claude Code est apparu. Un module invalide est signalé sans empêcher les autres.
"""
from __future__ import annotations

import importlib.util
import logging
import sys
import unicodedata
from pathlib import Path
from types import ModuleType
from typing import Any

from api import chemins

log = logging.getLogger("api.generateurs")

MODULES_EXCLUS = {"__init__", "_base"}
CHAMPS_MANIFESTE = (
    "nom", "titre", "version", "types", "categorie", "famille", "dimensions_type",
    "symetrique", "pieces_declarees", "parametres", "variantes",
)
FAMILLES = ("armes", "outils", "props", "mobilier", "contenants", "archi")
CATEGORIES = ("petit_prop", "prop_moyen", "grand_prop", "module_archi")
TYPES_PARAMETRE = ("float", "int", "bool", "choix")


class ManifesteInvalide(ValueError):
    """Le MANIFESTE d'un générateur ne respecte pas generators/CONTRAT.md."""


def normaliser_type(texte: str) -> str:
    """Minuscules, sans accent, espaces et tirets bas réduits : 'Bouclier_rond' -> 'bouclier rond'."""
    sans_accent = unicodedata.normalize("NFKD", str(texte or "")).encode("ascii", "ignore").decode()
    return " ".join(sans_accent.lower().replace("_", " ").replace("-", " ").split())


def dossier() -> Path:
    return chemins.dossier_generateurs()


def noms_disponibles(racine: Path | None = None) -> list[str]:
    racine = racine or dossier()
    if not racine.is_dir():
        return []
    return sorted(f.stem for f in racine.glob("*.py") if f.stem not in MODULES_EXCLUS and not f.stem.startswith("_"))


def charger(nom: str, racine: Path | None = None) -> ModuleType:
    """Importe le module d'un générateur depuis son fichier (cache invalidé : un script qui apparaît est vu)."""
    racine = racine or dossier()
    chemin = racine / f"{nom}.py"
    if not chemin.is_file():
        raise KeyError(f"générateur inconnu : {nom}")
    importlib.invalidate_caches()
    nom_module = f"atelier_generateur_{nom}"
    spec = importlib.util.spec_from_file_location(nom_module, chemin)
    if spec is None or spec.loader is None:
        raise ManifesteInvalide(f"{nom}.py : impossible à charger")
    module = importlib.util.module_from_spec(spec)
    sys.modules.pop(nom_module, None)
    spec.loader.exec_module(module)
    return module


def valider_manifeste(m: dict[str, Any]) -> None:
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
    if m["categorie"] not in CATEGORIES:
        raise ManifesteInvalide(f"categorie {m['categorie']!r} inconnue (attendu {CATEGORIES})")
    if m["famille"] not in FAMILLES:
        raise ManifesteInvalide(f"famille {m['famille']!r} inconnue (attendu {FAMILLES})")
    if m["symetrique"] not in ("X", "Y", None):
        raise ManifesteInvalide("symetrique doit valoir 'X', 'Y' ou None")
    if not isinstance(m["pieces_declarees"], int) or m["pieces_declarees"] < 1:
        raise ManifesteInvalide("pieces_declarees doit être un entier >= 1 (le nombre de pièces de l'objet)")
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
            if (lo is not None and schema["defaut"] < lo) or (hi is not None and schema["defaut"] > hi):
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


def manifestes(racine: Path | None = None) -> tuple[dict[str, dict[str, Any]], dict[str, str]]:
    """({nom: MANIFESTE valide}, {nom: erreur}) : un script bancal n'empêche pas les autres."""
    valides: dict[str, dict[str, Any]] = {}
    erreurs: dict[str, str] = {}
    for nom in noms_disponibles(racine):
        try:
            module = charger(nom, racine)
            manifeste = getattr(module, "MANIFESTE", None)
            if manifeste is None or not callable(getattr(module, "build", None)):
                raise ManifesteInvalide("MANIFESTE et build(params, style, seed) requis")
            valider_manifeste(manifeste)
            if manifeste["nom"] != nom:
                raise ManifesteInvalide(f"MANIFESTE['nom'] vaut {manifeste['nom']!r}, attendu {nom!r}")
            valides[nom] = manifeste
        except Exception as e:  # noqa: BLE001 - l'erreur d'un module est rapportée, pas propagée
            erreurs[nom] = f"{type(e).__name__}: {e}"
            log.warning("générateur %s ignoré : %s", nom, e)
    return valides, erreurs


def trouver_pour_type(type_objet: str, registre: dict[str, dict[str, Any]] | None = None,
                      racine: Path | None = None) -> str | None:
    """Nom du générateur qui sait fabriquer ce type d'objet du brief, ou None."""
    cible = normaliser_type(type_objet)
    if not cible:
        return None
    if registre is None:
        registre, _ = manifestes(racine)
    for nom, manifeste in registre.items():
        if cible == normaliser_type(nom) or cible in (normaliser_type(t) for t in manifeste["types"]):
            return nom
    return None


def types_connus(registre: dict[str, dict[str, Any]]) -> list[str]:
    out: list[str] = []
    for nom, m in registre.items():
        for t in [nom, *m["types"]]:
            t = normaliser_type(t)
            if t not in out:
                out.append(t)
    return out
