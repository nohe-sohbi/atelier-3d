"""Règles de routage, en lecture (le Brief les explique ; l'éditeur arrive avec Générateurs, étape 11)."""
from __future__ import annotations

from fastapi import APIRouter

from api.dependances import Db
from api.services import generateurs_registre, routage

router = APIRouter(prefix="/routage", tags=["routage"])


@router.get("/regles")
def regles(conn: Db) -> dict:
    generateurs, erreurs = generateurs_registre.manifestes()
    return {
        "regles": [{"id": r["id"], "ordre": r["ordre"], "condition": r["condition"], "quand": r["libelle_quand"],
                    "alors": r["libelle_alors"], "voie": r["voie"], "generateur": r["generateur"],
                    "generateur_secours": r["generateur_secours"], "actif": bool(r["actif"]),
                    # Honnête sur ce qui marche déjà : bibliothèque et CC0 n'ont rien à comparer avant les étapes 7 et 9.
                    "operationnelle": r["condition"] not in ("equivalent_cc0",)}
                   for r in routage.regles(conn, actives_seulement=False)],
        "generateurs_code": [{"nom": nom, "titre": m["titre"], "types": list(m["types"])} for nom, m in generateurs.items()],
        "generateurs_invalides": erreurs,
    }
