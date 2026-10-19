"""Proposition de liste (B2) : Claude classe les objets du brief, les règles de routage choisissent la voie.

Claude reçoit le style (palette, catégories, dimensions connues) et le besoin, répond un JSON structuré :
objets (nom, type, description, catégorie, nature, symétrie, famille, dimensions, matériaux, pièces,
paramètres suggérés) et un nom de lot. La voie n'est jamais demandée à Claude : elle vient des règles
(api/services/routage.py). L'appel passe par la file `api` ; son coût est consigné (tokens, simulé ou non).
"""
from __future__ import annotations

import json
import sqlite3
from typing import Any

from api import config as cfgmod
from api import db
from api.services import couts, evenements, generateurs_registre, routage, taches
from api.services import lots as lots_svc
from api.services import styles as styles_svc
from api.services.taches import TacheDefinitive

TYPE_TACHE_PROPOSITION = "proposer_liste"
NATURES = ("geometrique", "ornemental", "mixte", "personnage")
CATEGORIES = ("petit_prop", "prop_moyen", "grand_prop", "module_archi")
MAX_OBJETS = 20

SCHEMA: dict[str, Any] = {
    "title": "proposition_brief",
    "type": "object",
    "additionalProperties": False,
    "required": ["nom_lot", "objets"],
    "properties": {
        "nom_lot": {"type": "string", "description": "Nom court du lot, 2 à 5 mots, dans la langue du besoin."},
        "objets": {
            "type": "array", "minItems": 1, "maxItems": MAX_OBJETS,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["nom", "type_objet", "description", "categorie", "nature", "symetrique", "famille",
                             "dimensions_m", "materiaux", "pieces", "parametres_suggeres"],
                "properties": {
                    "nom": {"type": "string"},
                    "type_objet": {"type": "string", "description": "Type générique en minuscules sans accent : 'bouclier rond', 'amphore'."},
                    "description": {"type": "string", "description": "Une phrase : forme, usage, ce qui le distingue."},
                    "categorie": {"type": "string", "enum": list(CATEGORIES)},
                    "nature": {"type": "string", "enum": list(NATURES),
                               "description": "geometrique : formes simples, symétriques ou fines ; ornemental : organique, sculpté ; "
                                              "mixte : une partie géométrique et une partie ornementale ; personnage : être vivant."},
                    "symetrique": {"type": ["string", "null"], "enum": ["X", "Y", None]},
                    "famille": {"type": "string", "enum": list(generateurs_registre.FAMILLES)},
                    "dimensions_m": {
                        "type": "object", "additionalProperties": False,
                        "required": ["largeur", "profondeur", "hauteur"],
                        "properties": {"largeur": {"type": "number"}, "profondeur": {"type": "number"}, "hauteur": {"type": "number"}},
                    },
                    "materiaux": {"type": "array", "items": {"type": "string"}, "description": "Noms de matériaux du style."},
                    "pieces": {
                        "type": "array",
                        "description": "Pour un objet mixte seulement : chaque pièce avec sa nature.",
                        "items": {
                            "type": "object", "additionalProperties": False,
                            "required": ["nom", "nature", "type_objet"],
                            "properties": {"nom": {"type": "string"},
                                           "nature": {"type": "string", "enum": ["geometrique", "ornemental"]},
                                           "type_objet": {"type": "string"}},
                        },
                    },
                    "parametres_suggeres": {"type": "array", "items": {"type": "string"},
                                            "description": "Paramètres qu'un générateur code devrait exposer."},
                },
            },
        },
    },
}


class PropositionInvalide(ValueError):
    """La réponse de Claude ne respecte pas le schéma ou n'est pas exploitable."""


# --- prompts -------------------------------------------------------------------------

def prompt_systeme(style, types_connus: list[str]) -> str:
    cats = ", ".join(f"{c} (≤ {style.budgets_tris.get(c, '?')} tris)" for c in CATEGORIES)
    dims = "; ".join(f"{t} {d[0]}×{d[1]}×{d[2]} m" for t, d in style.dimensions_m.items())
    return (
        "Tu es l'assistant d'un atelier qui fabrique des assets 3D de jeu vidéo. À partir d'un besoin, tu proposes "
        "la liste des objets à fabriquer, chacun classé. Tu ne choisis jamais la voie de fabrication : tu décris et "
        "tu classes, les règles de routage de l'atelier décident.\n"
        f"Style : {style.brut.get('nom', style.nom)} ({style.direction}). {style.description}\n"
        f"Palette : {', '.join(style.palette)}. Matériaux disponibles : {', '.join(style.materiaux)}.\n"
        f"Catégories de budget : {cats}.\n"
        f"Dimensions réelles connues (largeur × profondeur × hauteur) : {dims}.\n"
        f"Types connus : {', '.join(types_connus) if types_connus else 'aucun'}. Quand un objet correspond à un type connu, "
        "utilise exactement ce type_objet.\n"
        "Natures : geometrique (formes simples, symétriques ou fines, faisables par un script), ornemental (organique, "
        "sculpté, mieux rendu par l'IA), mixte (une partie géométrique et une partie ornementale : liste les pièces), "
        "personnage (être vivant : hors périmètre, à signaler quand même).\n"
        "Unités : mètres. Haut = +Z, face avant = -Y. Réponds uniquement avec le JSON demandé, en français."
    )


