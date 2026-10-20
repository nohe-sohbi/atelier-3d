"""Point d'entrée des scripts Blender de l'app (lancé par pipeline/blender.py).

Lit l'entrée JSON, exécute sa commande, écrit le rapport JSON : {"ok": true, ...} ou {"ok": false, "erreur": "..."}.
Tourne dans le Python de Blender : bpy, bmesh, mathutils et numpy y sont ; PyYAML et Pillow non.
"""
from __future__ import annotations

import sys
import traceback
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # racine du dépôt : api/, pipeline/, generators/

from pipeline._cli import args_apres_double_tiret, ecrire_json, lire_json

COMMANDES: dict[str, Any] = {}


def commande(nom: str):
    def enregistrer(fn):
        COMMANDES[nom] = fn
        return fn
    return enregistrer


@commande("version")
def version(entree: dict, style) -> dict:
    import bpy

    return {"version": bpy.app.version_string}


def main() -> int:
    chemin_entree, chemin_sortie = args_apres_double_tiret()[:2]
    entree = lire_json(chemin_entree)
    try:
        from api.services import style_yaml

        style = style_yaml.depuis_dict(entree["style"]) if entree.get("style") else None
        fn = COMMANDES.get(entree.get("commande"))
        if fn is None:
            raise ValueError(f"commande inconnue : {entree.get('commande')!r} (connues : {', '.join(sorted(COMMANDES))})")
        ecrire_json(chemin_sortie, {"ok": True, **fn(entree, style)})
        return 0
    except Exception as e:  # noqa: BLE001 - tout échec part dans le rapport, avec sa pile dans le journal
        traceback.print_exc()
        ecrire_json(chemin_sortie, {"ok": False, "erreur": f"{type(e).__name__}: {e}"})
        return 1


if __name__ == "__main__":
    sys.exit(main())
