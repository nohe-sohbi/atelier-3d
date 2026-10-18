"""File de tâches (table taches) : création, prise atomique, relances, reprise après coupure.

Utilisée par l'API (routes) et par le worker (worker/queue.py la réexporte).

- Quatre files : gpu, meshy, blender (limites dans la config) et api (limite fixe à 4).
- Une tâche est prise par `UPDATE … WHERE etat='en_attente'` sous BEGIN IMMEDIATE, avec un
  verrou = identifiant du worker, et un horodatage `verrou_le` rafraîchi régulièrement.
- Un échec relance la tâche (backoff exponentiel) tant que tentatives < max_tentatives ;
  ensuite elle passe `echouee` et une notification est écrite.
- Au démarrage du worker, les tâches `en_cours` au verrou périmé repassent `en_attente`.
- Chaque changement d'état écrit un événement.
"""
from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime, timedelta

from api import config as cfgmod
from api import db
from api.services import evenements

FILES = ("gpu", "meshy", "blender", "api")
ETATS = ("en_attente", "en_cours", "terminee", "echouee", "annulee")
ETATS_FINAUX = ("terminee", "echouee", "annulee")
BACKOFF_BASE_S = 5.0
BACKOFF_MAX_S = 300.0
VERROU_PERIME_S = 120


class TacheIntrouvable(LookupError):
    pass


class TransitionInterdite(ValueError):
    pass


def _iso(d: datetime) -> str:
    return d.replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _charger(row: dict | None) -> dict | None:
    if row is None:
        return None
    t = dict(row)
    t["params"] = json.loads(t.pop("params_json") or "{}")
    t["resultat"] = json.loads(t.pop("resultat_json") or "null")
    return t


def lire_tache(conn: sqlite3.Connection, tache_id: int) -> dict:
    t = _charger(db.une(conn, "SELECT * FROM taches WHERE id = ?", (tache_id,)))
    if t is None:
        raise TacheIntrouvable(f"tâche {tache_id} introuvable")
    return t


def lister_taches(conn: sqlite3.Connection, etat: str | None = None, lot_id: int | None = None,
                  file: str | None = None, limit: int = 200) -> list[dict]:
    clauses, params = [], []
    if etat:
        clauses.append("etat = ?")
        params.append(etat)
    if lot_id is not None:
        clauses.append("lot_id = ?")
        params.append(lot_id)
    if file:
        clauses.append("file = ?")
        params.append(file)
    sql = "SELECT * FROM taches"
    if clauses:
        sql += " WHERE " + " AND ".join(clauses)
    sql += " ORDER BY id DESC LIMIT ?"
    params.append(max(1, min(int(limit), 1000)))
    return [_charger(r) for r in db.toutes(conn, sql, tuple(params))]


def creer_tache(
    conn: sqlite3.Connection,
    type: str,
    file: str,
    params: dict | None = None,
    lot_id: int | None = None,
    objet_id: int | None = None,
    essai_id: int | None = None,
    priorite: int = 0,
    max_tentatives: int | None = None,
    cfg: dict | None = None,
) -> int:
    """Crée une tâche en attente ; renvoie son id. max_tentatives = 1 + relances_max par défaut."""
    if file not in FILES:
        raise ValueError(f"file inconnue : {file} (attendu {', '.join(FILES)})")
    if max_tentatives is None:
        max_tentatives = 1 + cfgmod.relances_max(cfg if cfg is not None else cfgmod.charger())
    with db.transaction(conn):
        tache_id = db.inserer(conn, "taches", {
            "type": type, "file": file, "etat": "en_attente",
            "params_json": json.dumps(params or {}, ensure_ascii=False),
            "tentatives": 0, "max_tentatives": max(1, int(max_tentatives)), "priorite": int(priorite),
            "lot_id": lot_id, "objet_id": objet_id, "essai_id": essai_id, "cree_le": db.maintenant(),
        })
        evenements.ecrire(conn, "tache_creee", f"Tâche {type} créée", f"File {file}.",
                          niveau="debug", lot_id=lot_id, objet_id=objet_id, tache_id=tache_id)
    return tache_id


def compter_en_cours(conn: sqlite3.Connection, file: str) -> int:
    r = db.une(conn, "SELECT COUNT(*) AS n FROM taches WHERE file = ? AND etat = 'en_cours'", (file,))
    return int(r["n"])


