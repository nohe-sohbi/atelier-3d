"""Proposition de liste (B2) : tâche `proposer_liste`, Claude simulé, validation du JSON, re-proposition."""
import json

import pytest

from api.adapters.claude.simule import ClaudeSimule, proposition_brief_simulee
from api.services import brief, taches
from api.services import generateurs_registre as reg
from api.services import styles as styles_svc
from api.services.taches import TacheDefinitive
from tests.fabrique_generateur import ecrire_generateur
from worker import handlers
from worker.main import Worker

BESOIN = "Un camp de légionnaires : armes, mobilier, contenants et un peu de décor."


def _lot(client, **corps):
    r = client.post("/api/lots", json={"nom": "", "theme": "Rome antique", "besoin": BESOIN, **corps})
    assert r.status_code == 201, r.text
    return r.json()


def _worker_tourne(cfg):
    w = Worker(verrou="test", tick_s=0.05, backoff_base_s=0, charger_config=lambda: cfg)
    try:
        w.tour()
        assert w.attendre_fin(30)
    finally:
        w.arreter(delai_s=1)


def _proposer(client, conn, cfg, lot_id):
    r = client.post(f"/api/lots/{lot_id}/proposition")
    assert r.status_code == 202, r.text
    tid = r.json()["tache_id"]
    assert taches.lire_tache(conn, tid)["file"] == "api"
    _worker_tourne(cfg)
    t = client.get(f"/api/taches/{tid}").json()
    assert t["etat"] == "terminee", t
    return client.get(f"/api/lots/{lot_id}/objets").json()


def test_le_handler_est_enregistre():
    assert handlers.HANDLERS["proposer_liste"].__module__ == "worker.handlers.proposer_liste"


def test_le_schema_ne_demande_jamais_la_voie():
    props = brief.SCHEMA["properties"]["objets"]["items"]["properties"]
    assert "voie" not in props and "generateur" not in props
    assert set(props["nature"]["enum"]) == set(brief.NATURES)


def test_proposer_exige_un_besoin_et_un_style(client, conn):
    lot = _lot(client, besoin="")
    r = client.post(f"/api/lots/{lot['id']}/proposition")
    assert r.status_code == 409 and "écris ce que tu veux" in r.json()["erreur"]
    conn.execute("UPDATE lots SET besoin = 'x', style_id = NULL WHERE id = ?", (lot["id"],))
    conn.commit()
    r = client.post(f"/api/lots/{lot['id']}/proposition")
    assert r.status_code == 409 and "style" in r.json()["erreur"]
    assert client.post("/api/lots/999/proposition").status_code == 404


def test_proposition_simulee_classee_et_routee(client, conn, cfg, atelier):
    ecrire_generateur(atelier.generateurs, "caisse", types=["caisse", "coffre"])
    lot = _lot(client)
    r = _proposer(client, conn, cfg, lot["id"])
    objets = r["objets"]
    assert r["simule"] is True and r["proposition"]["etat"] == "terminee"
    assert 6 <= len(objets) <= 8 and all(o["nom"].startswith("Objet simulé") for o in objets)
    natures = {o["nature"] for o in objets}
    assert natures == {"geometrique", "ornemental", "mixte", "personnage"}
    par_nature = {}
    for o in objets:
        par_nature.setdefault(o["nature"], []).append(o)
    # géométrique sur un type connu du générateur → code ; sur un type inconnu → à créer
    code = [o for o in par_nature["geometrique"] if o["voie"] == "code"]
    assert code and code[0]["type_objet"] == "caisse" and code[0]["generateur"] == "caisse" and code[0]["regle_id"] == 3
    assert code[0]["dimensions"] == {"largeur": 0.6, "profondeur": 0.4, "hauteur": 0.4, "source": "style"}
    a_creer = [o for o in par_nature["geometrique"] if o["voie"] == "a_creer"]
    assert a_creer and a_creer[0]["dimensions"]["source"] == "claude" and "Claude Code" in a_creer[0]["raison_voie"]
    assert all(o["voie"] == "ia" and o["generateur"] == "meshy" for o in par_nature["ornemental"])
    mixte = par_nature["mixte"][0]
    assert mixte["voie"] == "a_creer" and len(mixte["pieces"]) == 2  # aucun générateur pour le fût simulé
    assert [p["voie"] for p in mixte["pieces"]] == ["a_creer", "ia"]
    perso = par_nature["personnage"][0]
    assert perso["voie"] == "hors_perimetre" and perso["retire"] is True
    assert all(o["voie_forcee"] is False for o in objets)
    assert r["resume"]["hors_perimetre"] == 0 and r["resume"]["a_creer"] >= 2
    assert r["resume"]["credits_estimes"] == 42 * len(par_nature["ornemental"])

    tete = client.get(f"/api/lots/{lot['id']}").json()
    assert tete["nom"].startswith("Lot simulé") and tete["nom_propose"] == tete["nom"] and tete["etape_courante"] == 1
    cout = conn.execute("SELECT * FROM couts WHERE service = 'claude'").fetchone()
    assert cout["type"] == "brief" and cout["simule"] == 1 and cout["lot_id"] == lot["id"] and cout["usd"] == 0
    assert json.loads(cout["detail"])["modele"] == "claude-sonnet-5-5"
    assert cout["tokens_entree"] > 0 and cout["tokens_sortie"] > 0 and cout["tache_id"] == r["proposition"]["id"]
    ev = conn.execute("SELECT * FROM evenements WHERE type = 'liste_proposee'").fetchone()
    assert "(simulée)" in ev["titre"] and ev["lien"] == f"/lots/{lot['id']}/brief"


