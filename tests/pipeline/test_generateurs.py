"""Les générateurs livrés, pour de vrai dans Blender : générer, finir, contrôler, rendre (tests marqués `blender`)."""
import json

import pytest

from api import chemins
from api.services import generateurs_registre, outils, style_yaml
from pipeline import blender, meta, planche, validate
from tests.pipeline.fabrique import validateur_factice

LIVRES = ["amphore", "caisse", "colonne", "gladius", "pilum", "scutum"]


def _style():
    return style_yaml.charger(chemins.racine() / "style" / "rome-stylise-v0" / "style.yaml")


def test_les_six_generateurs_livres_sont_valides_pour_le_theme_pilote():
    valides, erreurs = generateurs_registre.manifestes(chemins.racine() / "generators")
    assert erreurs == {} and sorted(valides) == LIVRES
    style = _style()
    for nom, m in valides.items():
        assert style.dimensions(m["dimensions_type"]), f"{nom} : dimensions absentes du style"
        assert style.budget(m["categorie"]) > 0
        assert generateurs_registre.trouver_pour_type(nom, valides) == nom


@pytest.mark.blender
@pytest.mark.parametrize("nom", LIVRES)
def test_generateur_de_bout_en_bout(nom, cfg_blender, tmp_path):
    style = _style()
    m = generateurs_registre.charger(nom, chemins.racine() / "generators").MANIFESTE
    ident = f"ROM_PROP_{nom.capitalize()}_A"
    fichier = chemins.racine() / "generators" / f"{nom}.py"
    g = blender.lancer("generer", {"fichier": str(fichier), "params": m["variantes"]["A"], "seed": 0, "id": ident,
                                   "dossier": str(tmp_path)}, cfg_blender, tmp_path, style=style)
    assert g["tris"] <= style.budget(m["categorie"])
    assert g["dimensions_m"] == pytest.approx(style.dimensions(m["dimensions_type"]), abs=1e-3)  # au millimètre près
    assert set(g["materiaux"]) <= set(style.materiaux)  # rien hors du style
    asset = tmp_path / "asset"
    f = blender.lancer("finir", {"blend": g["blend"], "dossier": str(asset), "id": ident, "infos": m},
                       cfg_blender, tmp_path, style=style)
    tolerance = style.tolerances["lod_pct"] / 100
    for i, ratio in ((1, style.lod_ratios[1]), (2, style.lod_ratios[2])):
        assert f[f"tris_lod{i}"] / f["tris_lod0"] == pytest.approx(ratio, abs=tolerance)
    # Petits rendus sur le processeur : le test ne dépend pas d'une carte graphique.
    r = blender.lancer("rendre", {"blend": str(asset / f"{ident}.blend"), "dossier": str(asset / "rendus"), "id": ident,
                                  "moteur": "cycles", "taille_px": 96}, cfg_blender, tmp_path, style=style)
    assert sorted(r["vues"]) == sorted(validate.VUES)
    planche.assembler(asset / "rendus", ident)
    (asset / "meta.json").write_text(json.dumps(meta.construire_meta(
        id=ident, categorie=m["categorie"], voie="code", generateur=meta.reference_generateur(nom),
        dimensions_m=f["normalisation"]["dimensions_m"], tris_lod0=f["tris_lod0"])), encoding="utf-8")
    validateur = outils.resoudre_chemin("gltf_validator") or validateur_factice(tmp_path)
    rapport = validate.valider(asset, style, {**m, "id": ident}, {"gltf_validator": {"chemin": validateur}})
    echecs = [f"{c.nom} : {c.detail}" for c in rapport.controles if c.bloquant and not c.ok]
    assert echecs == [] and rapport.statut == "accepte"
