"""Suivi des coûts (table couts) : crédits Meshy, tokens et dollars de l'API Claude.

- Chaque appel payant est enregistré avec sa tâche.
- La dépense Claude du mois est comparée au plafond : au-delà, l'appel est refusé.
- Les crédits Meshy sont comptés depuis le dernier renouvellement (jour 1 ou 15) ;
  à `alerte_pct` %, une notification est écrite (une seule par période).
"""
from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime

from api import config as cfgmod
from api import db
from api.services import evenements

# Tarifs par million de tokens (entrée, sortie), en USD.
PRIX_PAR_MILLION = {
    "claude-sonnet-5-5": (2.00, 10.00),
    "claude-haiku-5-5": (0.10, 0.50),
}
# Crédits Meshy : 30 par objet 3D texturé, 3 par image de référence.
CREDITS_MESHY_3D = 30
CREDITS_MESHY_IMAGE = 3


class PlafondAtteint(RuntimeError):
    """Le plafond mensuel de l'API Claude est atteint : l'appel est refusé."""


def prix_usd(modele: str, tokens_entree: int, tokens_sortie: int) -> float:
    entree, sortie = PRIX_PAR_MILLION.get(modele, PRIX_PAR_MILLION["claude-sonnet-5-5"])
    return round((tokens_entree * entree + tokens_sortie * sortie) / 1_000_000, 6)


def enregistrer(
    conn: sqlite3.Connection,
    service: str,
    *,
    credits: int = 0,
    usd: float = 0.0,
    tokens_entree: int = 0,
    tokens_sortie: int = 0,
    tache_id: int | None = None,
    detail: dict | None = None,
) -> int:
    return db.inserer(conn, "couts", {
        "date": db.maintenant(), "service": service, "tache_id": tache_id,
        "credits": int(credits), "usd": float(usd), "tokens_entree": int(tokens_entree),
        "tokens_sortie": int(tokens_sortie), "detail": json.dumps(detail or {}, ensure_ascii=False),
    })


def debut_du_mois(maintenant: datetime | None = None) -> str:
    m = maintenant or datetime.now(UTC)
    return m.replace(day=1, hour=0, minute=0, second=0, microsecond=0).isoformat().replace("+00:00", "Z")


def debut_periode_meshy(renouvellement_jour: int, maintenant: datetime | None = None) -> str:
    """Date ISO du dernier renouvellement des crédits (jour 1 ou 15 du mois)."""
    m = maintenant or datetime.now(UTC)
    jour = 15 if int(renouvellement_jour) == 15 else 1
    if m.day >= jour:
        debut = m.replace(day=jour)
    else:
        mois, annee = (m.month - 1, m.year) if m.month > 1 else (12, m.year - 1)
        debut = m.replace(year=annee, month=mois, day=jour)
    return debut.replace(hour=0, minute=0, second=0, microsecond=0).isoformat().replace("+00:00", "Z")


def depense_claude_mois(conn: sqlite3.Connection) -> dict:
    """{"usd", "briefs", "avis"} : dépense Claude depuis le 1er du mois."""
    r = db.une(conn, """
        SELECT COALESCE(SUM(usd), 0) AS usd,
               COALESCE(SUM(json_extract(detail, '$.type') = 'brief'), 0) AS briefs,
               COALESCE(SUM(json_extract(detail, '$.type') = 'avis'), 0) AS avis
        FROM couts WHERE service = 'claude' AND date >= ?""", (debut_du_mois(),))
    return {"usd": round(float(r["usd"]), 4), "briefs": int(r["briefs"]), "avis": int(r["avis"])}


def credits_meshy_utilises(conn: sqlite3.Connection, cfg: dict) -> int:
    jour = cfgmod.service(cfg, "meshy").get("renouvellement_jour", 1)
    r = db.une(conn, "SELECT COALESCE(SUM(credits), 0) AS c FROM couts WHERE service='meshy' AND date >= ?",
               (debut_periode_meshy(jour),))
    return int(r["c"])


def verifier_plafond_claude(conn: sqlite3.Connection, cfg: dict) -> None:
    """Lève PlafondAtteint si la dépense du mois atteint le plafond mensuel."""
    plafond = float(cfgmod.service(cfg, "claude").get("plafond_mensuel_usd", 5.0))
    depense = depense_claude_mois(conn)["usd"]
    if plafond > 0 and depense >= plafond:
        raise PlafondAtteint(
            f"plafond mensuel de l'API Claude atteint ({depense:.2f} $ sur {plafond:.2f} $)")


def enregistrer_appel_claude(conn: sqlite3.Connection, cfg: dict, usage: dict, type: str,
                             tache_id: int | None = None) -> float:
    """Enregistre un appel Claude à partir de son usage ; renvoie le coût en USD."""
    modele = str(usage.get("modele") or cfgmod.service(cfg, "claude").get("modele", "claude-sonnet-5-5"))
    te, ts = int(usage.get("tokens_entree", 0)), int(usage.get("tokens_sortie", 0))
    usd = prix_usd(modele, te, ts)
    enregistrer(conn, "claude", usd=usd, tokens_entree=te, tokens_sortie=ts, tache_id=tache_id,
                detail={"type": type, "modele": modele})
    return usd


def enregistrer_credits_meshy(conn: sqlite3.Connection, cfg: dict, credits: int, type: str,
                              tache_id: int | None = None) -> None:
    """Enregistre des crédits Meshy consommés et déclenche l'alerte au seuil configuré."""
    enregistrer(conn, "meshy", credits=credits, tache_id=tache_id, detail={"type": type})
    verifier_alerte_credits(conn, cfg)


def verifier_alerte_credits(conn: sqlite3.Connection, cfg: dict) -> bool:
    """Écrit une notification (une par période) si les crédits dépassent alerte_pct."""
    meshy = cfgmod.service(cfg, "meshy")
    pct_alerte = int(meshy.get("alerte_pct", 80) or 0)
    total = int(meshy.get("credits_mensuels", 0) or 0)
    if pct_alerte <= 0 or total <= 0:
        return False
    utilises = credits_meshy_utilises(conn, cfg)
    pct = 100 * utilises / total
    if pct < pct_alerte:
        return False
    debut = debut_periode_meshy(meshy.get("renouvellement_jour", 1))
    deja = db.une(conn, "SELECT 1 AS x FROM evenements WHERE type=? AND date >= ? LIMIT 1",
                  (evenements.CREDITS_ALERTE, debut))
    if deja:
        return False
    evenements.ecrire(conn, evenements.CREDITS_ALERTE, f"Crédits Meshy à {pct:.0f} %",
                      f"{utilises} crédits utilisés sur {total} depuis le dernier renouvellement.",
                      niveau="alerte", lien="/reglages")
    return True
