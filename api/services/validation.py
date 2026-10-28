"""Validation (étape 4 d'un projet) : ce que l'utilisateur voit d'un objet fabriqué, le verdict calculé sur ses fichiers,
et ses décisions.

Quatre décisions, toutes réelles :
- garder : l'objet entre dans la collection du projet ; s'annule ;
- jeter : l'objet est écarté, avec un motif ; s'annule ;
- refaire : l'objet revient au Look, pour choisir une autre image ou une autre version (gratuit) ;
- corriger : l'app redessine 4 nouveaux looks en tenant compte des remarques, puis l'objet revient au Look
  (objets faits par IA seulement : un objet fait par script se règle par ses variantes).

Le verdict vient des contrôles du cahier des charges (rapport.json) et de mesures faites sur le fichier 3D lui-même.
Rien n'est inventé : sans avis de l'IA, il n'y a pas d'avis.
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from api import db
from api.adapters.meshy.base import CREDITS_IMAGE
from api.services import evenements, fabrication, references
from api.services import lots as lots_svc
from api.services.routage import VOIES_SANS_FABRICATION
from pipeline import validate

DECISIONS = ("garder", "jeter", "refaire", "corriger", "annuler")
MOTIFS_JET = ("proportions", "details_flous", "ne_ressemble_pas", "hors_style", "inutile")
PRECISION_M = 0.003  # un objet est « posé au sol » à 3 mm près
RAISONS_REUSSIES = 4  # réussites montrées dans le verdict

_BIEN = {
    "Maillage fermé": "Forme fermée, sans trou",
    "Pièces flottantes": "Aucune pièce détachée",
    "Normales": "Surfaces bien orientées",
    "Dimensions": "Taille cohérente avec le style",
    "Polycount": "Assez léger pour un jeu",
    "Symétrie": "Symétrie respectée",
    "UV": "Texture bien dépliée",
    "Densité de texels": "Texture d'une netteté régulière",
}
_PAS_BIEN = {
    "Maillage fermé": "La forme a des trous",
    "Pièces flottantes": "Des pièces flottent à côté de l'objet",
    "Normales": "Des surfaces sont à l'envers",
    "Dimensions": "La taille sort de la fourchette du style",
    "Polycount": "Trop de triangles pour un jeu",
    "Symétrie": "La symétrie n'est pas respectée",
    "UV": "La texture est mal dépliée",
    "Densité de texels": "La netteté de la texture varie trop",
}


class DecisionImpossible(RuntimeError):
    """La décision ne s'applique pas à l'état de l'objet (409)."""


# --- fichiers ----------------------------------------------------------------------------------------------

def _dossier_asset(essai: dict) -> Path:
    return fabrication.dossier_essai(essai) / "asset"


def _glb(essai: dict) -> Path | None:
    return next(iter(sorted(_dossier_asset(essai).glob("*.glb"))), None)


def modele_public(essai_id: int) -> Path:
    """Le fichier .glb d'un essai, servi à l'afficheur 3D."""
    conn = db.connexion()
    try:
        essai = db.une(conn, "SELECT * FROM essais WHERE id = ?", (essai_id,))
    finally:
        conn.close()
    glb = _glb(essai) if essai else None
    if glb is None:
        raise FileNotFoundError(f"modèle de l'essai {essai_id}")
    return glb