def test_reproposer_garde_les_decisions_et_le_nom(client, conn, cfg, atelier):
    ecrire_generateur(atelier.generateurs, "caisse")
    lot = _lot(client)
    lid = lot["id"]
    r = _proposer(client, conn, cfg, lid)
    a_creer = next(o for o in r["objets"] if o["voie"] == "a_creer" and o["nature"] == "geometrique")
    decoche = next(o for o in r["objets"] if o["voie"] == "ia")
    client.patch(f"/api/lots/{lid}/objets/{a_creer['id']}", json={"voie": "ia"})
    client.patch(f"/api/lots/{lid}/objets/{decoche['id']}", json={"retenu": False})
    client.patch(f"/api/lots/{lid}", json={"nom": "Mon camp"})

    r2 = _proposer(client, conn, cfg, lid)
    assert len(r2["objets"]) == len(r["objets"])  # même besoin : même liste simulée
    par_type = {o["type_objet"]: o for o in r2["objets"]}
    assert par_type[a_creer["type_objet"]]["voie"] == "ia" and par_type[a_creer["type_objet"]]["voie_forcee"] is True
    assert par_type[decoche["type_objet"]]["retire"] is True
    assert client.get(f"/api/lots/{lid}").json()["nom"] == "Mon camp"  # un nom saisi n'est pas écrasé
    assert conn.execute("SELECT COUNT(*) AS n FROM couts WHERE service = 'claude'").fetchone()["n"] == 2
    # Les anciens objets au brief ont été remplacés, pas empilés
    assert conn.execute("SELECT COUNT(*) AS n FROM objets WHERE lot_id = ?", (lid,)).fetchone()["n"] == len(r2["objets"])


def test_une_proposition_en_cours_n_est_pas_doublee(client, conn, cfg):
    lot = _lot(client)
    t1 = client.post(f"/api/lots/{lot['id']}/proposition").json()["tache_id"]
    t2 = client.post(f"/api/lots/{lot['id']}/proposition").json()["tache_id"]
    assert t1 == t2
    assert client.get(f"/api/lots/{lot['id']}/objets").json()["proposition"] == {"id": t1, "etat": "en_attente", "erreur": None}


def test_le_prompt_systeme_donne_le_style_et_les_types_connus(conn, atelier):
    ecrire_generateur(atelier.generateurs, "caisse", types=["caisse", "coffre"])
    style = styles_svc.charger_style("rome-stylise-v0")
    gens, _ = reg.manifestes()
    types = reg.types_connus(gens) + ["scutum"]
    p = brief.prompt_systeme(style, types)
    assert "Types connus : caisse, coffre, scutum" in p
    assert "terre_cuite" in p and "petit_prop (≤ 2000 tris)" in p and "scutum 0.65×0.2×1.1 m" in p
    assert "voie" not in p.lower().replace("voie de fabrication", "")  # Claude ne choisit pas la voie