def prendre_tache(conn: sqlite3.Connection, file: str, verrou: str, limite: int) -> dict | None:
    """Prend atomiquement la prochaine tâche en attente de la file, si la limite le permet."""
    maintenant = db.maintenant()
    with db.transaction(conn):
        if compter_en_cours(conn, file) >= max(0, int(limite)):
            return None
        row = db.une(conn, """
            SELECT id FROM taches
            WHERE etat = 'en_attente' AND file = ? AND (reprise_le IS NULL OR reprise_le <= ?)
            ORDER BY priorite DESC, id LIMIT 1""", (file, maintenant))
        if row is None:
            return None
        cur = conn.execute("""
            UPDATE taches SET etat = 'en_cours', verrou = ?, verrou_le = ?, debute_le = ?,
                   tentatives = tentatives + 1, erreur = NULL, reprise_le = NULL
            WHERE id = ? AND etat = 'en_attente'""", (verrou, maintenant, maintenant, row["id"]))
        if cur.rowcount != 1:
            return None
        t = lire_tache(conn, row["id"])
        evenements.ecrire(conn, "tache_debutee", f"Tâche {t['type']} démarrée",
                          f"Tentative {t['tentatives']} sur {t['max_tentatives']}.", niveau="debug",
                          lot_id=t["lot_id"], objet_id=t["objet_id"], tache_id=t["id"])
    return t


def rafraichir_verrou(conn: sqlite3.Connection, tache_ids: list[int], verrou: str) -> None:
    if not tache_ids:
        return
    marques = ",".join("?" for _ in tache_ids)
    conn.execute(f"UPDATE taches SET verrou_le = ? WHERE verrou = ? AND etat = 'en_cours' AND id IN ({marques})",
                 (db.maintenant(), verrou, *tache_ids))


def progression(conn: sqlite3.Connection, tache_id: int, pct: float, texte: str = "") -> None:
    """Écrit l'avancement dans resultat_json.progression et un événement (niveau debug)."""
    with db.transaction(conn):
        t = lire_tache(conn, tache_id)
        resultat = t["resultat"] if isinstance(t["resultat"], dict) else {}
        resultat["progression"] = {"pct": max(0, min(100, round(float(pct), 1))), "texte": texte}
        conn.execute("UPDATE taches SET resultat_json = ?, verrou_le = ? WHERE id = ?",
                     (json.dumps(resultat, ensure_ascii=False), db.maintenant(), tache_id))
        evenements.ecrire(conn, "tache_progression", f"{t['type']} : {texte or ''}".strip(" :"),
                          f"{resultat['progression']['pct']:.0f} %", niveau="debug",
                          lot_id=t["lot_id"], objet_id=t["objet_id"], tache_id=tache_id)


def terminer_tache(conn: sqlite3.Connection, tache_id: int, resultat: dict | None = None) -> None:
    with db.transaction(conn):
        t = lire_tache(conn, tache_id)
        if t["etat"] != "en_cours":
            raise TransitionInterdite(f"tâche {tache_id} n'est pas en cours ({t['etat']})")
        res = t["resultat"] if isinstance(t["resultat"], dict) else {}
        res.update(resultat or {})
        res.pop("progression", None)
        conn.execute("""UPDATE taches SET etat = 'terminee', resultat_json = ?, fini_le = ?,
                        verrou = NULL, verrou_le = NULL WHERE id = ?""",
                     (json.dumps(res, ensure_ascii=False), db.maintenant(), tache_id))
        evenements.ecrire(conn, "tache_terminee", f"Tâche {t['type']} terminée", niveau="succes",
                          lot_id=t["lot_id"], objet_id=t["objet_id"], tache_id=tache_id)


def delai_backoff(tentatives: int, base_s: float = BACKOFF_BASE_S) -> float:
    return min(BACKOFF_MAX_S, base_s * (2 ** max(0, tentatives - 1)))


def echouer_tache(conn: sqlite3.Connection, tache_id: int, erreur: str,
                  backoff_base_s: float = BACKOFF_BASE_S) -> str:
    """Relance (en_attente + backoff) ou marque echouee ; renvoie le nouvel état."""
    with db.transaction(conn):
        t = lire_tache(conn, tache_id)
        if t["etat"] != "en_cours":
            raise TransitionInterdite(f"tâche {tache_id} n'est pas en cours ({t['etat']})")
        erreur = (erreur or "erreur inconnue")[:4000]
        if t["tentatives"] < t["max_tentatives"]:
            delai = delai_backoff(t["tentatives"], backoff_base_s)
            reprise = _iso(datetime.now(UTC) + timedelta(seconds=delai))
            conn.execute("""UPDATE taches SET etat = 'en_attente', erreur = ?, verrou = NULL,
                            verrou_le = NULL, reprise_le = ? WHERE id = ?""", (erreur, reprise, tache_id))
            evenements.ecrire(conn, "tache_relancee", f"Tâche {t['type']} relancée",
                              f"Tentative {t['tentatives']} échouée : {erreur}. Nouvel essai dans {delai:.0f} s.",
                              niveau="alerte", lot_id=t["lot_id"], objet_id=t["objet_id"], tache_id=tache_id)
            return "en_attente"
        conn.execute("""UPDATE taches SET etat = 'echouee', erreur = ?, fini_le = ?, verrou = NULL,
                        verrou_le = NULL WHERE id = ?""", (erreur, db.maintenant(), tache_id))
        relances = t["tentatives"] - 1
        evenements.ecrire(conn, evenements.TACHE_ECHEC_FINAL,
                          f"Tâche {t['type']} en échec après {relances} relance{'s' if relances > 1 else ''}",
                          erreur, niveau="erreur", lien=f"/lots/{t['lot_id']}/generation" if t["lot_id"] else None,
                          lot_id=t["lot_id"], objet_id=t["objet_id"], tache_id=tache_id)
        return "echouee"


