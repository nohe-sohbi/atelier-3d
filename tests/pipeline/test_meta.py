from pipeline import meta as me


def test_meta_json_a_les_cles_exactes_dans_l_ordre():
    m = me.construire_meta(id="ROM_PROP_Scutum_A", categorie="prop_moyen", voie="code",
                           generateur=me.reference_generateur("scutum", "abc1234"),
                           parametres={"hauteur_m": 1.1, "courbure": 0.35}, dimensions_m=[0.65, 0.2, 1.1],
                           tris_lod0=3200, tris_lod1=1600, seed=0, blender_version="5.2.2 LTS")
    assert list(m)[:12] == list(me.CLES_META)
    assert m["voie"] == "B" and m["generateur"] == "generators/scutum.py@abc1234"
    assert m["outils_ia"] == {"geometrie": "code ecrit par Claude Code", "textures": "procedural"}
    assert m["licence"] == "CC0-1.0" and m["sources"] == [] and m["valide_par"] == "aucun"
    assert m["tris_lod1"] == 1600 and m["seed"] == 0
    assert me.verifier_meta(m) == []


def test_reference_generateur_lit_le_commit():
    ref = me.reference_generateur("scutum")
    assert ref.startswith("generators/scutum.py@") and len(ref.split("@")[1]) >= 4


def test_verifier_meta_signale_les_ecarts():
    m = me.construire_meta(id="X", categorie="petit_prop", voie="ia", dimensions_m=[1, 1, 1], tris_lod0=3)
    assert m["voie"] == "A" and m["outils_ia"] == {}
    del m["licence"]
    assert any("manquantes" in p for p in me.verifier_meta(m))
