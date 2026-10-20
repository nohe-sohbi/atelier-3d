"""Les 12 contrôles sur des GLB fabriqués avec trimesh (sans Blender ; repris de l'archive et adaptés)."""
from __future__ import annotations

import numpy as np
import pytest
import trimesh

from api import chemins
from api.services import style_yaml
from pipeline import validate as va
from pipeline.meta import construire_meta
from tests.pipeline.fabrique import (
    avec_n_tris,
    boite,
    dossier_asset,
    eclater,
    uv_grille,
    validateur_factice,
)

ID = "ROM_PROP_Caisse_A"
INFOS = {"id": ID, "categorie": "petit_prop", "dimensions_type": "caisse", "symetrique": "X",
         "pieces_declarees": 1, "sources": []}


@pytest.fixture(scope="module")
def style():
    return style_yaml.charger(chemins.racine() / "style" / "rome-stylise-v0" / "style.yaml")


@pytest.fixture
def config(tmp_path):
    return {"gltf_validator": {"chemin": validateur_factice(tmp_path)}}


def caisse_lods():
    base = boite()                      # 12 tris, 0,6 x 0,4 x 0,4 m (la caisse du style)
    return eclater(avec_n_tris(base, 48)), avec_n_tris(base, 24), base


def valider(tmp_path, style, config, **kw):
    infos = {**INFOS, **kw.pop("infos", {})}
    lod0, lod1, lod2 = caisse_lods()
    kw.setdefault("lod0", lod0)
    kw.setdefault("lod1", lod1)
    kw.setdefault("lod2", lod2)
    return va.valider(dossier_asset(tmp_path, ID, **kw), style, infos, config)


def test_un_cube_ferme_passe_tous_les_bloquants(tmp_path, style, config):
    r = valider(tmp_path, style, config)
    assert [c.nom for c in r.controles] == list(va.NOMS_CONTROLES)
    assert [c.nom for c in r.controles if c.bloquant and not c.ok] == [], r.to_json()
    assert r.bloquants_ok and r.statut == "accepte"
    assert r.controle("Conformité du fichier").detail.startswith("0 erreurs")
    assert r.controle("Critique IA").etat == "non demandée"
    assert r.controle("Densité de texels").ok, r.controle("Densité de texels").detail
    assert r.controle("Dimensions").ok, r.controle("Dimensions").detail  # GLB en Y vers le haut, relu en Z
    d = r.to_dict()
    assert d["nb_controles"] == 12 and va.Rapport.depuis_dict(d).bloquants_ok


def test_sans_gltf_validator_le_controle_bloque(tmp_path, style):
    r = valider(tmp_path, style, {"gltf_validator": {"chemin": "gltf_validator_absent_pour_le_test"}})
    c = r.controle("Conformité du fichier")
    assert c.bloquant and not c.ok and c.etat == "non exécuté" and "Réglages" in c.detail
    assert not r.bloquants_ok


def test_une_erreur_gltf_bloque(tmp_path, style):
    r = valider(tmp_path, style, {"gltf_validator": {"chemin": validateur_factice(tmp_path, erreurs=2)}})
    c = r.controle("Conformité du fichier")
    assert not c.ok and c.mesure == 2 and "erreur factice" in c.detail


def test_une_face_enlevee_echoue_maillage_ferme(tmp_path, style, config):
    lod0, _, _ = caisse_lods()
    troue = lod0.copy()
    troue.update_faces(np.arange(len(troue.faces)) != 0)
    r = valider(tmp_path, style, config, lod0=troue, uv=uv_grille(troue))
    c = r.controle("Maillage fermé")
    assert not c.ok and c.mesure == 3 and "bord" in c.detail and not r.bloquants_ok


def test_deux_cubes_separes(tmp_path, style, config):
    a = boite((0.3, 0.4, 0.4))
    a.apply_translation([-0.16, 0, 0])
    b = boite((0.3, 0.4, 0.4))
    b.apply_translation([0.17, 0, 0])
    deux = eclater(trimesh.util.concatenate([a, b]))
    infos = {"symetrique": None, "dimensions_type": None, "dimensions_m": [0.63, 0.4, 0.4]}
    autres = {"lod1": avec_n_tris(boite(), 12), "lod2": avec_n_tris(boite(), 12)}
    c = valider(tmp_path, style, config, lod0=deux, infos=infos, **autres).controle("Pièces flottantes")
    assert not c.ok and "2 morceaux" in c.detail
    r = valider(tmp_path, style, config, lod0=deux, infos={**infos, "pieces_declarees": 2}, **autres)
    assert r.controle("Pièces flottantes").ok


def test_faces_inversees_echouent_normales(tmp_path, style, config):
    lod0, _, _ = caisse_lods()
    inv = lod0.copy()
    f = inv.faces.copy()
    f[:5] = f[:5][:, ::-1]
    inv.faces = f
    c = valider(tmp_path, style, config, lod0=inv).controle("Normales")
    assert not c.ok and c.mesure == 5
    tout = lod0.copy()
    tout.invert()
    assert not valider(tmp_path, style, config, lod0=tout).controle("Normales").ok


