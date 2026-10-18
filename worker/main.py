"""Boucle du worker : `python -m worker`.

- Un pool de threads partagé ; la limite par file (gpu, meshy, blender, api) est relue dans la
  config à chaque tour, et la prise de tâche est atomique en base.
- Reprise après coupure au démarrage : toute tâche `en_cours` au verrou étranger repasse
  `en_attente` avec un événement.
- Arrêt propre (SIGINT/SIGTERM) : on ne prend plus de tâche, celles en cours finissent
  (les handlers consultent ctx.arret_demande()) ou repassent en attente.
"""
from __future__ import annotations

import argparse
import logging
import os
import signal
import socket
import threading
import time
import traceback
from concurrent.futures import Future, ThreadPoolExecutor, wait
from datetime import UTC, datetime

from api import config as cfgmod
from api import db
from api.adapters import get_claude, get_comfyui, get_itchio, get_meshy
from api.services import taches
from worker import handlers

log = logging.getLogger("worker")


class Contexte:
    """Ce qu'un handler reçoit : config, base, adaptateurs, progression(), arret_demande()."""

    def __init__(self, worker: Worker, tache: dict, conn) -> None:
        self._worker = worker
        self.tache = tache
        self.db = conn
        self.config = worker.config()
        self._adaptateurs: dict = {}

    def _adaptateur(self, nom: str, fabrique):
        if nom not in self._adaptateurs:
            self._adaptateurs[nom] = fabrique(self.config)
        return self._adaptateurs[nom]

    @property
    def meshy(self):
        return self._adaptateur("meshy", get_meshy)

    @property
    def claude(self):
        return self._adaptateur("claude", get_claude)

    @property
    def comfyui(self):
        return self._adaptateur("comfyui", get_comfyui)

    @property
    def itchio(self):
        return self._adaptateur("itchio", get_itchio)

    @property
    def adaptateurs(self) -> dict:
        return {"meshy": self.meshy, "claude": self.claude, "comfyui": self.comfyui, "itchio": self.itchio}

    def progression(self, pct: float, texte: str = "") -> None:
        taches.progression(self.db, self.tache["id"], pct, texte)

    def arret_demande(self) -> bool:
        return self._worker.arret.is_set()