def _json(chemin: Path) -> dict:
    try:
        return json.loads(chemin.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


# --- mesures et verdict ------------------------------------------------------------------------------------

def mesurer(glb: Path) -> dict[str, Any] | None:
    """Mesures sur le LOD0 du fichier : taille, pied au sol, écart du point d'ancrage. None si le fichier ne se lit pas."""
    try:
        mesh = validate.maillage_par_suffixe(validate.charger_maillages(glb), "_LOD0")
    except Exception:  # noqa: BLE001 - un fichier illisible ne doit pas casser l'écran : le verdict le dit
        return None
    if mesh is None or len(mesh.vertices) == 0:
        return None
    mini, maxi = mesh.bounds
    taille = maxi - mini
    centre = (maxi + mini) / 2
    # Repère de l'app : Z en haut, face avant vers -Y.
    return {"largeur": float(taille[0]), "profondeur": float(taille[1]), "hauteur": float(taille[2]),
            "pied": float(mini[2]), "decalage": float((centre[0] ** 2 + centre[1] ** 2) ** 0.5)}


def _cm(v: float) -> str:
    return f"{abs(v) * 100:.1f}".replace(".", ",") + " cm"


def _metre(v: float) -> str:
    return f"{v:.2f}".replace(".", ",")


def verdict(controles: list[dict], mesure: dict | None) -> dict:
    """« Prêt à garder » ou « À regarder avant de garder », avec ses raisons : les défauts d'abord, puis quelques réussites
    (la taille et la pose au sol avant les contrôles)."""
    pas_bien: list[dict] = []
    reussites: list[dict] = []
    mesures_ok: list[dict] = []
    for c in controles:
        nom = c["nom"]
        if nom not in _BIEN or c.get("etat") in ("non exécuté", "non demandée"):
            continue
        if c["ok"]:
            reussites.append({"ok": True, "texte": _BIEN[nom]})
        else:
            detail = f" ({c['detail']})" if c.get("detail") else ""
            pas_bien.append({"ok": False, "texte": _PAS_BIEN[nom] + detail})
    if mesure is None:
        pas_bien.append({"ok": False, "texte": "Le fichier 3D n'a pas pu être mesuré"})
    else:
        mesures_ok.append({"ok": True, "texte": f"Taille : {_metre(mesure['largeur'])} × {_metre(mesure['profondeur'])} × {_metre(mesure['hauteur'])} m"})
        pied = mesure["pied"]
        if abs(pied) <= PRECISION_M:
            mesures_ok.append({"ok": True, "texte": "Posé au sol"})
        else:
            pas_bien.append({"ok": False, "texte": f"Flotte à {_cm(pied)} au-dessus du sol" if pied > 0 else f"Enfoncé de {_cm(pied)} sous le sol"})
        tolerance = max(0.004, max(mesure["largeur"], mesure["profondeur"]) * 0.03)
        if mesure["decalage"] <= tolerance:
            mesures_ok.append({"ok": True, "texte": "Bien centré sur son point d'ancrage"})
        else:
            pas_bien.append({"ok": False, "texte": f"Point d'ancrage décalé de {_cm(mesure['decalage'])}"})
    bien = mesures_ok + reussites
    return {"etat": "attention" if pas_bien else "ok", "raisons": pas_bien + bien[:RAISONS_REUSSIES],
            "autres_ok": max(0, len(bien) - RAISONS_REUSSIES)}


# --- lecture -----------------------------------------------------------------------------------------------

def _etat(o: dict) -> str:
    return {"revue": "a_valider", "garde": "garde", "rejete": "jete"}.get(
        o["etape"], "en_fabrication" if o["etape"] in fabrication.ETAPES else "look")


def _source(o: dict, essai: dict) -> str:
    if o["voie"] == "ia":
        return f"Faite par Meshy d'après ton look · essai {essai['numero']}"
    return f"Faite par script ({o['generateur'] or 'sans nom'}) · essai {essai['numero']}"


def _objet_vue(conn: sqlite3.Connection, o: dict) -> dict:
    etat = _etat(o)
    vue: dict[str, Any] = {"id": o["id"], "nom": o["nom"], "voie": o["voie"], "etat": etat, "peut_annuler": etat in ("garde", "jete"),
                           "peut_corriger": o["voie"] == "ia",
                           "credits_correction": CREDITS_IMAGE * references.PAR_SERIE if o["voie"] == "ia" else 0, "modele": None, "reference": None, "vues": [], "planche": None,
                           "verdict": None, "controles": [], "faits": None, "source": None, "avis_ia": None, "essai_id": None}
    if o.get("reference_id"):
        vue["reference"] = f"/api/fichiers/references/{o['reference_id']}"
    if etat not in ("a_valider", "garde", "jete"):
        return vue
    essai = db.une(conn, "SELECT * FROM essais WHERE objet_id = ? AND etat = 'pret' ORDER BY numero DESC LIMIT 1", (o["id"],))
    if essai is None:
        return vue
    asset = _dossier_asset(essai)
    glb = _glb(essai)
    rapport = _json(asset / "rapport.json")
    meta = _json(asset / "meta.json")
    controles = [c for c in rapport.get("controles", []) if isinstance(c, dict)]
    rendus = asset / "rendus"
    vue.update({
        "essai_id": essai["id"], "source": _source(o, essai), "avis_ia": essai.get("avis_ia") or None,
        "modele": f"/api/fichiers/essais/{essai['id']}/modele.glb" if glb else None,
        "vues": [{"nom": n, "url": f"/api/fichiers/essais/{essai['id']}/{n}.png"} for n in validate.VUES if (rendus / f"{n}.png").is_file()],
        "planche": f"/api/fichiers/essais/{essai['id']}/planche.png" if (rendus / "planche.png").is_file() else None,
        "controles": [{"nom": c["nom"], "ok": bool(c.get("ok")), "etat": c.get("etat", ""), "detail": c.get("detail", ""),
                       "bloquant": bool(c.get("bloquant"))} for c in controles],
        "verdict": verdict(controles, mesurer(glb) if glb else None),
        "faits": {"dimensions_m": meta.get("dimensions_m"), "tris": {"lod0": meta.get("tris_lod0"), "lod1": meta.get("tris_lod1"),
                                                                       "lod2": meta.get("tris_lod2")},
                  "credits": int(essai["cout_credits"] or 0), "nombre_essais": int(essai["numero"])},
    })
    return vue


def _fabriques(conn: sqlite3.Connection, lot_id: int) -> list[dict]:
    return [o for o in lots_svc.objets_du_lot(conn, lot_id) if not o["retire"] and o["voie"] not in VOIES_SANS_FABRICATION]


def vue(conn: sqlite3.Connection, lot_id: int) -> dict:
    lots_svc._ligne(conn, lot_id)
    objets = [_objet_vue(conn, o) for o in _fabriques(conn, lot_id)]
    compte = {e: sum(1 for o in objets if o["etat"] == e) for e in ("a_valider", "garde", "jete", "en_fabrication", "look")}
    decides = compte["garde"] + compte["jete"]
    return {"lot_id": lot_id, "objets": objets,
            "resume": {"total": len(objets), "a_valider": compte["a_valider"], "gardes": compte["garde"], "jetes": compte["jete"],
                       "pas_prets": compte["en_fabrication"] + compte["look"]},
            "termine": bool(objets) and decides == len(objets),
            "collection": _nom_collection(lots_svc._ligne(conn, lot_id))}


# --- décisions ---------------------------------------------------------------------------------------------

def _nom_collection(lot: dict) -> str:
    return (lot["nom"] or "").strip() or f"Projet {lot['id']}"


def _objet(conn: sqlite3.Connection, lot_id: int, objet_id: int) -> dict:
    for o in lots_svc.objets_du_lot(conn, lot_id):
        if o["id"] == objet_id:
            return o
    raise lots_svc.LotIntrouvable(f"objet {objet_id} introuvable dans le projet {lot_id}")


def _asset(conn: sqlite3.Connection, objet_id: int) -> dict | None:
    return db.une(conn, "SELECT * FROM assets WHERE objet_id = ?", (objet_id,))


def _collection(conn: sqlite3.Connection, lot: dict) -> int:
    nom = _nom_collection(lot)
    existante = db.une(conn, "SELECT id FROM collections WHERE nom = ?", (nom,))
    return int(existante["id"]) if existante else db.inserer(conn, "collections", {"nom": nom})


def _exiger(o: dict, *etapes: str, action: str) -> None:
    if o["etape"] not in etapes:
        raise DecisionImpossible(f"{action} : cet objet n'est pas à valider")


def decider(conn: sqlite3.Connection, cfg: dict, lot_id: int, objet_id: int, decision: str, *, motif: str | None = None,
            notes: list[str] | None = None, texte: str | None = None) -> dict:
    """Applique une décision et renvoie l'objet relu. DecisionImpossible (409) si elle ne convient pas à son état."""
    if decision not in DECISIONS:
        raise ValueError(f"décision inconnue : {decision} (attendu : {', '.join(DECISIONS)})")
    lot = lots_svc._ligne(conn, lot_id)
    o = _objet(conn, lot_id, objet_id)
    maintenant = db.maintenant()

    if decision == "garder":
        _exiger(o, "revue", action="Garder")
        asset = _asset(conn, objet_id)
        with db.transaction(conn):
            conn.execute("UPDATE objets SET etape = 'garde' WHERE id = ?", (objet_id,))
            if asset:
                conn.execute("UPDATE assets SET statut = 'garde', maj_le = ? WHERE id = ?", (maintenant, asset["id"]))
                conn.execute("INSERT OR IGNORE INTO collections_assets(collection_id, asset_id) VALUES (?, ?)",
                             (_collection(conn, lot), asset["id"]))
            evenements.ecrire(conn, "objet_garde", f"{o['nom']} gardé", f"dans {_nom_collection(lot)}", niveau="info",
                              lot_id=lot_id, objet_id=objet_id)

    elif decision == "jeter":
        _exiger(o, "revue", action="Jeter")
        if motif is not None and motif not in MOTIFS_JET:
            raise ValueError(f"motif inconnu : {motif} (attendu : {', '.join(MOTIFS_JET)})")
        asset = _asset(conn, objet_id)
        with db.transaction(conn):
            conn.execute("UPDATE objets SET etape = 'rejete' WHERE id = ?", (objet_id,))
            if asset:
                conn.execute("UPDATE assets SET statut = 'archive', maj_le = ? WHERE id = ?", (maintenant, asset["id"]))
            evenements.ecrire(conn, "objet_jete", f"{o['nom']} jeté", f"motif : {motif}" if motif else "", niveau="info",
                              lot_id=lot_id, objet_id=objet_id)

    elif decision == "annuler":
        _exiger(o, "garde", "rejete", action="Annuler")
        asset = _asset(conn, objet_id)
        with db.transaction(conn):
            conn.execute("UPDATE objets SET etape = 'revue' WHERE id = ?", (objet_id,))
            if asset:
                conn.execute("UPDATE assets SET statut = 'revue', maj_le = ? WHERE id = ?", (maintenant, asset["id"]))
                conn.execute("DELETE FROM collections_assets WHERE asset_id = ? AND collection_id IN "
                             "(SELECT id FROM collections WHERE nom = ?)", (asset["id"], _nom_collection(lot)))

    else:  # refaire, corriger : l'objet revient au Look
        _exiger(o, "revue", action="Refaire" if decision == "refaire" else "Corriger")
        if decision == "corriger":
            if o["voie"] != "ia":
                raise DecisionImpossible("Corriger : un objet fait par script se règle par ses variantes, utilise « Refaire »")
            remarques = " ".join(" ".join([*(f"{i}. {n.strip()}" for i, n in enumerate(notes or [], start=1) if n and n.strip()),
                                           (texte or "").strip()]).split())
            if not remarques:
                raise ValueError("Corriger : dis ce qui ne va pas (pointe un défaut ou écris une phrase)")
            _, style = references._style_du_lot(conn, lot)
            consigne = f"{references.consigne_par_defaut(style, o)} Corrections demandées : {remarques}"
            if len(consigne) > references.MAX_CONSIGNE:
                raise ValueError(f"Corriger : tes remarques sont trop longues (reste sous {references.MAX_CONSIGNE - len(references.consigne_par_defaut(style, o)) - 30} caractères)")
            conn.execute("UPDATE objets SET consigne = ? WHERE id = ?", (consigne, objet_id))
        with db.transaction(conn):
            conn.execute("UPDATE objets SET etape = 'references' WHERE id = ?", (objet_id,))
            conn.execute("UPDATE pieces SET etape = 'references' WHERE objet_id = ?", (objet_id,))
            evenements.ecrire(conn, "objet_refait", f"{o['nom']} : retour au Look", "avec tes remarques" if decision == "corriger" else "",
                              niveau="info", lot_id=lot_id, objet_id=objet_id)
        if decision == "corriger":
            references.preparer(conn, cfg, lot_id, objet_id)

    lots_svc.synchroniser_etat(conn, lot_id)
    conn.commit()
    return _objet_vue(conn, _objet(conn, lot_id, objet_id))
