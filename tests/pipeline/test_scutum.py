"""Le premier générateur, pour de vrai dans Blender : générer, finir, contrôler, rendre (tests marqués `blender`)."""
import importlib.util

import pytest

from api import chemins
from api.services import outils, style_yaml
from pipeline import blender, meta, planche, validate
from tests.pipeline.fabrique import validateur_factice

ID = "ROM_PROP_Scutum_A"


def _scutum():
    spec = importlib.util.spec_from_file_location("scutum", chemins.racine() / "generators" / "scutum.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.blender
def test_scutum_de_bout_en_bout(cfg_blender, tmp_path):
    style = style_yaml.charger(chemins.racine() / "style" / "rome-stylise-v0" / "style.yaml")
    m = _scutum().MANIFESTE
    g = blender.lancer("generer", {"fichier": str(chemins.racine() / "generators" / "scutum.py"), "params": {},
                                   "seed": 0, "id": ID, "dossier": str(tmp_path)}, cfg_blender, tmp_path, style=style)
    assert g["tris"] <= style.budget(m["categorie"]) and g["dimensions_m"] == pytest.approx(style.dimensions("scutum"))
    assert set(g["materiaux"]) <= set(style.materiaux)  # rien hors du style
    asset = tmp_path / "asset"
    f = blender.lancer("finir", {"blend": g["blend"], "dossier": str(asset), "id": ID, "infos": m},
                       cfg_blender, tmp_path, style=style)
    tolerance = style.tolerances["lod_pct"] / 100
    for i, ratio in ((1, style.lod_ratios[1]), (2, style.lod_ratios[2])):
        assert f[f"tris_lod{i}"] / f["tris_lod0"] == pytest.approx(ratio, abs=tolerance)
    # Petits rendus sur le processeur : le test ne dépend pas d'une carte graphique.
    r = blender.lancer("rendre", {"blend": str(asset / f"{ID}.blend"), "dossier": str(asset / "rendus"), "id": ID,
                                  "moteur": "cycles", "taille_px": 96}, cfg_blender, tmp_path, style=style)
    assert sorted(r["vues"]) == sorted(validate.VUES)
    planche.assembler(asset / "rendus", ID)
    (asset / "meta.json").write_text(__import__("json").dumps(meta.construire_meta(
        id=ID, categorie=m["categorie"], voie="code", generateur=meta.reference_generateur("scutum"),
        dimensions_m=f["normalisation"]["dimensions_m"], tris_lod0=f["tris_lod0"])), encoding="utf-8")
    validateur = outils.resoudre_chemin("gltf_validator") or validateur_factice(tmp_path)
    rapport = validate.valider(asset, style, {**m, "id": ID}, {"gltf_validator": {"chemin": validateur}})
    echecs = [f"{c.nom} : {c.detail}" for c in rapport.controles if c.bloquant and not c.ok]
    assert echecs == [] and rapport.statut == "accepte"