class Worker:
    def __init__(
        self,
        verrou: str | None = None,
        charger_config=cfgmod.charger,
        tick_s: float = 0.5,
        backoff_base_s: float = taches.BACKOFF_BASE_S,
        handlers_: dict | None = None,
        max_threads: int = 16,
    ) -> None:
        self.verrou = verrou or f"{socket.gethostname()}-{os.getpid()}"
        self._charger_config = charger_config
        self.tick_s = tick_s
        self.backoff_base_s = backoff_base_s
        self.handlers = handlers_ if handlers_ is not None else handlers.HANDLERS
        self.arret = threading.Event()
        self._executeur = ThreadPoolExecutor(max_workers=max_threads, thread_name_prefix="tache")
        self._en_cours: dict[int, tuple[str, Future]] = {}
        self._cadenas = threading.Lock()
        self._conn = None
        self._dernier_battement = 0.0

    # --- cycle de vie ---------------------------------------------------
    def config(self) -> dict:
        return self._charger_config()

    def demarrer(self) -> list[int]:
        db.initialiser()
        self._conn = db.connexion()
        reprises = taches.reprendre_apres_coupure(self._conn, self.verrou, delai_s=0)
        if reprises:
            log.warning("reprise après coupure : %d tâche(s) remise(s) en attente %s", len(reprises), reprises)
        log.info("worker %s prêt ; handlers : %s", self.verrou, ", ".join(sorted(self.handlers)) or "aucun")
        return reprises

    def boucle(self) -> None:
        if self._conn is None:
            self.demarrer()
        while not self.arret.is_set():
            try:
                self.tour()
            except Exception:  # noqa: BLE001 - la boucle ne meurt jamais sur une erreur passagère
                log.error("erreur dans la boucle :\n%s", traceback.format_exc())
            self.arret.wait(self.tick_s)
        self.arreter()

    def arreter(self, delai_s: float = 30.0) -> None:
        """Arrêt propre : attend les tâches en cours, remet le reste en attente."""
        self.arret.set()
        with self._cadenas:
            futures = [f for _, f in self._en_cours.values()]
        if futures:
            log.info("arrêt : %d tâche(s) en cours, attente %.0f s max", len(futures), delai_s)
            wait(futures, timeout=delai_s)
        with self._cadenas:
            restantes = [tid for tid, (_, f) in self._en_cours.items() if not f.done()]
        if restantes and self._conn is not None:
            for tid in restantes:
                taches.remettre_en_attente(self._conn, tid, "arrêt du worker avant la fin")
            log.warning("arrêt : %d tâche(s) remise(s) en attente %s", len(restantes), restantes)
        self._executeur.shutdown(wait=False, cancel_futures=True)
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    # --- un tour de boucle ----------------------------------------------
    def nb_en_cours(self, file: str | None = None) -> int:
        with self._cadenas:
            return sum(1 for f, _ in self._en_cours.values() if file is None or f == file)

    def tour(self) -> int:
        """Récolte les tâches finies, rafraîchit les verrous, prend ce que les limites permettent."""
        if self._conn is None:
            self.demarrer()
        conn = self._conn
        with self._cadenas:
            for tid in [tid for tid, (_, f) in self._en_cours.items() if f.done()]:
                del self._en_cours[tid]
            actives = list(self._en_cours)
        maintenant = time.monotonic()
        if actives and maintenant - self._dernier_battement > 15:
            taches.rafraichir_verrou(conn, actives, self.verrou)
            self._dernier_battement = maintenant
        if self.arret.is_set():
            return 0
        prises = 0
        for file, limite in cfgmod.limites_files(self.config()).items():
            while self.nb_en_cours(file) < limite:
                t = taches.prendre_tache(conn, file, self.verrou, limite)
                if t is None:
                    break
                with self._cadenas:
                    self._en_cours[t["id"]] = (file, self._executeur.submit(self._executer, t))
                prises += 1
        return prises

    def attendre_fin(self, timeout: float = 30.0) -> bool:
        """(Tests) Attend que toutes les tâches prises soient finies."""
        fin = time.monotonic() + timeout
        while time.monotonic() < fin:
            with self._cadenas:
                futures = [f for _, f in self._en_cours.values()]
            if not futures:
                return True
            wait(futures, timeout=max(0.0, fin - time.monotonic()))
            with self._cadenas:
                for tid in [tid for tid, (_, f) in self._en_cours.items() if f.done()]:
                    del self._en_cours[tid]
        return self.nb_en_cours() == 0

    # --- exécution d'une tâche (dans un thread) ---------------------------
    def _executer(self, t: dict) -> None:
        conn = db.connexion()
        debut = datetime.now(UTC)
        try:
            ctx = Contexte(self, t, conn)
            handler = self.handlers.get(t["type"])
            try:
                if handler is None:
                    raise LookupError(f"aucun handler pour le type de tâche « {t['type']} »")
                resultat = handler(t, ctx)
                if not isinstance(resultat, dict):
                    resultat = {"resultat": resultat}
                resultat.setdefault("duree_s", round((datetime.now(UTC) - debut).total_seconds(), 2))
                taches.terminer_tache(conn, t["id"], resultat)
                log.info("tâche %s (%s) terminée", t["id"], t["type"])
            except InterruptedError as e:
                taches.remettre_en_attente(conn, t["id"], f"interrompue : {e}")
                log.info("tâche %s (%s) remise en attente", t["id"], t["type"])
            except taches.TacheDefinitive as e:
                taches.echouer_definitivement(conn, t["id"], str(e))
                log.warning("tâche %s (%s) impossible, sans relance : %s", t["id"], t["type"], e)
            except Exception as e:  # noqa: BLE001 - toute erreur du handler = échec de la tâche
                erreur = f"{type(e).__name__}: {e}"
                etat = taches.echouer_tache(conn, t["id"], erreur, self.backoff_base_s)
                log.warning("tâche %s (%s) échouée → %s : %s", t["id"], t["type"], etat, erreur)
        except Exception:  # noqa: BLE001 - le thread ne doit jamais mourir en silence
            log.error("erreur interne sur la tâche %s :\n%s", t["id"], traceback.format_exc())
        finally:
            conn.close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Worker d'Atelier 3D")
    parser.add_argument("--tick", type=float, default=0.5, help="pause entre deux tours (s)")
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s : %(message)s", datefmt="%H:%M:%S")
    worker = Worker(tick_s=args.tick)

    def _signal(signum, frame):
        if worker.arret.is_set():
            return
        log.info("signal %s reçu : arrêt propre", signal.Signals(signum).name)
        worker.arret.set()

    signal.signal(signal.SIGINT, _signal)
    signal.signal(signal.SIGTERM, _signal)
    worker.boucle()
    return 0
