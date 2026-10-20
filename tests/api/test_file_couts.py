"""Étape 4 : suivi des coûts (A6), battement du worker, écran Génération, journal d'une tâche."""
import json
from datetime import UTC, datetime, timedelta

import pytest

from api import db
from api.adapters import get_meshy
from api.adapters.claude.simule import ClaudeSimule
from api.services import brief, couts, generation, styles, taches, workers
from api.services.taches import TacheDefinitive
from tests.conftest import ecrire_config
from worker.main import Worker

BESOIN = "Des contenants, du mobilier et un peu de décor."


class ClaudeReelFactice(ClaudeSimule):
    """Répond comme le simulateur, mais se présente comme l'API réelle : ses appels coûtent."""
    mode = "reel"

    def __init__(self, cfg, appels=None):
        super().__init__(cfg)
        self.appels = appels if appels is not None else []

    def completer_json(self, system, user, schema):
        self.appels.append(user)
        return super().completer_json(system, user, schema)


def _worker_tourne(cfg):
    w = Worker(verrou="test", tick_s=0.05, backoff_base_s=0, charger_config=lambda: cfg)
    try:
        w.tour()
        assert w.attendre_fin(30)
    finally:
        w.arreter(delai_s=1)


def _lot(client, **corps):
    return client.post("/api/lots", json={"theme": "Thème", "besoin": BESOIN, **corps}).json()


# --- coûts de l'API Claude ------------------------------------------------------------------------

def test_brief_simule_ne_coute_rien_et_le_dit(client, conn, cfg):
    lot = _lot(client)
    client.post(f"/api/lots/{lot['id']}/proposition")
    _worker_tourne(cfg)
    c = conn.execute("SELECT * FROM couts").fetchone()
    assert (c["service"], c["type"], c["lot_id"], c["simule"], c["usd"]) == ("claude", "brief", lot["id"], 1, 0)
    assert c["tokens_entree"] > 0
    assert couts.depense_claude_mois(conn) == {"usd": 0.0, "appels": 0, "briefs": 0, "avis": 0, "appels_simules": 1,
                                               "sans_tarif": 0}


def test_brief_reel_coute_d_apres_les_tarifs(client, conn, cfg):
    lot = _lot(client)
    brief.executer_proposition(conn, ClaudeReelFactice(cfg), {"lot_id": lot["id"]}, cfg=cfg)
    c = conn.execute("SELECT * FROM couts").fetchone()
    attendu = round((c["tokens_entree"] * 2.0 + c["tokens_sortie"] * 10.0) / 1_000_000, 6)  # Sonnet 5.5
    assert c["simule"] == 0 and c["usd"] == pytest.approx(attendu) and attendu > 0
    d = couts.depense_claude_mois(conn)
    assert d["appels"] == 1 and d["briefs"] == 1 and d["usd"] == pytest.approx(round(attendu, 4))


def test_tarifs_reglables_et_modele_sans_tarif(cfg):
    assert couts.usd_claude(cfg, "claude-haiku-5-5", 1_000_000, 1_000_000) == pytest.approx(0.60)
    cfg["services"]["claude"]["tarifs_usd_par_million"] = {"claude-haiku-5-5": [1.0, 2.0]}
    assert couts.usd_claude(cfg, "claude-haiku-5-5", 1_000_000, 1_000_000) == pytest.approx(3.0)
    assert couts.usd_claude(cfg, "modele-inconnu", 10, 10) is None  # jamais un prix inventé


def test_plafond_atteint_echec_definitif_sans_appel(client, conn, cfg):
    lot = _lot(client)
    cfg["services"]["claude"]["plafond_mensuel_usd"] = 1.0
    couts.enregistrer(conn, "claude", "brief", simule=False, usd=1.2, lot_id=lot["id"])
    appels = []
    with pytest.raises(TacheDefinitive, match="plafond mensuel"):
        brief.executer_proposition(conn, ClaudeReelFactice(cfg, appels), {"lot_id": lot["id"]}, cfg=cfg)
    assert appels == []
    # Le simulateur ne dépense rien : le plafond ne le bloque pas.
    brief.executer_proposition(conn, ClaudeSimule(cfg), {"lot_id": lot["id"]}, cfg=cfg)


