"""Routage (B3) : les règles ordonnées donnent une voie à chaque objet du brief.

Claude classe l'objet (nature : geometrique, ornemental, mixte, personnage) ; les règles, lues en base
dans l'ordre, choisissent la voie : bibliothèque d'abord, puis équivalent CC0, code si un générateur
sait le faire, mixte, IA, « à créer », hors périmètre. Une voie choisie à la main n'est jamais écrasée.
"""
from __future__ import annotations

import sqlite3
from typing import Any

from api import db
from api.services import generateurs_registre as registre

CONDITIONS = ("deja_en_bibliotheque", "equivalent_cc0", "geometrique_avec_generateur", "geometrique_ornemental",
              "ornemental", "geometrique_sans_generateur", "personnage")
VOIES_SANS_FABRICATION = ("reutilise", "hors_perimetre")


def regles(conn: sqlite3.Connection, actives_seulement: bool = True) -> list[dict]:
    sql = "SELECT * FROM regles_routage" + (" WHERE actif = 1" if actives_seulement else "") + " ORDER BY ordre, id"
    return db.toutes(conn, sql)


def asset_reutilisable(conn: sqlite3.Connection, type_objet: str) -> dict | None:
    """Un asset gardé du même type (par l'objet d'origine ou le nom), avec son lot d'origine."""
    cible = registre.normaliser_type(type_objet)
    if not cible:
        return None
    rows = db.toutes(conn, """
        SELECT a.id, a.nom, o.type_objet, l.nom AS lot FROM assets a
        LEFT JOIN objets o ON o.id = a.objet_id LEFT JOIN lots l ON l.id = a.lot_id
        WHERE a.statut = 'garde' ORDER BY a.maj_le DESC""")
    for r in rows:
        if cible in (registre.normaliser_type(r["type_objet"] or ""), registre.normaliser_type(r["nom"])):
            return r
    return None


def catalogue_cc0(conn: sqlite3.Connection, type_objet: str) -> dict | None:
    """Catalogue CC0 : arrive avec la fabrication IA (étape 7). Aucune correspondance pour l'instant."""
    return None


def router(conn: sqlite3.Connection, objet: dict, generateurs: dict[str, dict[str, Any]] | None = None) -> dict:
    """Décision de voie pour un objet proposé : {voie, generateur, regle_id, raison, reutilise_asset_id, pieces}."""
    if generateurs is None:
        generateurs, _ = registre.manifestes()
    nature = str(objet.get("nature") or "")
    type_objet = str(objet.get("type_objet") or objet.get("nom") or "")
    generateur_code = registre.trouver_pour_type(type_objet, generateurs)
    pieces = [dict(p) for p in (objet.get("pieces") or [])]

    for regle in regles(conn):
        c = regle["condition"]
        decision = {"voie": regle["voie"], "generateur": regle["generateur"], "regle_id": regle["id"],
                    "raison": "", "reutilise_asset_id": None, "pieces": pieces}
        if c == "deja_en_bibliotheque":
            asset = asset_reutilisable(conn, type_objet)
            if asset:
                decision.update({"reutilise_asset_id": asset["id"],
                                 "raison": f"Déjà dans ta bibliothèque (lot {asset['lot'] or 'sans lot'}) : réutilisée telle quelle"})
                return decision
        elif c == "equivalent_cc0":
            cc0 = catalogue_cc0(conn, type_objet)
            if cc0:
                decision["raison"] = "Équivalent CC0 trouvé : importé, puis fini, testé et revu comme le reste"
                return decision
        elif c == "geometrique_avec_generateur":
            if nature == "geometrique" and generateur_code:
                decision["generateur"] = generateur_code
                return decision
        elif c == "geometrique_ornemental":
            if nature == "mixte":
                for p in pieces:
                    if p.get("nature") == "ornemental":
                        p["voie"], p["generateur"] = "ia", regle["generateur"]
                    else:
                        g = registre.trouver_pour_type(str(p.get("type_objet") or p.get("nom") or ""), generateurs)
                        p["voie"], p["generateur"] = ("code", g) if g else ("a_creer", None)
                sans_generateur = [p for p in pieces if p["voie"] == "a_creer"]
                if sans_generateur:
                    # Honnête : tant que la pièce géométrique n'a pas de générateur, l'objet est « à créer ».
                    decision.update({"voie": "a_creer", "generateur": None,
                                     "raison": "Mixte : pièce « " + str(sans_generateur[0].get("nom", "")).lower()
                                     + " » sans générateur : à écrire avec Claude Code, ou passer en voie IA"})
                    return decision
                en_code = [str(p.get("nom", "")).lower() for p in pieces if p["voie"] == "code"]
                en_ia = [str(p.get("nom", "")).lower() for p in pieces if p["voie"] == "ia"]
                decision["raison"] = f"{len(pieces)} pièces : {', '.join(en_code)} en code, {', '.join(en_ia)} en IA"
                return decision
        elif c == "ornemental":
            if nature == "ornemental":
                return decision
        elif c == "geometrique_sans_generateur":
            if nature == "geometrique" and not generateur_code:
                decision["raison"] = "Aucun générateur pour ce type : à écrire avec Claude Code, ou passer en voie IA"
                return decision
        elif c == "personnage":
            if nature == "personnage":
                decision["raison"] = "Personnage ou créature : hors périmètre pour l'instant"
                return decision
    # Aucune règle : honnête, à créer.
    return {"voie": "a_creer", "generateur": None, "regle_id": None, "pieces": pieces, "reutilise_asset_id": None,
            "raison": "Aucune règle de routage ne s'applique : à écrire avec Claude Code, ou passer en voie IA"}
