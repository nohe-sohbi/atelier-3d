"""Boucle du worker : handlers, exécution, relances, arrêt propre."""
import threading
import time

from api import config as cfgmod
from api import db
from api.services import evenements
from worker import handlers
from worker import queue as q
from worker.main import Contexte, Worker


def _worker(**kw):
    return Worker(verrou="test-worker", tick_s=0.05, backoff_base_s=0, **kw)


def test_registre_des_handlers():
    assert {"attendre", "echec"} <= set(handlers.HANDLERS)
    assert handlers.HANDLERS["attendre"].__module__ == "worker.handlers.attendre"


def test_execute_attendre_avec_progression(atelier, conn, cfg):
    tid = q.creer_tache(conn, "attendre", "api", {"secondes": 0.1, "pas": 2}, cfg=cfg)
    w = _worker()
    assert w.demarrer() == []
    try:
        assert w.tour() == 1
        assert w.attendre_fin(10)
    finally:
        w.arreter(delai_s=1)
    t = q.lire_tache(conn, tid)
    assert t["etat"] == "terminee" and t["resultat"]["ok"] is True and "duree_s" in t["resultat"]
    types = [e["type"] for e in conn.execute("SELECT type FROM evenements WHERE tache_id = ? ORDER BY id", (tid,))]
    assert types == ["tache_creee", "tache_debutee", "tache_progression", "tache_progression", "tache_terminee"]


def test_echec_relance_puis_echouee(atelier, conn, cfg):
    tid = q.creer_tache(conn, "echec", "api", {"message": "cassé"}, max_tentatives=2, cfg=cfg)
    w = _worker()
    try:
        for _ in range(2):
            assert w.tour() == 1
            assert w.attendre_fin(10)
        assert w.tour() == 0
    finally:
        w.arreter(delai_s=1)
    t = q.lire_tache(conn, tid)
    assert t["etat"] == "echouee" and t["tentatives"] == 2 and "cassé" in t["erreur"]
    assert db.une(conn, "SELECT 1 AS x FROM evenements WHERE type = ? AND tache_id = ?",
                  (evenements.TACHE_ECHEC_FINAL, tid))


def test_type_inconnu_echoue_proprement(atelier, conn, cfg):
    tid = q.creer_tache(conn, "martien", "api", max_tentatives=1, cfg=cfg)
    w = _worker()
    try:
        w.tour()
        w.attendre_fin(10)
    finally:
        w.arreter(delai_s=1)
    t = q.lire_tache(conn, tid)
    assert t["etat"] == "echouee" and "aucun handler" in t["erreur"]


def test_limites_relues_dans_la_config(atelier, conn, cfg):
    for _ in range(3):
        q.creer_tache(conn, "attendre", "blender", {"secondes": 0.3, "pas": 1}, cfg=cfg)
    limites = {"files": {"blender": 1}}
    w = _worker(charger_config=lambda: cfgmod._fusionner(cfgmod.charger(), limites))
    try:
        assert w.tour() == 1 and w.nb_en_cours("blender") == 1
        assert w.tour() == 0
        limites["files"]["blender"] = 3
        assert w.tour() == 2
        assert w.attendre_fin(10)
    finally:
        w.arreter(delai_s=1)
    assert db.une(conn, "SELECT COUNT(*) AS n FROM taches WHERE etat = 'terminee'")["n"] == 3


def test_reprise_au_demarrage(atelier, conn, cfg):
    tid = q.creer_tache(conn, "attendre", "gpu", {"secondes": 0}, cfg=cfg)
    q.prendre_tache(conn, "gpu", "worker-mort", 1)
    w = _worker()
    try:
        assert w.demarrer() == [tid]
        assert q.lire_tache(conn, tid)["etat"] == "en_attente"
        assert w.tour() == 1 and w.attendre_fin(10)
    finally:
        w.arreter(delai_s=1)
    assert q.lire_tache(conn, tid)["etat"] == "terminee"


def test_arret_propre_remet_en_attente(atelier, conn, cfg):
    longue = q.creer_tache(conn, "attendre", "api", {"secondes": 20, "pas": 200}, cfg=cfg)
    courte = q.creer_tache(conn, "attendre", "api", {"secondes": 0.05, "pas": 1}, cfg=cfg)
    w = _worker()
    th = threading.Thread(target=w.boucle)
    th.start()
    fin = time.monotonic() + 5
    while time.monotonic() < fin and q.lire_tache(conn, courte)["etat"] != "terminee":
        time.sleep(0.05)
    assert q.lire_tache(conn, longue)["etat"] == "en_cours"
    w.arret.set()  # équivalent de SIGINT
    th.join(timeout=10)
    assert not th.is_alive()
    t = q.lire_tache(conn, longue)
    assert t["etat"] == "en_attente" and t["tentatives"] == 0 and t["verrou"] is None
    assert db.une(conn, "SELECT 1 AS x FROM evenements WHERE type = 'tache_remise_en_attente' AND tache_id = ?", (longue,))
    assert q.lire_tache(conn, courte)["etat"] == "terminee"


def test_contexte_donne_config_db_et_adaptateurs(atelier, conn, cfg):
    tid = q.creer_tache(conn, "attendre", "api", cfg=cfg)
    w = _worker()
    ctx = Contexte(w, q.lire_tache(conn, tid), conn)
    assert ctx.config["files"]["gpu"] == 1 and ctx.db is conn
    assert ctx.meshy.mode == "simule" and set(ctx.adaptateurs) == {"meshy", "claude", "comfyui", "itchio"}
    assert ctx.arret_demande() is False
    q.prendre_tache(conn, "api", w.verrou, 4)
    ctx.progression(10, "en route")
    assert q.lire_tache(conn, tid)["resultat"]["progression"]["pct"] == 10