def test_migration_030_reprend_les_couts_deja_ecrits(atelier, monkeypatch):
    chemin = atelier.racine / "ancienne.db"
    tout = db.lister_migrations()
    monkeypatch.setattr(db, "lister_migrations", lambda: [m for m in tout if m[0] < 30])
    c = db.connexion(chemin)
    try:
        db.appliquer_migrations(c)
        c.execute("INSERT INTO lots(nom, theme, cree_le, maj_le) VALUES ('L', 'T', 'x', 'x')")
        c.execute("INSERT INTO couts(date, service, detail) VALUES ('2026-10-18T08:00:00Z', 'claude', ?)",
                  (json.dumps({"type": "brief", "lot_id": 1, "simule": True}),))
        monkeypatch.setattr(db, "lister_migrations", lambda: tout)
        assert db.appliquer_migrations(c) == [30, 50]
        r = c.execute("SELECT type, lot_id, simule FROM couts").fetchone()
        assert (r["type"], r["lot_id"], r["simule"]) == ("brief", 1, 1)
    finally:
        c.close()


# --- crédits Meshy de la planche ---------------------------------------------------------------------

def test_planche_note_ses_credits_meshy_sans_doublon(client, conn, cfg):
    pilote = client.get("/api/styles").json()["styles"][0]
    palette = {c["nom"]: c["hex"] for c in pilote["palette"]}
    sid = client.post("/api/styles", json={"nom": "Avec coûts", "palette": palette, "budgets_depuis": pilote["id"]}).json()["id"]
    tid = client.post(f"/api/styles/{sid}/planche").json()["tache_id"]
    params = taches.lire_tache(conn, tid)["params"]
    meshy = get_meshy(cfg)
    for _ in range(2):  # le rangement peut se refaire (reprise) : les coûts aussi, sans doublon
        styles.executer_planche(conn, meshy, params, tache_id=tid, attente_s=0)
    lignes = conn.execute("SELECT * FROM couts WHERE service = 'meshy'").fetchall()
    assert len(lignes) == 6 and sum(x["credits"] for x in lignes) == 18
    assert all(x["simule"] == 1 and x["type"] == "planche" and x["tache_id"] == tid for x in lignes)


# --- battement du worker ------------------------------------------------------------------------------

def test_le_worker_dit_qu_il_tourne_puis_qu_il_s_arrete(atelier, conn, cfg, client):
    assert client.get("/api/worker").json()["actif"] is False  # jamais lancé
    w = Worker(verrou="w-test", tick_s=0.05, charger_config=lambda: cfg)
    w.demarrer()
    e = client.get("/api/worker").json()
    assert e["actif"] is True and e["battu_le"] and e["en_attente"] == 0
    w.arreter(delai_s=1)
    assert client.get("/api/worker").json()["actif"] is False


def test_un_battement_ancien_veut_dire_arrete(conn):
    vieux = (datetime.now(UTC) - timedelta(minutes=5)).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    conn.execute("INSERT INTO workers(verrou, demarre_le, battu_le) VALUES ('coupe', ?, ?)", (vieux, vieux))
    assert workers.etat(conn)["actif"] is False  # coupure : aucune sortie propre, mais plus de battement


# --- écran Génération --------------------------------------------------------------------------------

def _lot_valide(client, cfg):
    lot = _lot(client)
    client.post(f"/api/lots/{lot['id']}/proposition")
    _worker_tourne(cfg)
    objets = client.get(f"/api/lots/{lot['id']}/objets").json()["objets"]
    for o in objets:
        if o["voie"] == "a_creer":
            client.patch(f"/api/lots/{lot['id']}/objets/{o['id']}", json={"voie": "ia"})
    assert client.post(f"/api/lots/{lot['id']}/valider-brief").status_code == 200
    return lot["id"]


def test_generation_avant_la_fabrication(client, conn, cfg):
    lid = _lot_valide(client, cfg)
    g = client.get(f"/api/lots/{lid}/generation").json()
    f = g["fabrication"]  # objets simulés passés en voie IA : rien à lancer avant l'étape 7
    assert f["autres_voies"] == len(g["objets"]) and "étape 7" in f["raison_ia"]
    assert all(not o["peut_fabriquer"] and "étape 7" in o["motif"] for o in g["objets"])
    assert g["objets"] and all(o["statut"].startswith("Attend sa référence") for o in g["objets"])
    assert all([p["etat"] for p in o["etapes"]] == ["a_faire"] * 4 for o in g["objets"])
    # « Générer les références » : une tâche d'images de référence par objet, après la proposition de la liste.
    types = [t["type"] for t in g["taches"]]
    assert types[-1] == "proposer_liste" and types[:-1] == ["references_images"] * len(g["objets"])
    assert g["taches"][-1]["etat"] == "terminee" and g["taches"][-1]["peut_relancer"] is False
    lot = client.get(f"/api/lots/{lid}").json()
    assert g["tuiles"] == {"prets_revue": 0, "fabriques": len(g["objets"]), "en_cours": 0, "relances": 0,
                           "credits_utilises": 0, "credits_simules": False, "credits_prevus": lot["credits_prevus"]}
    assert [x["nom"] for x in g["generateurs"]] == ["Générateurs par code", "Meshy", "ComfyUI"]
    assert g["generateurs"][1]["etat"] == "Simulé" and g["generateurs"][0]["etat"] == "Aucun script"