def test_simule_deterministe_et_honnete():
    system = "Types connus : caisse, coffre.\nMatériaux disponibles : bois, fer, cuir.\n"
    a = proposition_brief_simulee(system, "Besoin A")
    b = proposition_brief_simulee(system, "Besoin A")
    c = proposition_brief_simulee(system, "Besoin B")
    assert a == b and a["objets"] != c["objets"]
    assert all("simulé" in o["nom"] and "simulée" in o["description"] for o in a["objets"])
    assert a["objets"][0]["type_objet"] == "caisse" and a["objets"][0]["materiaux"] == ["bois", "fer"]
    reponse, usage = ClaudeSimule({}).completer_json(system, "Besoin A", brief.SCHEMA)
    assert reponse == a and usage["tokens_sortie"] > 0
    brief.valider_reponse(a)  # conforme au schéma de l'app


@pytest.mark.parametrize("reponse, attendu", [
    ({}, "sans liste"),
    ({"objets": []}, "sans liste"),
    ({"objets": [{"nom": ""}]}, "nom manquant"),
    ({"objets": [{"nom": "X", "nature": "bizarre", "categorie": "petit_prop"}]}, "nature 'bizarre'"),
    ({"objets": [{"nom": "X", "nature": "ornemental", "categorie": "xl"}]}, "catégorie 'xl'"),
    ({"objets": [{"nom": "X", "nature": "mixte", "categorie": "petit_prop", "pieces": [{"nom": "a", "nature": "geometrique"}]}]},
     "au moins 2 pièces"),
])
def test_reponse_invalide_refusee(reponse, attendu):
    with pytest.raises(brief.PropositionInvalide, match=attendu):
        brief.valider_reponse(reponse)


def test_valider_reponse_normalise_et_dedoublonne():
    r = brief.valider_reponse({"nom_lot": " Camp ", "objets": [
        {"nom": "Bouclier", "type_objet": "Bouclier_Rond", "nature": "geometrique", "categorie": "petit_prop",
         "dimensions_m": {"largeur": "0.6", "profondeur": 0, "hauteur": None}, "symetrique": "Z", "famille": "???"},
        {"nom": "Bouclier bis", "type_objet": "bouclier rond", "nature": "geometrique", "categorie": "petit_prop"},
    ]})
    assert r["nom_lot"] == "Camp" and len(r["objets"]) == 1
    o = r["objets"][0]
    assert o["type_objet"] == "bouclier rond" and o["symetrique"] is None and o["famille"] == "props"
    assert o["dimensions"] == {"largeur": 0.6, "profondeur": 0.5, "hauteur": 0.5}


class _ClaudeCasse:
    mode = "reel"

    def __init__(self, reponse=None, erreur=None):
        self.reponse, self.erreur = reponse, erreur

    def completer_json(self, system, user, schema):
        if self.erreur:
            raise self.erreur
        return self.reponse, {"tokens_entree": 1, "tokens_sortie": 1, "modele": "test"}


def test_reponse_inexploitable_echoue_clairement(client, conn):
    lot = _lot(client)
    with pytest.raises(RuntimeError, match="réponse de Claude inexploitable : objet 1 : nom manquant"):
        brief.executer_proposition(conn, _ClaudeCasse({"objets": [{"nom": ""}]}), {"lot_id": lot["id"]})
    assert client.get(f"/api/lots/{lot['id']}/objets").json()["objets"] == []


def test_cle_absente_est_definitive(client, conn):
    lot = _lot(client)
    with pytest.raises(TacheDefinitive, match="clé API Claude absente"):
        brief.executer_proposition(conn, _ClaudeCasse(erreur=RuntimeError("clé API Claude absente : renseigne-la dans Réglages")),
                                   {"lot_id": lot["id"]})


def test_reponse_reelle_non_simulee_n_est_pas_marquee(client, conn):
    lot = _lot(client)
    reponse = {"nom_lot": "Camp", "objets": [
        {"nom": "Amphore", "type_objet": "amphore", "nature": "ornemental", "categorie": "prop_moyen", "description": "Contenant",
         "dimensions_m": {"largeur": 0.4, "profondeur": 0.4, "hauteur": 0.9}, "materiaux": ["terre_cuite"]}]}
    brief.executer_proposition(conn, _ClaudeCasse(reponse), {"lot_id": lot["id"]})
    r = client.get(f"/api/lots/{lot['id']}/objets").json()
    assert r["simule"] is False and r["objets"][0]["voie"] == "ia"
    # amphore est dans dimensions_m du style : ce sont ses dimensions qui font foi
    assert r["objets"][0]["dimensions"] == {"largeur": 0.35, "profondeur": 0.35, "hauteur": 0.9, "source": "style"}
