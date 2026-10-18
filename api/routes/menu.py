"""Menu de gauche : badges, collections épinglées, jauge de crédits Meshy. Tout vient de la base."""
from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends

from api import config as cfgmod
from api import db
from api.dependances import get_config, get_db
from api.services import couts

router = APIRouter(tags=["menu"])

MOIS = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre",
        "octobre", "novembre", "décembre"]


def texte_renouvellement(jour: int, maintenant: datetime | None = None) -> str:
    m = maintenant or datetime.now(UTC)
    jour = 15 if int(jour) == 15 else 1
    if m.day < jour:
        prochain = m.replace(day=jour)
    else:
        mois, annee = (m.month + 1, m.year) if m.month < 12 else (1, m.year + 1)
        prochain = m.replace(year=annee, month=mois, day=jour)
    return f"Renouvelés le {'1er' if jour == 1 else jour} {MOIS[prochain.month - 1]}"


@router.get("/menu")
def menu(conn=Depends(get_db), cfg: dict = Depends(get_config)) -> dict:
    n = lambda sql, p=(): int(db.une(conn, sql, p)["n"])  # noqa: E731
    badges = {
        "lots": n("SELECT COUNT(*) AS n FROM lots WHERE etat = 'en_cours'"),
        "bibliotheque": n("SELECT COUNT(*) AS n FROM assets WHERE statut = 'garde'"),
        "generateurs": n("SELECT COUNT(*) AS n FROM bancs WHERE etat = 'termine' AND decision IS NULL"),
    }
    collections = [
        {"id": r["id"], "nom": r["nom"], "couleur": r["couleur"], "nombre": int(r["nombre"])}
        for r in db.toutes(conn, """
            SELECT c.id, c.nom, c.couleur, COUNT(ca.asset_id) AS nombre
            FROM collections c LEFT JOIN collections_assets ca ON ca.collection_id = c.id
            WHERE c.epinglee = 1 GROUP BY c.id ORDER BY c.nom""")
    ]
    meshy = cfgmod.service(cfg, "meshy")
    total = int(meshy.get("credits_mensuels", 0) or 0)
    utilises = couts.credits_meshy_utilises(conn, cfg)
    jour = meshy.get("renouvellement_jour")
    credits = {"utilises": utilises, "total": total, "restants": max(0, total - utilises),
               "renouvellement": texte_renouvellement(jour) if jour in (1, 15) else None}
    return {"badges": badges, "collections": collections, "credits": credits}