def annuler_tache(conn: sqlite3.Connection, tache_id: int) -> dict:
    with db.transaction(conn):
        t = lire_tache(conn, tache_id)
        if t["etat"] in ETATS_FINAUX:
            raise TransitionInterdite(f"tâche {tache_id} déjà {t['etat']}")
        conn.execute("""UPDATE taches SET etat = 'annulee', fini_le = ?, verrou = NULL, verrou_le = NULL
                        WHERE id = ?""", (db.maintenant(), tache_id))
        evenements.ecrire(conn, "tache_annulee", f"Tâche {t['type']} annulée", niveau="info",
                          lot_id=t["lot_id"], objet_id=t["objet_id"], tache_id=tache_id)
    return lire_tache(conn, tache_id)


def relancer_tache(conn: sqlite3.Connection, tache_id: int) -> dict:
    """Remet une tâche échouée ou annulée en attente, compteur de tentatives à zéro."""
    with db.transaction(conn):
        t = lire_tache(conn, tache_id)
        if t["etat"] not in ("echouee", "annulee"):
            raise TransitionInterdite(f"tâche {tache_id} est {t['etat']} : seule une tâche échouée ou annulée se relance")
        conn.execute("""UPDATE taches SET etat = 'en_attente', tentatives = 0, erreur = NULL, fini_le = NULL,
                        resultat_json = NULL, reprise_le = NULL WHERE id = ?""", (tache_id,))
        evenements.ecrire(conn, "tache_relancee", f"Tâche {t['type']} relancée à la main", niveau="info",
                          lot_id=t["lot_id"], objet_id=t["objet_id"], tache_id=tache_id)
    return lire_tache(conn, tache_id)


def reprendre_apres_coupure(conn: sqlite3.Connection, verrou_courant: str | None = None,
                            delai_s: float = 0) -> list[int]:
    """Remet en attente les tâches en_cours dont le verrou est périmé ; renvoie leurs ids.

    delai_s = 0 : tout verrou étranger est périmé (au démarrage, un seul worker tourne).
    La tentative entamée n'est pas comptée deux fois (tentatives - 1).
    """
    limite = _iso(datetime.now(UTC) - timedelta(seconds=delai_s))
    with db.transaction(conn):
        rows = db.toutes(conn, """
            SELECT * FROM taches WHERE etat = 'en_cours'
              AND (verrou IS NULL OR verrou != ?) AND (verrou_le IS NULL OR verrou_le <= ?)""",
            (verrou_courant or "", limite))
        ids = []
        for t in rows:
            conn.execute("""UPDATE taches SET etat = 'en_attente', verrou = NULL, verrou_le = NULL,
                            tentatives = MAX(0, tentatives - 1), reprise_le = NULL WHERE id = ?""", (t["id"],))
            evenements.ecrire(conn, "tache_reprise", f"Tâche {t['type']} reprise après coupure",
                              f"Elle était en cours (verrou {t['verrou'] or '?'}) ; elle repart du début.",
                              niveau="alerte", lot_id=t["lot_id"], objet_id=t["objet_id"], tache_id=t["id"])
            ids.append(t["id"])
    return ids


def remettre_en_attente(conn: sqlite3.Connection, tache_id: int, raison: str = "arrêt du worker") -> None:
    """Arrêt propre : une tâche en cours non finie repart en attente sans compter la tentative."""
    with db.transaction(conn):
        t = lire_tache(conn, tache_id)
        if t["etat"] != "en_cours":
            return
        conn.execute("""UPDATE taches SET etat = 'en_attente', verrou = NULL, verrou_le = NULL,
                        tentatives = MAX(0, tentatives - 1), reprise_le = NULL WHERE id = ?""", (tache_id,))
        evenements.ecrire(conn, "tache_remise_en_attente", f"Tâche {t['type']} remise en attente", raison,
                          niveau="info", lot_id=t["lot_id"], objet_id=t["objet_id"], tache_id=tache_id)
