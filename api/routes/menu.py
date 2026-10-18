"""Menu de gauche : badges et collections épinglées (base), jauge de crédits Meshy (adaptateur).

`credits` vaut None quand le solde n'a pas pu être lu : l'interface le dit, sans chiffre inventé."""
from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter

from api import config as cfgmod
from api import db
from api.dependances import Config, Db
from api.services import credits as credits_svc

router = APIRouter(tags=["menu"])

MOIS = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre",
        "octobre", "novembre", "décembre"]


def texte_renouvellement(jour: int, maintenant: datetime | None = None) -> str:
    m = maintenant or datetime.now(UTC)
    jour = 15 if int(jour) == 15 else 1
    if m.day <= jour:  # le jour même, le renouvellement est celui d'aujourd'hui
        prochain = m.replace(day=jour)
    else:
        mois, annee = (m.month + 1, m.year) if m.month < 12 else (1, m.year + 1)
        prochain = m.replace(year=annee, month=mois, day=jour)
    return f"Renouvelés le {'1er' if jour == 1 else jour} {MOIS[prochain.month - 1]}"


@router.get("/menu")
def menu(conn: Db, cfg: Config) -> dict:
    def n(sql: str) -> int:
        return int(db.une(conn, sql)["n"])

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
    jour = meshy.get("renouvellement_jour")
    solde = credits_svc.solde_meshy(conn, cfg)
    credits = None if solde is None else {
        **solde, "renouvellement": texte_renouvellement(jour) if jour in (1, 15) else None}
    return {"badges": badges, "collections": collections, "credits": credits}
