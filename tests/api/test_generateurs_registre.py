"""Registre des générateurs code lu sans bpy : découverte, MANIFESTE, isolation d'un script bancal."""
import re

import pytest

from api.services import generateurs_registre as reg
from tests.fabrique_generateur import ecrire_generateur, ecrire_generateur_invalide


def test_normaliser_type():
    assert reg.normaliser_type("Bouclier_rond") == "bouclier rond"
    assert reg.normaliser_type("  Râtelier d'armes ") == "ratelier d'armes"
    assert reg.normaliser_type("") == "" and reg.normaliser_type(None) == ""


def test_dossier_vide_ou_absent(tmp_path):
    assert reg.noms_disponibles(tmp_path) == []
    assert reg.manifestes(tmp_path) == ({}, {})
    assert reg.noms_disponibles(tmp_path / "nulle-part") == []
    assert reg.trouver_pour_type("caisse", racine=tmp_path) is None


def test_generateur_valide_et_recherche_par_type(tmp_path):
    ecrire_generateur(tmp_path, "caisse", types=["caisse", "coffre"])
    valides, erreurs = reg.manifestes(tmp_path)
    assert list(valides) == ["caisse"] and erreurs == {}
    assert valides["caisse"]["titre"] == "Caisse" and valides["caisse"]["variantes"]["B"]["usure"] == "forte"
    assert reg.trouver_pour_type("Coffre", valides) == "caisse"
    assert reg.trouver_pour_type("caisse", racine=tmp_path) == "caisse"
    assert reg.trouver_pour_type("amphore", valides) is None
    assert reg.types_connus(valides) == ["caisse", "coffre"]
    module = reg.charger("caisse", tmp_path)
    assert module.build({"largeur": 0.9}, None, seed=3) == {"nom": "caisse", "params": {"largeur": 0.9}, "seed": 3}


def test_un_manifeste_invalide_n_empeche_pas_les_autres(tmp_path):
    ecrire_generateur(tmp_path, "caisse")
    ecrire_generateur_invalide(tmp_path, "bancal")
    (tmp_path / "casse.py").write_text("raise RuntimeError('import impossible')\n", encoding="utf-8")
    (tmp_path / "_prive.py").write_text("MANIFESTE = {}\n", encoding="utf-8")
    valides, erreurs = reg.manifestes(tmp_path)
    assert list(valides) == ["caisse"]
    assert set(erreurs) == {"bancal", "casse"}
    assert "champs manquants" in erreurs["bancal"] and "RuntimeError" in erreurs["casse"]


def test_un_script_apparu_apres_coup_est_vu(tmp_path):
    assert reg.manifestes(tmp_path) == ({}, {})
    ecrire_generateur(tmp_path, "banc")
    assert list(reg.manifestes(tmp_path)[0]) == ["banc"]
    # Le fichier change : la nouvelle version est relue, pas un module en cache
    ecrire_generateur(tmp_path, "banc", types=["banc", "tabouret"])
    assert reg.trouver_pour_type("tabouret", racine=tmp_path) == "banc"


@pytest.mark.parametrize("casse, attendu", [
    ({"types": []}, "types doit être une liste non vide"),
    ({"types": ["Caisse"]}, "minuscules sans accent"),
    ({"categorie": "enorme"}, "categorie"),
    ({"famille": "divers"}, "famille"),
    ({"symetrique": "Z"}, "symetrique"),
    ({"pieces_declarees": 0}, "pieces_declarees"),
    ({"version": 0}, "version"),
    ({"parametres": {"x": {"type": "float"}}}, "valeur par défaut manquante"),
    ({"parametres": {"x": {"type": "couleur", "defaut": 1}}}, "type 'couleur' inconnu"),
    ({"parametres": {"x": {"type": "choix", "defaut": "c", "choix": ["a", "b"]}}}, "le défaut doit être dans choix"),
    ({"parametres": {"x": {"type": "int", "defaut": 9, "min": 0, "max": 5}}}, "sort de [min, max]"),
    ({"variantes": {"A": {}}}, "2 à 4 jeux"),
    ({"variantes": {"A": {"inconnu": 1}, "B": {}}}, "paramètres inconnus"),
])
def test_valider_manifeste_refuse(casse, attendu):
    manifeste = {
        "nom": "x", "titre": "X", "version": 1, "types": ["x"], "categorie": "petit_prop", "famille": "props",
        "dimensions_type": "x", "symetrique": None, "pieces_declarees": 1,
        "parametres": {"largeur": {"type": "float", "defaut": 0.5, "min": 0.1, "max": 1.0}},
        "variantes": {"A": {"largeur": 0.5}, "B": {"largeur": 0.8}},
    }
    manifeste.update(casse)
    with pytest.raises(reg.ManifesteInvalide, match=re.escape(attendu)):
        reg.valider_manifeste(manifeste)
