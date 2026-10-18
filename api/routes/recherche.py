"""Recherche globale (barre du haut) sur la table FTS5 `recherche`."""
from __future__ import annotations

import re

from fastapi import APIRouter, Depends, Query

from api import db
from api.dependances import get_db

router = APIRouter(tags=["recherche"])
_MOT = re.compile(r"[\w'-]+", re.UNICODE)

LIENS = {
    "asset": lambda rid: f"/assets/{rid}",
    "lot": lambda rid: f"/lots/{rid}",
    "collection": lambda rid: f"/bibliotheque?collection={rid}",
    "etiquette": lambda rid: f"/bibliotheque?etiquette={rid}",
}


def requete_fts(q: str) -> str:
    """Chaque mot devient un préfixe entre guillemets : `scut lot` → `"scut"* "lot"*`."""
    mots = [m.replace('"', "") for m in _MOT.findall(q)]
    return " ".join(f'"{m}"*' for m in mots if m)


@router.get("/recherche")
def rechercher(q: str = Query("", max_length=200), limit: int = Query(20, ge=1, le=100),
               conn=Depends(get_db)) -> dict:
    requete = requete_fts(q)
    if not requete:
        return {"resultats": []}
    rows = db.toutes(conn, """
        SELECT type, ref_id, nom, lot FROM recherche WHERE recherche MATCH ? ORDER BY rank LIMIT ?""",
        (requete, limit))
    resultats = []
    for r in rows:
        titre = r["nom"].split(" ")[0] if r["type"] == "asset" else r["nom"]
        resultats.append({"type": r["type"], "id": r["ref_id"], "titre": titre,
                          "lien": LIENS.get(r["type"], lambda rid: "/")(r["ref_id"])})
    return {"resultats": resultats}