def prompt_utilisateur(lot: dict) -> str:
    return (f"Thème : {lot['theme'] or 'non précisé'}.\nBesoin : {lot['besoin'] or 'non précisé'}.\n"
            f"Propose entre 5 et {MAX_OBJETS} objets, du plus structurant au plus décoratif, sans doublon.")


# --- demande (API) ----------------------------------------------------------------------

def proposer(conn: sqlite3.Connection, cfg: dict, lot_id: int) -> int:
    """Crée la tâche `proposer_liste` (file api) et la rattache au lot ; renvoie son id."""
    lot = lots_svc._ligne(conn, lot_id)
    if not (lot["besoin"] or "").strip():
        raise lots_svc.BriefIncomplet("écris ce que tu veux (une phrase suffit) avant de demander une liste")
    if lot["style_id"] is None or db.une(conn, "SELECT 1 FROM styles WHERE id = ?", (lot["style_id"],)) is None:
        raise lots_svc.BriefIncomplet("choisis un style : il fixe la palette, les matériaux et les budgets du lot")
    en_cours = lot["proposition_tache_id"] and db.une(
        conn, "SELECT 1 FROM taches WHERE id = ? AND etat IN ('en_attente', 'en_cours')", (lot["proposition_tache_id"],))
    if en_cours:
        return int(lot["proposition_tache_id"])
    tache_id = taches.creer_tache(conn, TYPE_TACHE_PROPOSITION, "api", {"lot_id": lot_id}, lot_id=lot_id, cfg=cfg)
    conn.execute("UPDATE lots SET proposition_tache_id = ?, maj_le = ? WHERE id = ?", (tache_id, db.maintenant(), lot_id))
    conn.commit()
    return tache_id


# --- exécution (worker) -------------------------------------------------------------------

def _nombre(v: Any, defaut: float = 0.5) -> float:
    try:
        x = float(v)
    except (TypeError, ValueError):
        return defaut
    return x if x > 0 else defaut


def valider_reponse(reponse: Any) -> dict:
    """Normalise et vérifie la réponse de Claude : lève PropositionInvalide plutôt que d'inventer."""
    if not isinstance(reponse, dict) or not isinstance(reponse.get("objets"), list) or not reponse["objets"]:
        raise PropositionInvalide("réponse sans liste d'objets")
    objets = []
    vus: set[str] = set()
    for i, o in enumerate(reponse["objets"][:MAX_OBJETS], start=1):
        if not isinstance(o, dict) or not str(o.get("nom", "")).strip():
            raise PropositionInvalide(f"objet {i} : nom manquant")
        nature = str(o.get("nature", "")).strip()
        if nature not in NATURES:
            raise PropositionInvalide(f"objet {i} ({o['nom']}) : nature {nature!r} inconnue")
        categorie = str(o.get("categorie", "")).strip()
        if categorie not in CATEGORIES:
            raise PropositionInvalide(f"objet {i} ({o['nom']}) : catégorie {categorie!r} inconnue")
        type_objet = generateurs_registre.normaliser_type(o.get("type_objet") or o["nom"])
        if type_objet in vus:
            continue  # doublon : on garde le premier
        vus.add(type_objet)
        dims = o.get("dimensions_m") or {}
        if not isinstance(dims, dict):
            dims = {}
        pieces = []
        for j, p in enumerate(o.get("pieces") or [], start=1):
            if not isinstance(p, dict) or not str(p.get("nom", "")).strip():
                raise PropositionInvalide(f"objet {i} ({o['nom']}) : pièce {j} sans nom")
            pieces.append({"ordre": j, "nom": str(p["nom"]).strip(),
                           "nature": "ornemental" if p.get("nature") == "ornemental" else "geometrique",
                           "type_objet": generateurs_registre.normaliser_type(p.get("type_objet") or p["nom"])})
        if nature == "mixte" and len(pieces) < 2:
            raise PropositionInvalide(f"objet {i} ({o['nom']}) : un objet mixte décrit au moins 2 pièces")
        sym = o.get("symetrique")
        objets.append({
            "nom": str(o["nom"]).strip()[:120], "type_objet": type_objet,
            "description": str(o.get("description", "")).strip()[:600], "categorie": categorie, "nature": nature,
            "symetrique": sym if sym in ("X", "Y") else None,
            "famille": o.get("famille") if o.get("famille") in generateurs_registre.FAMILLES else "props",
            "dimensions": {"largeur": _nombre(dims.get("largeur")), "profondeur": _nombre(dims.get("profondeur")),
                           "hauteur": _nombre(dims.get("hauteur"))},
            "materiaux": [str(m) for m in (o.get("materiaux") or []) if str(m).strip()][:8],
            "pieces": pieces,
            "parametres": [str(p) for p in (o.get("parametres_suggeres") or []) if str(p).strip()][:12],
        })
    if not objets:
        raise PropositionInvalide("aucun objet exploitable dans la réponse")
    return {"nom_lot": str(reponse.get("nom_lot", "")).strip()[:120], "objets": objets}


