"""Écran Génération d'un lot (Generation.dc.html) : ce qui se fabrique, ce qui tourne, ce que ça coûte.

Tout vient de la base : étapes des objets, tâches du lot, coûts, registre des générateurs, battement du worker.
Avant les étapes 5 (voie code) et 7 (voie IA) du plan, aucun objet n'avance au-delà des Références : l'écran le dit.
"""
from __future__ import annotations

import sqlite3

from api import config as cfgmod
from api import db
from api.adapters import get_meshy
from api.services import couts, generateurs_registre, taches, workers
from api.services import lots as lots_svc
from api.services.routage import VOIES_SANS_FABRICATION

ETAPES = ("generation", "finition", "tests", "rendus")
LIBELLES = {"generation": "Génération", "finition": "Finition", "tests": "Tests", "rendus": "Rendus"}
FINIES = ("revue", "garde", "rejete", "archive")
TYPES_TACHES = {"proposer_liste": "Proposition de la liste par Claude", "planche_style": "Planche de style (images Meshy)",
                "echec": "Tâche d'essai (échoue exprès)", "attendre": "Tâche d'essai (attend)"}
FILES = {"gpu": "carte graphique", "meshy": "Meshy", "blender": "Blender", "api": "API Claude"}
FABRICATION = ("Génération, finition, tests et rendus arrivent avec la fabrication : étape 5 du plan pour la voie code, "
               "étape 7 pour la voie IA, le mixte et l'import CC0")


def _puces(o: dict) -> list[dict]:
    if o["etape"] in FINIES:
        rang = len(ETAPES)
    elif o["etape"] in ETAPES:
        rang = ETAPES.index(o["etape"])
    else:
        rang = -1  # au brief ou aux références : rien n'a commencé
    return [{"cle": cle, "libelle": "Import" if cle == "generation" and o["voie"] == "cc0" else LIBELLES[cle],
             "etat": "fait" if i < rang else "en_cours" if i == rang else "a_faire"} for i, cle in enumerate(ETAPES)]


def _fournisseur(o: dict, meshy_simule: bool) -> str:
    meshy = "Meshy (simulé)" if meshy_simule else "Meshy"
    if o["voie"] == "code":
        return f"Code · generators/{o['generateur']}.py · file Blender" if o["generateur"] else "Code · file Blender"
    if o["voie"] == "ia":
        return f"IA · {meshy} · file Meshy"
    if o["voie"] == "mixte":
        return f"Mixte · {len(o['pieces'])} pièces · code et {meshy}"
    if o["voie"] == "cc0":
        return "Import CC0 · catalogue local · file Blender"
    return "Voie à choisir"


def _statut(o: dict) -> tuple[str, str, int]:
    """(texte, ton, pourcentage) d'un objet, d'après son étape."""
    if o["etape"] in FINIES:
        return "Prêt pour la revue", "good", 100
    if o["etape"] in ETAPES:
        i = ETAPES.index(o["etape"])
        return f"{LIBELLES[o['etape']]} en cours", "run", round(100 * i / len(ETAPES))
    if o["etape"] == "references":
        return "Attend sa référence (écran Références, étape 6 du plan)", "idle", 0
    return "Au brief", "idle", 0


def tache_vue(t: dict) -> dict:
    progression = (t["resultat"] or {}).get("progression") if isinstance(t["resultat"], dict) else None
    return {
        "id": t["id"], "type": t["type"], "libelle": TYPES_TACHES.get(t["type"], t["type"]),
        "file": t["file"], "libelle_file": FILES.get(t["file"], t["file"]), "etat": t["etat"],
        "tentatives": t["tentatives"], "max_tentatives": t["max_tentatives"], "erreur": t["erreur"],
        "progression": progression, "cree_le": t["cree_le"], "debute_le": t["debute_le"], "fini_le": t["fini_le"],
        "reprise_le": t["reprise_le"], "lot_id": t["lot_id"], "objet_id": t["objet_id"],
        "peut_relancer": t["etat"] in ("echouee", "annulee"), "peut_annuler": t["etat"] in ("en_attente", "en_cours"),
    }


