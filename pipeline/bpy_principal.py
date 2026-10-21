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


def charger_generateur(fichier: str):
    """Le module d'un générateur, chargé depuis son fichier (generators/<nom>.py ou un dossier de test)."""
    import importlib.util

    chemin = Path(fichier)
    spec = importlib.util.spec_from_file_location(f"atelier_generateur_{chemin.stem}", chemin)
    if spec is None or spec.loader is None:
        raise ValueError(f"générateur illisible : {chemin}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@commande("generer")
def generer(entree: dict, style) -> dict:
    """Construit l'objet avec son générateur, l'enregistre en generation.blend et rapporte ce qui a été fait.

    entree : fichier (le .py du générateur), params, seed, id (nom de l'objet), dossier (de l'essai).
    """
    import bpy

    from pipeline import _bpy as P

    P.scene_vide()
    module = charger_generateur(entree["fichier"])
    params = {**dict(entree.get("params") or {}), "id": entree["id"]}
    obj = module.build(params, style, int(entree.get("seed", 0)))
    if isinstance(obj, list | tuple):
        obj = obj[0]
    dossier = Path(entree["dossier"])
    dossier.mkdir(parents=True, exist_ok=True)
    blend = dossier / "generation.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(blend))
    mini, maxi = P.boite(obj)
    m = module.MANIFESTE
    return {
        "blend": str(blend), "objet": obj.name, "tris": P.compter_tris(obj),
        "dimensions_m": [round(float(x), 4) for x in (maxi - mini)],
        "materiaux": [mat.name for mat in obj.data.materials if mat is not None],
        "generateur": {"nom": m["nom"], "version": m["version"]},
        "params": {k: v for k, v in dict(obj.items()).items() if isinstance(v, int | float | str)},
    }


@commande("importer")
def importer(entree: dict, style) -> dict:
    """Voie IA et import : le GLB reçu (Meshy, ComfyUI, pack CC0) devient generation.blend, comme une génération.

    entree : glb (le fichier reçu), id (nom de l'objet), dossier (de l'essai).
    """
    import bpy

    from pipeline import _bpy as P
    from pipeline import normalize

    P.scene_vide()
    obj = normalize.importer_glb(entree["glb"], nom=entree["id"])
    dossier = Path(entree["dossier"])
    dossier.mkdir(parents=True, exist_ok=True)
    blend = dossier / "generation.blend"
    bpy.ops.file.pack_all()  # les textures du GLB voyagent avec le .blend
    bpy.ops.wm.save_as_mainfile(filepath=str(blend))
    mini, maxi = P.boite(obj)
    return {
        "blend": str(blend), "objet": obj.name, "tris": P.compter_tris(obj),
        "dimensions_m": [round(float(x), 4) for x in (maxi - mini)],
        "materiaux": [mat.name for mat in obj.data.materials if mat is not None],
        "images": sorted(i.name for i in bpy.data.images if i.size[0]),
    }


@commande("finir")
def finir(entree: dict, style) -> dict:
    """Finition commune : entree = blend (de la génération), dossier (de l'asset), id, infos, voie."""
    from pipeline import finition

    return finition.finir(entree["blend"], entree["dossier"], entree["id"], style, entree["infos"],
                          entree.get("voie", "code"))


@commande("rendre")
def rendre(entree: dict, style) -> dict:
    """Les 5 vues du LOD0 : entree = blend (de l'asset), dossier (des rendus), id, moteur (eevee | cycles)."""
    from pipeline import rendu

    return rendu.rendre(entree["blend"], entree["dossier"], entree["id"], entree.get("moteur", "eevee"),
                        int(entree.get("taille_px") or rendu.TAILLE_PX))


@commande("apercus")
def apercus(entree: dict, style) -> dict:
    """Variantes d'un générateur, une image chacune, dans un seul lancement de Blender (écran Références).

    entree : fichier (le .py du générateur), variantes ([{params, seed, sortie}]), moteur, taille_px. Une variante que
    le générateur refuse (paramètres incompatibles) est rapportée en échec ; une erreur de rendu arrête tout (l'appelant
    réessaie avec Cycles).
    """
    from pipeline import _bpy as P
    from pipeline import rendu

    module = charger_generateur(entree["fichier"])
    resultats = []
    for v in entree["variantes"]:
        P.scene_vide()
        try:
            obj = module.build({**dict(v.get("params") or {}), "id": "apercu"}, style, int(v.get("seed", 0)))
        except Exception as e:  # noqa: BLE001 - un jeu de paramètres refusé n'empêche pas les autres
            resultats.append({"ok": False, "erreur": f"{type(e).__name__}: {e}"})
            continue
        if isinstance(obj, list | tuple):
            obj = obj[0]
        rendu.apercu(obj, v["sortie"], entree.get("moteur", "eevee"), int(entree.get("taille_px") or 384))
        mini, maxi = P.boite(obj)
        resultats.append({"ok": True, "sortie": v["sortie"], "tris": P.compter_tris(obj),
                          "dimensions_m": [round(float(x), 4) for x in (maxi - mini)]})
    return {"variantes": resultats, "moteur": entree.get("moteur", "eevee")}


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
