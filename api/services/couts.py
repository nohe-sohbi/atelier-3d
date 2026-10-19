"""Suivi des coûts (A6) : une ligne par appel payant, dans la table `couts`.

- Meshy : les crédits de chaque tâche (images de planche, plus tard 3D) ; la jauge, elle, lit le solde de l'adaptateur.
- API Claude : les tokens de chaque appel, convertis en dollars avec les tarifs de la config
  (`services.claude.tarifs_usd_par_million`). Un appel simulé ne coûte rien et le dit (`simule = 1`).
- Le plafond mensuel Claude (Réglages) se compare à la dépense réelle du mois.
"""
from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime

from api import config as cfgmod
from api import db

# Tarifs de l'API Claude, en dollars par million de tokens (entrée, sortie), relevés sur la documentation
# d'Anthropic le 6 octobre 2026. Haiku 5.5 : ce tarif vaut jusqu'à 100 000 tokens d'entrée par requête.
# Modifiables dans config.local.yaml si Anthropic les change.
TARIFS_CLAUDE = {"claude-sonnet-5-5": (2.0, 10.0), "claude-haiku-5-5": (0.10, 0.50)}


class PlafondAtteint(RuntimeError):
    """La dépense réelle du mois a atteint le plafond réglé : aucun appel réel de plus ce mois-ci."""


def tarifs_claude(cfg: dict) -> dict[str, tuple[float, float]]:
    reglage = cfgmod.service(cfg, "claude").get("tarifs_usd_par_million") or {}
    tarifs = dict(TARIFS_CLAUDE)
    for modele, (entree, sortie) in reglage.items():
        tarifs[str(modele)] = (float(entree), float(sortie))
    return tarifs


def usd_claude(cfg: dict, modele: str, tokens_entree: int, tokens_sortie: int) -> float | None:
    """Le prix d'un appel, ou None quand le modèle n'a pas de tarif connu (jamais un prix inventé)."""
    tarif = tarifs_claude(cfg).get(modele)
    if tarif is None:
        return None
    return round((tokens_entree * tarif[0] + tokens_sortie * tarif[1]) / 1_000_000, 6)


def enregistrer(conn: sqlite3.Connection, service: str, type: str, *, simule: bool, credits: int = 0,
                usd: float = 0.0, tokens_entree: int = 0, tokens_sortie: int = 0, lot_id: int | None = None,
                tache_id: int | None = None, detail: dict | None = None) -> int:
    return db.inserer(conn, "couts", {
        "date": db.maintenant(), "service": service, "type": type, "tache_id": tache_id, "lot_id": lot_id,
        "credits": int(credits), "usd": 0.0 if simule else float(usd), "tokens_entree": int(tokens_entree),
        "tokens_sortie": int(tokens_sortie), "simule": 1 if simule else 0,
        "detail": json.dumps(detail or {}, ensure_ascii=False),
    })


def enregistrer_claude(conn: sqlite3.Connection, cfg: dict, type: str, usage: dict, *, simule: bool,
                       lot_id: int | None = None, tache_id: int | None = None, detail: dict | None = None) -> int:
    modele = str(usage.get("modele") or cfgmod.service(cfg, "claude").get("modele") or "")
    entree, sortie = int(usage.get("tokens_entree", 0)), int(usage.get("tokens_sortie", 0))
    usd = usd_claude(cfg, modele, entree, sortie)
    return enregistrer(conn, "claude", type, simule=simule, usd=usd or 0.0, tokens_entree=entree, tokens_sortie=sortie,
                       lot_id=lot_id, tache_id=tache_id,
                       detail={"modele": modele, "tarif_connu": usd is not None, **(detail or {})})


def _debut_du_mois() -> str:
    d = datetime.now(UTC)
    return f"{d.year:04d}-{d.month:02d}-01T00:00:00Z"


def depense_claude_mois(conn: sqlite3.Connection) -> dict:
    """La dépense réelle du mois (appels simulés comptés à part, à 0 $)."""
    r = db.une(conn, """
        SELECT COALESCE(SUM(CASE WHEN simule = 0 THEN usd END), 0) AS usd,
               COUNT(CASE WHEN simule = 0 THEN 1 END) AS appels,
               COUNT(CASE WHEN simule = 0 AND type = 'brief' THEN 1 END) AS briefs,
               COUNT(CASE WHEN simule = 0 AND type = 'avis' THEN 1 END) AS avis,
               COUNT(CASE WHEN simule = 1 THEN 1 END) AS simules,
               COUNT(CASE WHEN simule = 0 AND detail LIKE '%"tarif_connu": false%' THEN 1 END) AS sans_tarif
          FROM couts WHERE service = 'claude' AND date >= ?""", (_debut_du_mois(),))
    return {"usd": round(float(r["usd"]), 4), "appels": int(r["appels"]), "briefs": int(r["briefs"]),
            "avis": int(r["avis"]), "appels_simules": int(r["simules"]), "sans_tarif": int(r["sans_tarif"])}


def verifier_plafond_claude(conn: sqlite3.Connection, cfg: dict) -> None:
    """Lève PlafondAtteint avant un appel réel quand la dépense du mois atteint le plafond réglé."""
    plafond = float(cfgmod.service(cfg, "claude").get("plafond_mensuel_usd", 0) or 0)
    if plafond <= 0:
        return
    depense = depense_claude_mois(conn)["usd"]
    if depense >= plafond:
        raise PlafondAtteint(f"plafond mensuel de l'API Claude atteint ({depense:.2f} $ sur {plafond:.2f} $) : "
                             "relève-le dans Réglages, ou attends le mois prochain")


def credits_meshy_lot(conn: sqlite3.Connection, lot_id: int) -> dict:
    r = db.une(conn, """SELECT COALESCE(SUM(credits), 0) AS credits, COUNT(CASE WHEN simule = 1 THEN 1 END) AS simules,
                               COUNT(*) AS lignes
                          FROM couts WHERE service = 'meshy' AND lot_id = ?""", (lot_id,))
    return {"credits": int(r["credits"]), "simule": int(r["lignes"]) > 0 and int(r["simules"]) == int(r["lignes"])}
