import copy

import pytest

from pipeline import style as st


def test_le_style_livre_se_charge():
    s = st.charger(st.style_par_defaut())
    assert s.theme == "ROM"
    assert s.budget("prop_moyen") == 6000
    assert s.lod_ratios == [1.0, 0.5, 0.25]
    assert s.dimensions("scutum") == [0.65, 0.20, 1.10]
    assert s.tolerances["dimensions_pct"] == 5
    assert 8 <= len(s.palette) <= 12


def test_materiau_resout_la_couleur():
    s = st.charger(st.style_par_defaut())
    m = s.materiau("bronze")
    assert m["metallic"] == 1.0
    assert len(m["rgb"]) == 3 and all(0 <= c <= 1 for c in m["rgb"])


def test_validation_refuse_un_style_bancal():
    brut = copy.deepcopy(st.charger(st.style_par_defaut()).brut)
    brut["palette"]["bidon"] = "pas-une-couleur"
    with pytest.raises(st.StyleInvalide):
        st.depuis_dict(brut)
    brut = copy.deepcopy(st.charger(st.style_par_defaut()).brut)
    del brut["budgets_tris"]["petit_prop"]
    with pytest.raises(st.StyleInvalide):
        st.depuis_dict(brut)
    brut = copy.deepcopy(st.charger(st.style_par_defaut()).brut)
    brut["conventions"]["haut"] = "+Y"
    with pytest.raises(st.StyleInvalide):
        st.depuis_dict(brut)


def test_pivot_par_categorie():
    s = st.charger(st.style_par_defaut())
    assert s.pivot_pour("armes") == "poignee"
    assert s.pivot_pour(None) == "sol_centre"