def _dimensions_du_style(style, type_objet: str, proposees: dict) -> dict:
    """Celles du style quand le type y figure (source des tests), sinon celles proposées par Claude."""
    for t, d in style.dimensions_m.items():
        if generateurs_registre.normaliser_type(t) == type_objet:
            return {"largeur": d[0], "profondeur": d[1], "hauteur": d[2], "source": "style"}
    return {**proposees, "source": "claude"}


def router_objet(conn: sqlite3.Connection, objet: dict, generateurs: dict, voie_forcee: dict | None = None) -> dict:
    """Décision de voie : celle choisie à la main pour ce type, sinon les règles."""
    if voie_forcee:
        return {"voie": voie_forcee["voie"], "generateur": voie_forcee.get("generateur"), "regle_id": None,
                "raison": voie_forcee.get("raison_voie") or "Voie choisie à la main", "reutilise_asset_id": None,
                "pieces": objet.get("pieces") or [], "forcee": True}
    return {**routage.router(conn, objet, generateurs), "forcee": False}


def appliquer(conn: sqlite3.Connection, lot_id: int, proposition: dict, usage: dict, simule: bool,
              tache_id: int | None = None, cfg: dict | None = None) -> dict:
    """Remplace les objets du lot par la liste proposée, en gardant les décisions prises sur les mêmes types
    (objet décoché, voie choisie à la main) ; route chaque objet ; consigne le coût."""
    lot = lots_svc._ligne(conn, lot_id)
    style = styles_svc.charger_style(db.une(conn, "SELECT code FROM styles WHERE id = ?", (lot["style_id"],))["code"])
    generateurs, _ = generateurs_registre.manifestes()
    anciens = {o["type_objet"]: o for o in lots_svc.objets_du_lot(conn, lot_id)}
    with db.transaction(conn):
        conn.execute("DELETE FROM objets WHERE lot_id = ? AND etape = 'brief'", (lot_id,))
        ids = []
        for ordre, o in enumerate(proposition["objets"], start=1):
            ancien = anciens.get(o["type_objet"])
            decision = router_objet(conn, o, generateurs, ancien if ancien and ancien["voie_forcee"] else None)
            dims = _dimensions_du_style(style, o["type_objet"], o["dimensions"])
            oid = db.inserer(conn, "objets", {
                "lot_id": lot_id, "nom": o["nom"], "type_objet": o["type_objet"], "description": o["description"],
                "categorie": o["categorie"], "nature": o["nature"], "dimensions_json": json.dumps(dims),
                "voie": decision["voie"], "voie_forcee": 1 if decision["forcee"] else 0, "raison_voie": decision["raison"],
                "regle_id": decision["regle_id"], "generateur": decision["generateur"], "etape": "brief",
                "retire": 1 if (ancien and ancien["retire"]) or decision["voie"] == "hors_perimetre" else 0,
                "reutilise_asset_id": decision["reutilise_asset_id"], "symetrique": o["symetrique"], "famille": o["famille"],
                "materiaux_json": json.dumps(o["materiaux"], ensure_ascii=False),
                "parametres_json": json.dumps(o["parametres"], ensure_ascii=False), "ordre": ordre,
            })
            for p in decision["pieces"]:
                db.inserer(conn, "pieces", {"objet_id": oid, "ordre": p.get("ordre", 0), "nom": p["nom"], "nature": p["nature"],
                                            "type_objet": p.get("type_objet", ""), "voie": p.get("voie", "a_creer"),
                                            "generateur": p.get("generateur"), "etape": "brief"})
            ids.append(oid)
        nom_propose = proposition["nom_lot"]
        conn.execute("UPDATE lots SET nom_propose = ?, nom = CASE WHEN nom = '' THEN ? ELSE nom END, maj_le = ? WHERE id = ?",
                     (nom_propose, nom_propose, db.maintenant(), lot_id))
        couts.enregistrer_claude(conn, cfg if cfg is not None else cfgmod.charger(), "brief", usage, simule=simule,
                                 lot_id=lot_id, tache_id=tache_id, detail={"objets": len(ids)})
        evenements.ecrire(conn, "liste_proposee", f"Liste proposée{' (simulée)' if simule else ''} : {lot['nom'] or nom_propose or lot_id}",
                          f"{len(ids)} objets classés et routés.", niveau="succes", lien=f"/lots/{lot_id}/brief",
                          lot_id=lot_id, tache_id=tache_id)
    lots_svc.synchroniser_etat(conn, lot_id)
    return {"objets": ids, "nom_lot": nom_propose, "simule": simule}


