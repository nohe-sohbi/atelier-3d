"""Contrôles qualité sur des GLB fabriqués avec trimesh (sans bpy)."""
from __future__ import annotations

import numpy as np
import pytest
import trimesh

from pipeline import validate as va
from tests.pipeline.conftest import avec_n_tris, boite, dossier_asset, eclater, uv_grille

ID = "ROM_PROP_Caisse_A"
INFOS = {"id": ID, "categorie": "petit_prop", "dimensions_type": "caisse", "symetrique": "X",
         "pieces_declarees": 1, "licence": "CC0-1.0", "sources": []}


def caisse_lods():
    base = boite()                      # 12 tris, 0.6 x 0.4 x 0.4 m (caisse du style)
    lod0 = eclater(avec_n_tris(base, 48))
    lod1 = avec_n_tris(base, 24)
    lod2 = base
    return lod0, lod1, lod2


def valider(tmp_path, style, config, **kw):
    infos = dict(INFOS)
    infos.update(kw.pop("infos", {}))
    lod0, lod1, lod2 = caisse_lods()
    kw.setdefault("lod0", lod0)
    kw.setdefault("lod1", lod1)
    kw.setdefault("lod2", lod2)
    dossier = dossier_asset(tmp_path, ID, **kw)
    return va.valider(dossier, style, infos, config)


def test_un_cube_ferme_passe_tous_les_bloquants(tmp_path, style, config_sans_validator):
    r = valider(tmp_path, style, config_sans_validator)
    noms = [c.nom for c in r.controles]
    assert noms == list(va.NOMS_CONTROLES)
    echecs = [c.nom for c in r.controles if c.bloquant and not c.ok]
    assert echecs == [], r.to_json()
    assert r.bloquants_ok and r.statut == "accepte"
    assert r.controle("Conformité du fichier").etat == "non exécuté"
    assert r.controle("Conformité du fichier").ok is False
    assert r.controle("Conformité du fichier").bloquant is False
    assert r.controle("Critique IA").etat == "non demandée"
    assert r.controle("Densité de texels").ok, r.controle("Densité de texels").detail
    assert r.controle("Symétrie").ok and r.controle("Symétrie").mesure <= style.tolerances["symetrie_m"]
    d = r.to_dict()
    assert d["nb_controles"] == 12 and {"nom", "mesure", "seuil", "bloquant", "ok", "detail"} <= set(d["controles"][0])
    assert va.Rapport.depuis_dict(d).bloquants_ok


def test_une_face_enlevee_echoue_maillage_ferme(tmp_path, style, config_sans_validator):
    lod0, lod1, lod2 = caisse_lods()
    troue = lod0.copy()
    troue.update_faces(np.arange(len(troue.faces)) != 0)
    uv = uv_grille(troue)
    r = valider(tmp_path, style, config_sans_validator, lod0=troue, uv=uv)
    c = r.controle("Maillage fermé")
    assert not c.ok and c.mesure == 3 and "bord" in c.detail
    assert not r.bloquants_ok


def test_deux_cubes_separes(tmp_path, style, config_sans_validator):
    a = boite((0.3, 0.4, 0.4))
    a.apply_translation([-0.15, 0, 0])
    b = boite((0.3, 0.4, 0.4))
    b.apply_translation([0.15, 0, 0])
    b.apply_translation([0.02, 0, 0])  # léger jour entre les deux
    a.apply_translation([-0.01, 0, 0])
    deux = eclater(trimesh.util.concatenate([a, b]))
    r = valider(tmp_path, style, config_sans_validator, lod0=deux, lod1=avec_n_tris(boite(), 12),
                lod2=avec_n_tris(boite(), 12), infos={"symetrique": None, "dimensions_type": None,
                                                      "dimensions_m": [0.64, 0.4, 0.4]})
    c = r.controle("Pièces flottantes")
    assert not c.ok and "2 morceaux" in c.detail
    r2 = valider(tmp_path, style, config_sans_validator, lod0=deux, lod1=avec_n_tris(boite(), 12),
                 lod2=avec_n_tris(boite(), 12), infos={"pieces_declarees": 2, "symetrique": None,
                                                       "dimensions_type": None, "dimensions_m": [0.64, 0.4, 0.4]})
    assert r2.controle("Pièces flottantes").ok


def test_faces_inversees_echouent_normales(tmp_path, style, config_sans_validator):
    lod0, _, _ = caisse_lods()
    inv = lod0.copy()
    f = inv.faces.copy()
    f[:5] = f[:5][:, ::-1]
    inv.faces = f
    r = valider(tmp_path, style, config_sans_validator, lod0=inv)
    c = r.controle("Normales")
    assert not c.ok and c.mesure == 5
    tout = lod0.copy()
    tout.invert()
    r = valider(tmp_path, style, config_sans_validator, lod0=tout)
    assert not r.controle("Normales").ok


def test_dimensions_hors_tolerance(tmp_path, style, config_sans_validator):
    base = boite((0.6, 0.4, 0.5))
    lod0 = eclater(avec_n_tris(base, 48))
    r = valider(tmp_path, style, config_sans_validator, lod0=lod0, lod1=avec_n_tris(base, 24), lod2=base)
    c = r.controle("Dimensions")
    assert not c.ok and c.mesure == pytest.approx(25.0)
    assert r.controle("Dimensions").seuil == style.tolerances["dimensions_pct"]


