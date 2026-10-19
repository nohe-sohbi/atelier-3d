"""File de tâches : création, prise atomique, limites, relances, reprise, événements."""
import threading
from datetime import UTC, datetime, timedelta

import pytest

from api import db
from api.services import evenements
from worker import queue as q


def _types(conn, tache_id):
    return [e["type"] for e in conn.execute(
        "SELECT type FROM evenements WHERE tache_id = ? ORDER BY id", (tache_id,)).fetchall()]


def test_creation(conn, cfg):
    tid = q.creer_tache(conn, "attendre", "blender", {"secondes": 1}, priorite=2, cfg=cfg)
    t = q.lire_tache(conn, tid)
    assert t["etat"] == "en_attente" and t["params"] == {"secondes": 1} and t["priorite"] == 2
    assert t["tentatives"] == 0 and t["max_tentatives"] == 4 and t["cree_le"].endswith("Z")
    assert _types(conn, tid) == ["tache_creee"]
    with pytest.raises(ValueError):
        q.creer_tache(conn, "x", "inconnue", cfg=cfg)
    with pytest.raises(q.TacheIntrouvable):
        q.lire_tache(conn, 999)


def test_prise_atomique_et_priorite(conn, cfg):
    bas = q.creer_tache(conn, "a", "api", priorite=0, cfg=cfg)
    haut = q.creer_tache(conn, "a", "api", priorite=5, cfg=cfg)
    t = q.prendre_tache(conn, "api", "w1", 4)
    assert t["id"] == haut and t["etat"] == "en_cours" and t["verrou"] == "w1" and t["tentatives"] == 1
    assert q.prendre_tache(conn, "api", "w1", 4)["id"] == bas
    assert q.prendre_tache(conn, "api", "w1", 4) is None
    assert q.prendre_tache(conn, "gpu", "w1", 1) is None
    assert _types(conn, haut) == ["tache_creee", "tache_debutee"]


def test_prise_concurrente_sans_doublon(atelier, conn, cfg):
    ids = [q.creer_tache(conn, "a", "api", cfg=cfg) for _ in range(20)]
    prises, cadenas = [], threading.Lock()

    def worker(nom):
        c = db.connexion()
        try:
            while True:
                t = q.prendre_tache(c, "api", nom, 100)
                if t is None:
                    return
                with cadenas:
                    prises.append(t["id"])
        finally:
            c.close()

    threads = [threading.Thread(target=worker, args=(f"w{i}",)) for i in range(6)]
    for th in threads:
        th.start()
    for th in threads:
        th.join()
    assert sorted(prises) == ids and len(set(prises)) == 20


def test_limite_de_concurrence_par_file(conn, cfg):
    for _ in range(3):
        q.creer_tache(conn, "a", "gpu", cfg=cfg)
    t1 = q.prendre_tache(conn, "gpu", "w", 1)
    assert t1 and q.prendre_tache(conn, "gpu", "w", 1) is None
    q.terminer_tache(conn, t1["id"], {"ok": True})
    assert q.lire_tache(conn, t1["id"])["etat"] == "terminee"
    t2 = q.prendre_tache(conn, "gpu", "w", 1)
    assert t2 and t2["id"] != t1["id"]
    t3 = q.prendre_tache(conn, "gpu", "w", 2)
    assert t3 and q.prendre_tache(conn, "gpu", "w", 2) is None


