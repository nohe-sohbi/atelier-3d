"""Demande pour Claude Code (Brief, voie « À créer ») : un Markdown dans generators/demandes/<type>.md.

L'app écrit la demande (style, dimensions, budget, matériaux, intention) ; Claude Code, hors de l'app,
écrit generators/<type>.py. Le worker surveille le dossier : dès que le script apparaît avec un
MANIFESTE valide, les objets « à créer » de ce type sont re-routés (voie code) et un événement le dit.
Les tests du script (finition, Blender) arrivent aux étapes 5 et 11 : l'état le dit tel quel.
"""
from __future__ import annotations

import re
import sqlite3
from pathlib import Path

from api import chemins, db
from api.services import evenements, generateurs_registre, style_yaml
from api.services import lots as lots_svc
from api.services import styles as styles_svc

DOSSIER_DEMANDES = "demandes"
ETATS = ("a_ecrire", "ecrite", "script_detecte")
LIBELLES_ETATS = {"a_ecrire": "Pas encore écrite", "ecrite": "Écrite dans le dépôt", "script_detecte": "Script détecté"}
_NOM = re.compile(r"^[a-z0-9]+(?:_[a-z0-9]+)*$")


def nom_module(type_objet: str) -> str:
    """'bouclier rond' -> 'bouclier_rond' : le nom du fichier generators/<nom>.py attendu."""
    nom = generateurs_registre.normaliser_type(type_objet).replace(" ", "_")
    nom = re.sub(r"[^a-z0-9_]+", "", nom).strip("_")
    if not nom or not _NOM.match(nom):
        raise ValueError(f"type d'objet inutilisable pour un nom de script : {type_objet!r}")
    return nom


def chemin_relatif(type_objet: str) -> str:
    return f"generators/{DOSSIER_DEMANDES}/{nom_module(type_objet)}.md"


def _chemin_absolu(type_objet: str) -> Path:
    racine = chemins.dossier_generateurs().resolve()
    chemin = (racine / DOSSIER_DEMANDES / f"{nom_module(type_objet)}.md").resolve()
    if racine not in chemin.parents:
        raise ValueError("chemin hors du dossier des générateurs")
    return chemin


def _fmt(x: float) -> str:
    """Deux décimales et virgule, comme la maquette : 1.2 -> « 1,20 »."""
    return f"{x:.2f}".replace(".", ",")


def texte_dimensions(d: dict | None) -> str:
    """« 1,20 × 1,60 m, profondeur 0,40 m » (largeur × hauteur, puis profondeur)."""
    if not d:
        return "à définir"
    return f"{_fmt(float(d['largeur']))} × {_fmt(float(d['hauteur']))} m, profondeur {_fmt(float(d['profondeur']))} m"


def markdown(lot: dict, objet: dict, style: style_yaml.Style, code_style: str) -> str:
    cat = objet.get("categorie") or "prop_moyen"
    budget = style.budgets_tris.get(cat)
    materiaux = [m for m in objet.get("materiaux") or [] if m in style.materiaux] or list(style.materiaux)[:2]
    pivot = style.pivot_pour(objet.get("famille"))
    parametres = objet.get("parametres") or ["hauteur", "largeur", "usure"]
    lignes = [
        f"# Générateur à écrire : {objet['nom'].lower()}",
        "",
        f"type        : {nom_module(objet['type_objet'])}",
        f"taille      : {cat}",
        f"dimensions  : {texte_dimensions(objet.get('dimensions'))}",
        f"budget      : {f'{budget:,}'.replace(',', ' ') if budget else '?'} tris ({style.libelle_categorie(cat).lower()}, style {code_style})",
        f"matériaux   : {', '.join(materiaux)} (palette du style)",
        f"pivot       : {'poignée' if pivot == 'poignee' else 'au sol, centré'}",
        f"symétrie    : {objet.get('symetrique') or 'aucune'}",
        "référence   : aucune image, s'appuyer sur l'intention",
        "",
        f"Intention : {objet.get('description') or 'voir le brief du lot'}",
        "",
        f"Paramètres attendus : {', '.join(parametres)}.",
        f"Demandé par : lot {lot['nom'] or lot['id']}.",
        "",
        "Contrat : generators/CONTRAT.md (MANIFESTE + build(params, style, seed) ; 1 unité = 1 m, haut +Z, face -Y ;",
        "couleurs, matériaux et budgets lus dans le style, jamais en dur).",
    ]
    return "\n".join(lignes) + "\n"


def texte_a_coller(type_objet: str) -> str:
    nom = nom_module(type_objet)
    return (f"Lis generators/demandes/{nom}.md et écris generators/{nom}.py en suivant generators/CONTRAT.md. "
            "Lance les tests de finition avant de rendre la main.")


def _ligne(conn: sqlite3.Connection, type_objet: str) -> dict | None:
    return db.une(conn, "SELECT * FROM demandes_generateurs WHERE type_objet = ?", (generateurs_registre.normaliser_type(type_objet),))


