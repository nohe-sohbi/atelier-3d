import copy

import pytest

from api.services import style_yaml as st


def _pilote(atelier):
    return st.charger(atelier.styles / "rome-stylise-v0" / "style.yaml")


def test_le_style_pilote_se_charge(atelier):
    s = _pilote(atelier)
    assert s.nom == "rome-stylise-v0" and s.theme == "ROM" and s.version == 0
    assert s.budget("prop_moyen") == 6000 and s.lod_ratios == [1.0, 0.5, 0.25]
    assert s.dimensions("scutum") == [0.65, 0.20, 1.10] and s.tolerances["dimensions_pct"] == 5
    assert 8 <= len(s.palette) <= 12 and s.description and len(s.objets_planche) == 6
    assert s.libelle_categorie("module_archi") == "Module d'architecture"


def test_materiau_resout_la_couleur(atelier):
    m = _pilote(atelier).materiau("bronze")
    assert m["metallic"] == 1.0 and len(m["rgb"]) == 3 and all(0 <= c <= 1 for c in m["rgb"])


def test_validation_refuse_un_style_bancal(atelier):
    brut = _pilote(atelier).brut
    for casse in (lambda b: b["palette"].__setitem__("bidon", "pas-une-couleur"),
                  lambda b: b["budgets_tris"].pop("petit_prop"),
                  lambda b: b["conventions"].__setitem__("haut", "+Y"),
                  lambda b: [b["palette"].pop(k) for k in list(b["palette"])[:4]]):
        b = copy.deepcopy(brut)
        casse(b)
        with pytest.raises(st.StyleInvalide):
            st.depuis_dict(b)


def test_ecrire_puis_recharger(atelier, tmp_path):
    brut = copy.deepcopy(_pilote(atelier).brut)
    brut["nom"] = "Copie"
    chemin = st.ecrire(brut, tmp_path / "x" / "style.yaml")
    assert st.charger(chemin).brut["nom"] == "Copie"
    assert chemin.read_text(encoding="utf-8").startswith("# Moodboard")