def test_polycount_trop_haut_et_lods(tmp_path, style, config_sans_validator):
    gros = trimesh.creation.icosphere(subdivisions=4, radius=0.2)  # 5120 tris > 2000 (petit_prop)
    gros.apply_translation([0, 0, 0.2])
    r = valider(tmp_path, style, config_sans_validator, lod0=gros, uv=np.zeros((len(gros.vertices), 2)),
                infos={"dimensions_m": [0.4, 0.4, 0.4], "symetrique": None},
                lod1=trimesh.creation.icosphere(subdivisions=3), lod2=trimesh.creation.icosphere(subdivisions=2))
    c = r.controle("Polycount")
    assert not c.ok and c.mesure == 5120 and c.seuil == style.budget("petit_prop")
    # ratios LOD hors tolérance : LOD1 = LOD0
    lod0, lod1, lod2 = caisse_lods()
    r = valider(tmp_path, style, config_sans_validator, lod1=lod0)
    assert not r.controle("Polycount").ok and "HORS TOLÉRANCE" in r.controle("Polycount").detail


def test_symetrie_detecte_une_bosse(tmp_path, style, config_sans_validator):
    lod0, lod1, lod2 = caisse_lods()
    bosse = lod0.copy()
    v = bosse.vertices.copy()
    v[(v[:, 0] > 0.29) & (v[:, 2] > 0.3), 0] += 0.03  # le haut d'un seul côté tiré de 3 cm
    bosse.vertices = v
    r = valider(tmp_path, style, config_sans_validator, lod0=bosse,
                infos={"dimensions_m": [0.63, 0.4, 0.4]})
    c = r.controle("Symétrie")
    assert not c.ok and c.mesure > style.tolerances["symetrie_m"]


def test_uv_hors_carre_et_chevauchements(tmp_path, style, config_sans_validator):
    lod0, _, _ = caisse_lods()
    uv = uv_grille(lod0)
    uv[0] += 1.5
    r = valider(tmp_path, style, config_sans_validator, uv=uv)
    c = r.controle("UV")
    assert not c.ok and "1 sommets hors" in c.detail
    # tous les triangles sur la même case : chevauchement
    chev = uv_grille(lod0) * 0
    for i, f in enumerate(lod0.faces):  # triangles décalés de 1 % chacun : ils se recouvrent
        chev[f] = np.array([[0.1, 0.1], [0.5, 0.1], [0.1, 0.5]]) + i * 0.01
    r = valider(tmp_path, style, config_sans_validator, uv=chev)
    assert not r.controle("UV").ok and "paires" in r.controle("UV").detail
    # miroir volontaire : deux moitiés aux UV empilés exactement -> accepté
    moitie = uv_grille(lod0)
    moitie[lod0.faces[24:]] = moitie[lod0.faces[:24]]
    r = valider(tmp_path, style, config_sans_validator, uv=moitie)
    assert r.controle("UV").ok, r.controle("UV").detail


def test_densite_de_texels_est_une_alerte(tmp_path, style, config_sans_validator):
    r = valider(tmp_path, style, config_sans_validator, texture_px=256)
    c = r.controle("Densité de texels")
    assert not c.ok and not c.bloquant and c.etat == "alerte"
    assert r.bloquants_ok  # non bloquant


def test_export_sans_fbx_ni_lod_echoue(tmp_path, style, config_sans_validator):
    r = valider(tmp_path, style, config_sans_validator, fbx=False)
    assert not r.controle("Export").ok and "FBX absent" in r.controle("Export").detail


def test_rendus_manquants(tmp_path, style, config_sans_validator):
    r = valider(tmp_path, style, config_sans_validator, rendus=False)
    c = r.controle("Rendus")
    assert not c.ok and c.mesure.startswith("0/5")


def test_licence_hors_liste_refuse(tmp_path, style, config_sans_validator):
    r = valider(tmp_path, style, config_sans_validator, infos={"licence": "Tripo-gratuit"})
    assert not r.licence["ok"] and not r.bloquants_ok and r.statut == "refuse"
    r = valider(tmp_path, style, config_sans_validator,
                infos={"sources": [{"nom": "x", "licence": "Hunyuan3D"}]})
    assert not r.licence["ok"] and "Hunyuan3D" in r.licence["detail"]
    r = valider(tmp_path, style, config_sans_validator,
                infos={"licence": "CC-BY-4.0", "sources": [{"nom": "Kenney", "licence": "CC0-1.0"}]})
    assert r.licence["ok"]
    assert set(va.LICENCES_AUTORISEES) == {"CC0-1.0", "CC-BY-4.0", "Meshy-Pro", "ComfyUI-local"}


def test_les_infos_viennent_du_meta_json_a_defaut(tmp_path, style, config_sans_validator):
    from pipeline.meta import construire_meta
    lod0, lod1, lod2 = caisse_lods()
    meta = construire_meta(id=ID, categorie="petit_prop", voie="code", generateur="generators/caisse.py@abc",
                           dimensions_m=[0.6, 0.4, 0.4], tris_lod0=48, dimensions_type="caisse",
                           symetrique="X", pieces_declarees=1)
    dossier = dossier_asset(tmp_path, ID, lod0, lod1, lod2, meta=meta)
    r = va.valider(dossier, style, {}, config_sans_validator)
    assert r.id == ID and r.bloquants_ok, r.to_json()
    assert r.controle("Symétrie").etat == "ok"


def test_glb_absent_rapporte_proprement(tmp_path, style, config_sans_validator):
    (tmp_path / ID).mkdir()
    r = va.valider(tmp_path / ID, style, INFOS, config_sans_validator)
    assert len(r.controles) == 12 and not r.bloquants_ok
    assert "GLB absent" in r.controle("Maillage fermé").detail