def etat(conn: sqlite3.Connection, lot_id: int, objet_id: int) -> dict:
    """Ce que la fenêtre affiche : chemin, Markdown, texte à coller, état et script attendu."""
    lot = lots_svc._ligne(conn, lot_id)
    objet = next((o for o in lots_svc.objets_du_lot(conn, lot_id) if o["id"] == objet_id), None)
    if objet is None:
        raise lots_svc.LotIntrouvable(f"objet {objet_id} introuvable dans le lot {lot_id}")
    style_row = db.une(conn, "SELECT code FROM styles WHERE id = ?", (lot["style_id"],))
    if style_row is None:
        raise lots_svc.BriefIncomplet("le lot n'a pas de style")
    style = styles_svc.charger_style(style_row["code"])
    ligne = _ligne(conn, objet["type_objet"])
    nom = nom_module(objet["type_objet"])
    e = ligne["etat"] if ligne else "a_ecrire"
    if e != "script_detecte" and generateurs_registre.trouver_pour_type(objet["type_objet"]):
        e = "script_detecte"
    return {
        "lot_id": lot_id, "objet_id": objet_id, "objet": objet["nom"], "type_objet": objet["type_objet"],
        "chemin_md": chemin_relatif(objet["type_objet"]), "script_attendu": f"generators/{nom}.py",
        "markdown": markdown(lot, objet, style, style_row["code"]), "texte_a_coller": texte_a_coller(objet["type_objet"]),
        "etat": e, "libelle_etat": LIBELLES_ETATS[e],
        "ecrite_le": ligne["ecrite_le"] if ligne else None, "script_detecte_le": ligne["script_detecte_le"] if ligne else None,
        "tests": {"disponibles": False, "raison": "Les tests du script (finition, Blender) arrivent à l'étape 5 du plan"},
        "voie_objet": objet["voie"],
    }


def ecrire(conn: sqlite3.Connection, lot_id: int, objet_id: int) -> dict:
    """Écrit (ou réécrit à l'identique) generators/demandes/<type>.md et la ligne en base ; idempotent."""
    info = etat(conn, lot_id, objet_id)
    chemin = _chemin_absolu(info["type_objet"])
    chemin.parent.mkdir(parents=True, exist_ok=True)
    if not chemin.exists() or chemin.read_text(encoding="utf-8") != info["markdown"]:
        chemin.write_text(info["markdown"], encoding="utf-8")
    maintenant = db.maintenant()
    ligne = _ligne(conn, info["type_objet"])
    nouvel_etat = "script_detecte" if info["etat"] == "script_detecte" else "ecrite"
    with db.transaction(conn):
        if ligne is None:
            db.inserer(conn, "demandes_generateurs", {
                "type_objet": info["type_objet"], "lot_id": lot_id, "objet_id": objet_id, "chemin_md": info["chemin_md"],
                "ecrite_le": maintenant, "etat": nouvel_etat})
        else:
            conn.execute("UPDATE demandes_generateurs SET lot_id = ?, objet_id = ?, chemin_md = ?, ecrite_le = COALESCE(ecrite_le, ?), "
                         "etat = CASE WHEN etat = 'script_detecte' THEN etat ELSE ? END WHERE id = ?",
                         (lot_id, objet_id, info["chemin_md"], maintenant, nouvel_etat, ligne["id"]))
        if ligne is None or ligne["ecrite_le"] is None:
            evenements.ecrire(conn, "demande_ecrite", f"Demande pour Claude Code écrite : {info['objet']}",
                              info["chemin_md"], niveau="info", lien=f"/lots/{lot_id}/brief", lot_id=lot_id, objet_id=objet_id)
    return etat(conn, lot_id, objet_id)


def lister(conn: sqlite3.Connection) -> list[dict]:
    rows = db.toutes(conn, "SELECT * FROM demandes_generateurs ORDER BY ecrite_le DESC, id DESC")
    for r in rows:
        r["libelle_etat"] = LIBELLES_ETATS.get(r["etat"], r["etat"])
    return rows


def scanner(conn: sqlite3.Connection) -> list[str]:
    """Le worker, toutes les 30 s : un generators/<type>.py valide apparu ? → script détecté + re-routage des lots au Brief."""
    generateurs, _ = generateurs_registre.manifestes()
    if not generateurs:
        return []
    detectes = []
    for d in db.toutes(conn, "SELECT * FROM demandes_generateurs WHERE etat != 'script_detecte'"):
        g = generateurs_registre.trouver_pour_type(d["type_objet"], generateurs)
        if not g:
            continue
        conn.execute("UPDATE demandes_generateurs SET etat = 'script_detecte', script_detecte_le = ?, generateur = ? WHERE id = ?",
                     (db.maintenant(), g, d["id"]))
        evenements.ecrire(conn, "script_detecte", f"Script détecté : generators/{g}.py",
                          f"Les objets « {d['type_objet']} » à créer passent en voie code.", niveau="succes",
                          lien=f"/lots/{d['lot_id']}/brief" if d["lot_id"] else "/generateurs", lot_id=d["lot_id"], objet_id=d["objet_id"])
        detectes.append(g)
    conn.commit()
    if detectes:
        from api.services import brief
        for lot in db.toutes(conn, "SELECT DISTINCT lot_id FROM objets WHERE etape = 'brief' AND voie IN ('a_creer', 'mixte') AND voie_forcee = 0"):
            brief.rerouter_lot(conn, lot["lot_id"], generateurs)
    return detectes