def test_generation_suit_les_etapes_les_relances_et_les_credits(client, conn, cfg):
    lid = _lot_valide(client, cfg)
    ids = [o["id"] for o in client.get(f"/api/lots/{lid}/generation").json()["objets"]]
    for oid, etape in zip(ids, ("finition", "revue", "generation"), strict=False):
        conn.execute("UPDATE objets SET etape = ? WHERE id = ?", (etape, oid))
    # Une tâche du lot qui a échoué deux fois avant de passer, et 60 crédits Meshy simulés.
    tid = taches.creer_tache(conn, "echec", "api", {}, lot_id=lid, cfg=cfg)
    conn.execute("UPDATE taches SET tentatives = 3, etat = 'echouee', erreur = 'RuntimeError: panne' WHERE id = ?", (tid,))
    couts.enregistrer(conn, "meshy", "generation", simule=True, credits=60, lot_id=lid)
    g = client.get(f"/api/lots/{lid}/generation").json()
    par_id = {o["id"]: o for o in g["objets"]}
    assert [p["etat"] for p in par_id[ids[0]]["etapes"]] == ["fait", "en_cours", "a_faire", "a_faire"]
    assert par_id[ids[1]]["statut"] == "Prêt pour la revue" and par_id[ids[1]]["pct"] == 100
    t = g["tuiles"]
    # En cours : l'objet en finition ; celui à « generation » sans essai est un objet IA qui attend l'étape 7.
    assert (t["prets_revue"], t["en_cours"], t["relances"], t["credits_utilises"], t["credits_simules"]) == (1, 1, 2, 60, True)
    echec = next(x for x in g["taches"] if x["id"] == tid)
    assert echec["peut_relancer"] is True and echec["erreur"] == "RuntimeError: panne"


def test_taches_recentes_pour_reglages(client, conn, cfg):
    lid = _lot(client)["id"]
    client.post(f"/api/lots/{lid}/proposition")
    pilote = client.get("/api/styles").json()["styles"][0]
    client.post(f"/api/styles/{pilote['id']}/planche")
    r = client.get("/api/worker/taches").json()
    assert r["worker"]["actif"] is False and r["worker"]["en_attente"] == 2
    contextes = {t["type"]: t["contexte"] for t in r["taches"]}
    assert contextes["planche_style"] == {"libelle": "Style rome-stylise-v0", "lien": "/styles?style=rome-stylise-v0"}
    assert contextes["proposer_liste"] == {"libelle": f"Lot n° {lid}", "lien": f"/lots/{lid}/generation"}  # lot sans nom


def test_journal_d_une_tache(client, conn, cfg):
    lid = _lot(client)["id"]
    tid = client.post(f"/api/lots/{lid}/proposition").json()["tache_id"]
    _worker_tourne(cfg)
    j = client.get(f"/api/taches/{tid}/journal").json()
    types = [e["type"] for e in j["evenements"]]
    assert types[0] == "tache_creee" and "tache_terminee" in types and types.index("tache_debutee") < types.index("tache_terminee")
    assert client.get("/api/taches/999/journal").status_code == 404


def test_vue_generation_lot_inconnu(client):
    assert client.get("/api/lots/999/generation").status_code == 404


def test_le_reglage_des_files_est_dans_la_vue(client, cfg, atelier):
    ecrire_config(atelier.config, lambda c: c["files"].update({"blender": 4}))
    lid = _lot(client)["id"]
    assert client.get(f"/api/lots/{lid}/generation").json()["limites_files"]["blender"] == 4
    assert generation.FILES["gpu"] == "carte graphique"


def test_alerte_credits_meshy_une_fois_par_mois(client, conn, cfg, atelier):
    from api.services import credits
    ecrire_config(atelier.config, lambda c: c["services"]["meshy"].update({"credits_mensuels": 100, "alerte_pct": 80}))
    meshy = get_meshy(__import__("api.config", fromlist=["charger"]).charger())
    meshy.image_vers_3d("a.png")  # 30 crédits : 30 %
    credits.oublier_cache()
    client.get("/api/menu")
    assert client.get("/api/notifications").json()["non_lues"] == 0
    meshy.image_vers_3d("b.png")
    meshy.image_vers_image("c", None, 10)  # 30 + 30 + 30 = 90 %
    for _ in range(2):  # le menu se relit souvent : une seule notification
        client.get("/api/menu")
    n = client.get("/api/notifications").json()
    assert n["non_lues"] == 1 and n["notifications"][0]["titre"] == "Crédits Meshy à 90 % (simulé)"