def generateurs_branches(cfg: dict) -> list[dict]:
    manifestes, _ = generateurs_registre.manifestes()
    meshy = get_meshy(cfg)
    n = len(manifestes)
    return [
        {"nom": "Générateurs par code", "detail": f"Voie code · {n} script{'s' if n > 1 else ''} Blender",
         "etat": "Actif" if n else "Aucun script", "ton": "good" if n else "idle"},
        {"nom": "Meshy", "detail": f"Voie IA · {meshy.credits_3d} crédits par génération texturée",
         "etat": "Simulé" if meshy.mode == "simule" else "Réel", "ton": "idle" if meshy.mode == "simule" else "good"},
        {"nom": "ComfyUI", "detail": f"Voie IA · {cfgmod.service(cfg, 'comfyui').get('url', '')}",
         "etat": "Simulé" if cfgmod.mode(cfg, "comfyui") == "simule" else "Réel",
         "ton": "idle" if cfgmod.mode(cfg, "comfyui") == "simule" else "good"},
    ]


def vue(conn: sqlite3.Connection, cfg: dict, lot_id: int) -> dict:
    lot = lots_svc._ligne(conn, lot_id)
    objets = [o for o in lots_svc.objets_du_lot(conn, lot_id) if not o["retire"]]
    fabriques = [o for o in objets if o["voie"] not in VOIES_SANS_FABRICATION]
    meshy_simule = cfgmod.mode(cfg, "meshy") == "simule"
    lignes = []
    for o in fabriques:
        texte, ton, pct = _statut(o)
        lignes.append({"id": o["id"], "nom": o["nom"], "voie": o["voie"], "fournisseur": _fournisseur(o, meshy_simule),
                       "etapes": _puces(o), "statut": texte, "ton": ton, "pct": pct})
    liste = [taches._charger(r) for r in db.toutes(conn, "SELECT * FROM taches WHERE lot_id = ? ORDER BY id DESC", (lot_id,))]
    credits = couts.credits_meshy_lot(conn, lot_id)
    prets = sum(1 for o in fabriques if o["etape"] in FINIES)
    return {
        "lot_id": lot_id,
        "tuiles": {
            "prets_revue": prets, "fabriques": len(fabriques),
            "en_cours": sum(1 for o in fabriques if o["etape"] in ETAPES),
            "relances": sum(max(0, t["tentatives"] - 1) for t in liste),
            "credits_utilises": credits["credits"], "credits_simules": credits["simule"],
            "credits_prevus": int(lot["credits_prevus"] or 0),
        },
        "objets": lignes,
        "reutilises": [o["nom"] for o in objets if o["voie"] == "reutilise"],
        "taches": [tache_vue(t) for t in liste],
        "generateurs": generateurs_branches(cfg),
        "worker": workers.etat(conn),
        "fabrication": {"disponible": False, "raison": FABRICATION},
        "limites_files": {f: int(v) for f, v in cfgmod.limites_files(cfg).items()},
    }


def taches_recentes(conn: sqlite3.Connection, limite: int = 20) -> list[dict]:
    """Pour Réglages · File de tâches : les tâches actives d'abord, puis les plus récentes."""
    rows = db.toutes(conn, """SELECT * FROM taches ORDER BY CASE etat WHEN 'en_cours' THEN 0 WHEN 'en_attente' THEN 1
                              WHEN 'echouee' THEN 2 ELSE 3 END, id DESC LIMIT ?""", (limite,))
    out = []
    for r in rows:
        t = taches._charger(r)
        vue_t = tache_vue(t)
        if t["lot_id"]:
            lot = db.une(conn, "SELECT nom FROM lots WHERE id = ?", (t["lot_id"],))
            nom = lot["nom"] if lot and lot["nom"] else f"Lot n° {t['lot_id']}"
            vue_t["contexte"] = {"libelle": nom, "lien": f"/lots/{t['lot_id']}/generation"}
        elif t["type"] == "planche_style" and isinstance(t["params"], dict):
            code = t["params"].get("code", "")
            vue_t["contexte"] = {"libelle": f"Style {code}", "lien": f"/styles?style={code}"}
        else:
            vue_t["contexte"] = None
        out.append(vue_t)
    return out

