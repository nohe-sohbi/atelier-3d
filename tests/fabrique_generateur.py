"""Un générateur code factice (MANIFESTE valide, build sans Blender) écrit dans un dossier de test."""
from __future__ import annotations

from pathlib import Path

SOURCE = '''"""Générateur de test : {nom}."""
MANIFESTE = {{
    "nom": "{nom}", "titre": "{titre}", "version": 1, "types": {types},
    "categorie": "{categorie}", "famille": "contenants", "dimensions_type": "{nom}", "symetrique": "X",
    "pieces_declarees": 1,
    "parametres": {{"largeur": {{"type": "float", "defaut": 0.6, "min": 0.3, "max": 1.2}},
                   "usure": {{"type": "choix", "defaut": "legere", "choix": ["aucune", "legere", "forte"]}}}},
    "variantes": {{"A": {{"largeur": 0.6}}, "B": {{"largeur": 0.9, "usure": "forte"}}}},
}}


def build(params, style, seed=0):
    return {{"nom": "{nom}", "params": dict(params), "seed": seed}}
'''


def ecrire_generateur(dossier: Path, nom: str = "caisse", types: list[str] | None = None,
                      categorie: str = "petit_prop", titre: str | None = None) -> Path:
    dossier.mkdir(parents=True, exist_ok=True)
    chemin = dossier / f"{nom}.py"
    chemin.write_text(SOURCE.format(nom=nom, titre=titre or nom.capitalize(), types=repr(types or [nom]),
                                    categorie=categorie), encoding="utf-8")
    return chemin


def ecrire_generateur_invalide(dossier: Path, nom: str = "bancal") -> Path:
    dossier.mkdir(parents=True, exist_ok=True)
    chemin = dossier / f"{nom}.py"
    chemin.write_text('MANIFESTE = {"nom": "' + nom + '", "titre": "Bancal"}\n\ndef build(params, style, seed=0):\n    return None\n',
                      encoding="utf-8")
    return chemin