def test_relances_jusqu_au_max(conn, cfg):
    tid = q.creer_tache(conn, "echec", "api", max_tentatives=3, cfg=cfg)
    for n in (1, 2):
        t = q.prendre_tache(conn, "api", "w", 4)
        assert t["id"] == tid and t["tentatives"] == n
        assert q.echouer_tache(conn, tid, f"boum {n}", backoff_base_s=0) == "en_attente"
        t = q.lire_tache(conn, tid)
        assert t["erreur"] == f"boum {n}" and t["verrou"] is None and t["reprise_le"] is not None
    t = q.prendre_tache(conn, "api", "w", 4)
    assert t["tentatives"] == 3
    assert q.echouer_tache(conn, tid, "boum 3", backoff_base_s=0) == "echouee"
    t = q.lire_tache(conn, tid)
    assert t["etat"] == "echouee" and t["fini_le"]
    assert q.prendre_tache(conn, "api", "w", 4) is None
    assert _types(conn, tid) == ["tache_creee", "tache_debutee", "tache_relancee", "tache_debutee",
                                 "tache_relancee", "tache_debutee", evenements.TACHE_ECHEC_FINAL]
    final = db.une(conn, "SELECT * FROM evenements WHERE type = ?", (evenements.TACHE_ECHEC_FINAL,))
    assert final["notification"] == 1 and "2 relances" in final["titre"] and final["niveau"] == "erreur"
    # Relance manuelle : repart de zéro.
    assert q.relancer_tache(conn, tid)["tentatives"] == 0
    assert q.prendre_tache(conn, "api", "w", 4)["id"] == tid


def test_backoff_retarde_la_reprise(conn, cfg):
    tid = q.creer_tache(conn, "echec", "api", cfg=cfg)
    q.prendre_tache(conn, "api", "w", 4)
    q.echouer_tache(conn, tid, "x", backoff_base_s=60)
    assert q.prendre_tache(conn, "api", "w", 4) is None  # pas avant 60 s
    reprise = datetime.fromisoformat(q.lire_tache(conn, tid)["reprise_le"])
    assert 55 <= (reprise - datetime.now(UTC)).total_seconds() <= 61
    assert q.delai_backoff(1, 5) == 5 and q.delai_backoff(3, 5) == 20 and q.delai_backoff(20, 5) == 300


def test_reprise_apres_coupure(conn, cfg):
    perimee = q.creer_tache(conn, "a", "blender", cfg=cfg)
    vivante = q.creer_tache(conn, "a", "blender", cfg=cfg)
    q.prendre_tache(conn, "blender", "ancien-worker", 2)
    q.prendre_tache(conn, "blender", "worker-actuel", 2)
    vieux = (datetime.now(UTC) - timedelta(minutes=10)).isoformat().replace("+00:00", "Z")
    conn.execute("UPDATE taches SET verrou_le = ? WHERE id = ?", (vieux, perimee))
    # Verrou étranger récent : pas périmé si on demande un délai.
    assert q.reprendre_apres_coupure(conn, "worker-actuel", delai_s=3600) == []
    assert q.reprendre_apres_coupure(conn, "worker-actuel", delai_s=120) == [perimee]
    t = q.lire_tache(conn, perimee)
    assert t["etat"] == "en_attente" and t["tentatives"] == 0 and t["verrou"] is None
    assert q.lire_tache(conn, vivante)["etat"] == "en_cours"
    ev = db.une(conn, "SELECT * FROM evenements WHERE type = 'tache_reprise'")
    assert ev["tache_id"] == perimee and ev["niveau"] == "alerte"
    # Au démarrage (délai 0), tout verrou étranger est périmé.
    assert q.reprendre_apres_coupure(conn, "nouveau", delai_s=0) == [vivante]


def test_progression_annulation_et_verrou(conn, cfg):
    tid = q.creer_tache(conn, "a", "api", cfg=cfg)
    q.prendre_tache(conn, "api", "w", 4)
    q.progression(conn, tid, 42.345, "en route")
    t = q.lire_tache(conn, tid)
    assert t["resultat"]["progression"] == {"pct": 42.3, "texte": "en route"}
    q.rafraichir_verrou(conn, [tid], "w")
    assert q.lire_tache(conn, tid)["verrou_le"]
    q.terminer_tache(conn, tid, {"ok": True})
    assert q.lire_tache(conn, tid)["resultat"] == {"ok": True}
    with pytest.raises(q.TransitionInterdite):
        q.terminer_tache(conn, tid)
    with pytest.raises(q.TransitionInterdite):
        q.annuler_tache(conn, tid)
    t2 = q.creer_tache(conn, "a", "api", cfg=cfg)
    assert q.annuler_tache(conn, t2)["etat"] == "annulee"
    assert "tache_annulee" in _types(conn, t2)
