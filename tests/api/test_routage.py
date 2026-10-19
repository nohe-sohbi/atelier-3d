"""Routage : les 7 règles, dans l'ordre, sur des objets classés ; une voie forcée n'est jamais écrasée."""
import pytest

from api.services import brief, routage
from api.services import generateurs_registre as reg
from tests.fabrique_generateur import ecrire_generateur


@pytest.fixture
def generateurs(atelier):
    ecrire_generateur(atelier.generateurs, "caisse", types=["caisse", "coffre"])
    valides, erreurs = reg.manifestes()
    assert erreurs == {}
    return valides


def _objet(nature, type_objet, pieces=()):
    return {"nom": type_objet.capitalize(), "type_objet": type_objet, "nature": nature, "pieces": list(pieces)}


def test_les_sept_regles_sont_en_base_dans_l_ordre(conn):
    assert [r["condition"] for r in routage.regles(conn)] == list(routage.CONDITIONS)
    assert [r["voie"] for r in routage.regles(conn)] == ["reutilise", "cc0", "code", "mixte", "ia", "a_creer", "hors_perimetre"]
    assert all(r["actif"] == 1 for r in routage.regles(conn))


def test_geometrique_avec_generateur_va_en_code(conn, generateurs):
    d = routage.router(conn, _objet("geometrique", "coffre"), generateurs)
    assert d["voie"] == "code" and d["generateur"] == "caisse" and d["regle_id"] == 3


def test_geometrique_sans_generateur_est_a_creer(conn, generateurs):
    d = routage.router(conn, _objet("geometrique", "ratelier"), generateurs)
    assert d["voie"] == "a_creer" and d["generateur"] is None and d["regle_id"] == 6
    assert "Claude Code" in d["raison"] and "voie IA" in d["raison"]


def test_ornemental_va_en_ia(conn, generateurs):
    d = routage.router(conn, _objet("ornemental", "amphore"), generateurs)
    assert d["voie"] == "ia" and d["generateur"] == "meshy" and d["regle_id"] == 5


def test_mixte_deux_pieces_code_et_ia(conn, generateurs):
    pieces = [{"nom": "Fût", "nature": "geometrique", "type_objet": "coffre"},
              {"nom": "Chapiteau", "nature": "ornemental", "type_objet": "chapiteau"}]
    d = routage.router(conn, _objet("mixte", "colonne", pieces), generateurs)
    assert d["voie"] == "mixte" and d["regle_id"] == 4
    assert [(p["voie"], p["generateur"]) for p in d["pieces"]] == [("code", "caisse"), ("ia", "meshy")]
    assert d["raison"] == "2 pièces : fût en code, chapiteau en IA"


def test_mixte_sans_generateur_pour_la_piece_geometrique_est_a_creer(conn, generateurs):
    pieces = [{"nom": "Fût", "nature": "geometrique", "type_objet": "fut cannele"},
              {"nom": "Chapiteau", "nature": "ornemental", "type_objet": "chapiteau"}]
    d = routage.router(conn, _objet("mixte", "colonne", pieces), generateurs)
    assert d["voie"] == "a_creer" and d["generateur"] is None and d["regle_id"] == 4
    assert d["pieces"][0]["voie"] == "a_creer" and d["pieces"][1]["voie"] == "ia"
    assert "fût" in d["raison"] and "Claude Code" in d["raison"]


def test_personnage_hors_perimetre(conn, generateurs):
    d = routage.router(conn, _objet("personnage", "legionnaire"), generateurs)
    assert d["voie"] == "hors_perimetre" and d["regle_id"] == 7 and "hors périmètre" in d["raison"].lower()


def test_la_bibliotheque_passe_avant_le_code(conn, generateurs):
    conn.execute("INSERT INTO lots(nom, theme, cree_le, maj_le) VALUES ('Vie du camp', 'ROM', 'x', 'x')")
    conn.execute("INSERT INTO objets(lot_id, nom, type_objet, etape) VALUES (1, 'Caisse', 'caisse', 'garde')")
    conn.execute("INSERT INTO assets(id, lot_id, objet_id, nom, theme, statut, cree_le, maj_le) "
                 "VALUES ('ROM_PROP_Caisse_A', 1, 1, 'Caisse', 'ROM', 'garde', 'x', 'x')")
    conn.execute("INSERT INTO assets(id, nom, theme, statut, cree_le, maj_le) VALUES ('ROM_PROP_Tente_A', 'Tente', 'ROM', 'revue', 'x', 'x')")
    conn.commit()
    d = routage.router(conn, _objet("geometrique", "caisse"), generateurs)
    assert d["voie"] == "reutilise" and d["regle_id"] == 1 and d["reutilise_asset_id"] == "ROM_PROP_Caisse_A"
    assert d["raison"] == "Déjà dans ta bibliothèque (lot Vie du camp) : réutilisée telle quelle"
    # un asset seulement en revue ne compte pas
    assert routage.router(conn, _objet("ornemental", "tente"), generateurs)["voie"] == "ia"


def test_regle_cc0_sans_catalogue_ne_s_applique_pas(conn, generateurs):
    assert routage.catalogue_cc0(conn, "caisse") is None
    assert routage.router(conn, _objet("geometrique", "coffre"), generateurs)["voie"] == "code"


def test_regle_desactivee_est_sautee(conn, generateurs):
    conn.execute("UPDATE regles_routage SET actif = 0 WHERE condition = 'ornemental'")
    conn.commit()
    d = routage.router(conn, _objet("ornemental", "amphore"), generateurs)
    assert d["voie"] == "a_creer" and d["regle_id"] is None and "Aucune règle" in d["raison"]
    # Les autres règles marchent toujours
    assert routage.router(conn, _objet("geometrique", "coffre"), generateurs)["voie"] == "code"


def test_aucune_regle_applicable_reste_honnete(conn, generateurs):
    conn.execute("UPDATE regles_routage SET actif = 0")
    conn.commit()
    d = routage.router(conn, _objet("ornemental", "amphore"), generateurs)
    assert d["voie"] == "a_creer" and d["regle_id"] is None and "Aucune règle" in d["raison"]


def test_voie_forcee_jamais_ecrasee(conn, generateurs):
    forcee = {"voie": "ia", "generateur": "meshy", "raison_voie": "Voie choisie à la main"}
    d = brief.router_objet(conn, _objet("geometrique", "coffre"), generateurs, forcee)
    assert d["voie"] == "ia" and d["forcee"] is True and d["regle_id"] is None
    assert brief.router_objet(conn, _objet("geometrique", "coffre"), generateurs)["voie"] == "code"


def test_route_regles_lecture(client, atelier):
    ecrire_generateur(atelier.generateurs, "caisse")
    r = client.get("/api/routage/regles").json()
    assert [x["ordre"] for x in r["regles"]] == [1, 2, 3, 4, 5, 6, 7]
    assert r["regles"][1]["operationnelle"] is False and r["regles"][2]["operationnelle"] is True
    assert r["regles"][5]["generateur_secours"] == "meshy"
    assert r["generateurs_code"] == [{"nom": "caisse", "titre": "Caisse", "types": ["caisse"]}] and r["generateurs_invalides"] == {}