def executer_proposition(conn: sqlite3.Connection, claude, params: dict, tache_id: int | None = None,
                         cfg: dict | None = None) -> dict:
    """Corps de la tâche `proposer_liste` : appelle Claude (sous le plafond mensuel en réel), valide, applique."""
    cfg = cfg if cfg is not None else cfgmod.charger()
    lot_id = int(params["lot_id"])
    lot = lots_svc._ligne(conn, lot_id)
    if lot["style_id"] is None:
        raise TacheDefinitive("le lot n'a pas de style : choisis-en un dans le Brief")
    style = styles_svc.charger_style(db.une(conn, "SELECT code FROM styles WHERE id = ?", (lot["style_id"],))["code"])
    generateurs, _ = generateurs_registre.manifestes()
    types = generateurs_registre.types_connus(generateurs)
    types += [generateurs_registre.normaliser_type(t) for t in style.dimensions_m if generateurs_registre.normaliser_type(t) not in types]
    if getattr(claude, "mode", "") == "reel":
        try:
            couts.verifier_plafond_claude(conn, cfg)
        except couts.PlafondAtteint as e:
            raise TacheDefinitive(str(e)) from e
    try:
        reponse, usage = claude.completer_json(prompt_systeme(style, types), prompt_utilisateur(lot), SCHEMA)
    except RuntimeError as e:
        if "clé" in str(e) or "plafond" in str(e):
            raise TacheDefinitive(str(e)) from e
        raise
    try:
        proposition = valider_reponse(reponse)
    except PropositionInvalide as e:
        raise RuntimeError(f"réponse de Claude inexploitable : {e}") from e
    simule = getattr(claude, "mode", "") == "simule"
    return appliquer(conn, lot_id, proposition, usage, simule, tache_id=tache_id, cfg=cfg)


def rerouter_lot(conn: sqlite3.Connection, lot_id: int, generateurs: dict | None = None) -> list[int]:
    """Refait passer les règles sur les objets « à créer » non forcés (un script est apparu) ; renvoie les objets changés."""
    if generateurs is None:
        generateurs, _ = generateurs_registre.manifestes()
    changes = []
    for o in lots_svc.objets_du_lot(conn, lot_id):
        if o["voie_forcee"] or o["etape"] != "brief" or o["voie"] not in ("a_creer", "mixte"):
            continue
        decision = routage.router(conn, o, generateurs)
        pieces_changees = [p for p in decision["pieces"]] if o["voie"] == "mixte" else []
        if decision["voie"] == o["voie"] and decision["generateur"] == o["generateur"] and not any(
                p.get("voie") != q["voie"] for p, q in zip(pieces_changees, o["pieces"], strict=False)):
            continue
        conn.execute("UPDATE objets SET voie = ?, generateur = ?, regle_id = ?, raison_voie = ? WHERE id = ?",
                     (decision["voie"], decision["generateur"], decision["regle_id"], decision["raison"], o["id"]))
        for p, q in zip(decision["pieces"], o["pieces"], strict=False):
            conn.execute("UPDATE pieces SET voie = ?, generateur = ? WHERE id = ?", (p.get("voie", "a_creer"), p.get("generateur"), q["id"]))
        changes.append(o["id"])
    if changes:
        conn.commit()
    return changes