def test_dimensions_hors_tolerance(tmp_path, style, config):
    base = boite((0.6, 0.4, 0.5))
    c = valider(tmp_path, style, config, lod0=eclater(avec_n_tris(base, 48)), lod1=avec_n_tris(base, 24),
                lod2=base).controle("Dimensions")
    assert not c.ok and c.mesure == pytest.approx(25.0) and c.seuil == style.tolerances["dimensions_pct"]


def test_polycount_trop_haut_et_lods(tmp_path, style, config):
    gros = trimesh.creation.icosphere(subdivisions=4, radius=0.2)  # 5 120 tris > 2 000 (petit_prop)
    gros.apply_translation([0, 0, 0.2])
    c = valider(tmp_path, style, config, lod0=gros, uv=np.zeros((len(gros.vertices), 2)),
                infos={"dimensions_m": [0.4, 0.4, 0.4], "symetrique": None},
                lod1=trimesh.creation.icosphere(subdivisions=3),
                lod2=trimesh.creation.icosphere(subdivisions=2)).controle("Polycount")
    assert not c.ok and c.mesure == 5120 and c.seuil == style.budget("petit_prop")
    lod0, _, _ = caisse_lods()
    c = valider(tmp_path, style, config, lod1=lod0).controle("Polycount")  # LOD1 = LOD0 : ratio hors tolérance
    assert not c.ok and "HORS TOLÉRANCE" in c.detail


def test_symetrie_detecte_une_bosse(tmp_path, style, config):
    lod0, _, _ = caisse_lods()
    bosse = lod0.copy()
    v = bosse.vertices.copy()
    v[(v[:, 0] > 0.29) & (v[:, 2] > 0.3), 0] += 0.03  # le haut d'un seul côté tiré de 3 cm
    bosse.vertices = v
    c = valider(tmp_path, style, config, lod0=bosse, infos={"dimensions_m": [0.63, 0.4, 0.4]}).controle("Symétrie")
    assert not c.ok and c.mesure > style.tolerances["symetrie_m"]


def test_uv_hors_carre_chevauchements_et_miroir(tmp_path, style, config):
    lod0, _, _ = caisse_lods()
    uv = uv_grille(lod0)
    uv[0] += 1.5
    c = valider(tmp_path, style, config, uv=uv).controle("UV")
    assert not c.ok and "1 sommets hors" in c.detail
    chev = uv_grille(lod0) * 0
    for i, f in enumerate(lod0.faces):  # triangles décalés de 1 % chacun : ils se recouvrent
        chev[f] = np.array([[0.1, 0.1], [0.5, 0.1], [0.1, 0.5]]) + i * 0.01
    assert not valider(tmp_path, style, config, uv=chev).controle("UV").ok
    moitie = uv_grille(lod0)
    moitie[lod0.faces[24:]] = moitie[lod0.faces[:24]]  # miroir volontaire : UV empilés exactement
    assert valider(tmp_path, style, config, uv=moitie).controle("UV").ok


def test_densite_de_texels_est_une_alerte(tmp_path, style, config):
    r = valider(tmp_path, style, config, texture_px=256)
    c = r.controle("Densité de texels")
    assert not c.ok and not c.bloquant and c.etat == "alerte" and r.bloquants_ok


def test_sans_texture_la_densite_ne_s_invente_pas(tmp_path, style, config):
    c = valider(tmp_path, style, config, texture_px=None).controle("Densité de texels")
    assert c.mesure is None and c.etat == "non exécuté" and "aucune texture" in c.detail


def test_export_sans_fbx_et_rendus_manquants(tmp_path, style, config):
    assert "FBX absent" in valider(tmp_path, style, config, fbx=False).controle("Export").detail
    c = valider(tmp_path, style, config, rendus=False).controle("Rendus")
    assert not c.ok and c.mesure.startswith("0/5")


def test_licences(tmp_path, style, config):
    r = valider(tmp_path, style, config)
    assert r.licence["ok"] and "à choisir" in r.licence["detail"]  # choisie à la publication (étape 10)
    r = valider(tmp_path, style, config, infos={"licence": "Tripo-gratuit"})
    assert not r.licence["ok"] and r.statut == "refuse"
    r = valider(tmp_path, style, config, infos={"sources": [{"nom": "x", "licence": "Hunyuan3D"}]})
    assert not r.licence["ok"] and "Hunyuan3D" in r.licence["detail"]
    r = valider(tmp_path, style, config, infos={"sources": [{"nom": "Kenney", "licence": "CC0-1.0"}]})
    assert r.licence["ok"]


def test_les_infos_viennent_du_meta_json_a_defaut(tmp_path, style, config):
    lod0, lod1, lod2 = caisse_lods()
    meta = construire_meta(id=ID, categorie="petit_prop", voie="code", generateur="generators/caisse.py@abc",
                           dimensions_m=[0.6, 0.4, 0.4], tris_lod0=48, dimensions_type="caisse",
                           symetrique="X", pieces_declarees=1)
    r = va.valider(dossier_asset(tmp_path, ID, lod0, lod1, lod2, meta=meta), style, {}, config)
    assert r.id == ID and r.bloquants_ok, r.to_json()


def test_glb_absent_rapporte_proprement(tmp_path, style, config):
    (tmp_path / ID).mkdir()
    r = va.valider(tmp_path / ID, style, INFOS, config)
    assert len(r.controles) == 12 and not r.bloquants_ok and "GLB absent" in r.controle("Maillage fermé").detail
