"""Écran Génération d'un lot (Generation.dc.html) : ce qui se fabrique, ce qui tourne, ce que ça coûte.

Tout vient de la base : étapes des objets, tâches du lot, coûts, registre des générateurs, battement du worker.
Les objets y arrivent depuis les Références (« Lancer la génération 3D ») : code par Blender, IA par Meshy puis
Blender. Les objets mixtes et l'import CC0 attendent la suite de l'étape 7 avec leur référence, et l'écran le dit.
"""
from __future__ import annotations

import sqlite3

from api import config as cfgmod
from api import db
from api.adapters import get_meshy
from api.services import couts, fabrication, fabrication_ia, generateurs_registre, taches, workers
from api.services import lots as lots_svc
from api.services.routage import VOIES_SANS_FABRICATION

ETAPES = ("generation", "finition", "tests", "rendus")
LIBELLES = {"generation": "Génération", "finition": "Finition", "tests": "Tests", "rendus": "Rendus"}
FINIES = ("revue", "garde", "rejete", "archive")
TYPES_TACHES = {"proposer_liste": "Proposition de la liste par Claude", "planche_style": "Planche de style (images Meshy)",
                "fabriquer_code": "Fabrication par code (Blender)",
                "references_images": "Images de référence (Meshy)", "references_variantes": "Variantes de référence (Blender)",
                "generer_ia": "Objet 3D par IA (Meshy)", "finir_ia": "Finition d'un objet IA (Blender)",
                "echec": "Tâche d'essai (échoue exprès)", "attendre": "Tâche d'essai (attend)"}
FILES = {"gpu": "carte graphique", "meshy": "Meshy", "blender": "Blender", "api": "API Claude"}
FABRICATION_IA = "Les objets mixtes et l'import CC0 se fabriqueront ici avec la suite de l'étape 7 du plan"


def _puces(o: dict, essai: dict | None = None) -> list[dict]:
    if o["etape"] in FINIES:
        rang = len(ETAPES)
    elif o["etape"] == "generation" and essai is None and o["voie"] != "code":
        rang = -1  # mixte ou import en attente de la suite de l'étape 7 : rien ne tourne encore
    elif o["etape"] in ETAPES:
        rang = ETAPES.index(o["etape"])
    else:
        rang = -1  # au brief ou aux références : rien n'a commencé
    echec = essai is not None and essai["etat"] == "echec"
    return [{"cle": cle, "libelle": "Import" if cle == "generation" and o["voie"] == "cc0" else LIBELLES[cle],
             "etat": "fait" if i < rang else ("echec" if echec else "en_cours") if i == rang else "a_faire"}
            for i, cle in enumerate(ETAPES)]


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


def _statut(o: dict, essai: dict | None = None) -> tuple[str, str, int]:
    """(texte, ton, pourcentage) d'un objet, d'après son étape et son dernier essai."""
    if essai is not None and essai["etat"] == "echec" and o["etape"] in ETAPES:
        i = ETAPES.index(o["etape"])
        return f"Échec à l'étape {LIBELLES[o['etape']]} : {essai['erreur'] or 'motif inconnu'}", "warn", round(100 * i / len(ETAPES))
    if o["etape"] in FINIES:
        return "Prêt à valider", "good", 100
    if o["etape"] == "generation" and essai is None and o["voie"] != "code":
        if o["voie"] == "cc0":
            return "En attente : l'import CC0 arrive avec la suite de l'étape 7", "idle", 0
        return "Référence choisie · en attente : l'assemblage mixte arrive avec la suite de l'étape 7", "idle", 0
    if o["etape"] in ETAPES:
        i = ETAPES.index(o["etape"])
        return f"{LIBELLES[o['etape']]} en cours", "run", round(100 * i / len(ETAPES))
    if o["etape"] == "references":
        return "Attend sa référence (écran Références)", "idle", 0
    return "Au brief", "idle", 0


def _en_attente_ia(conn: sqlite3.Connection, o: dict) -> bool:
    return o["voie"] != "code" and o["etape"] == "generation" and not db.une(conn, "SELECT 1 FROM essais WHERE objet_id = ?", (o["id"],))


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
    manifestes, _ = generateurs_registre.manifestes()
    lignes = []
    for o in fabriques:
        essai = db.une(conn, "SELECT * FROM essais WHERE objet_id = ? ORDER BY numero DESC LIMIT 1", (o["id"],))
        rendus = fabrication.dossier_essai(essai) / "asset" / "rendus" if essai else None
        texte, ton, pct = _statut(o, essai)
        if rendus is None or not (rendus / "vignette.png").is_file():
            vignette = f"/api/fichiers/references/{o['reference_id']}" if o.get("reference_id") else None
        else:
            vignette = f"/api/fichiers/essais/{essai['id']}/vignette.png"
        motif = fabrication_ia.motif_refus(conn, o) if o["voie"] == "ia" else fabrication.motif_refus(conn, o, manifestes)
        asset = db.une(conn, "SELECT id FROM assets WHERE objet_id = ?", (o["id"],))
        lignes.append({
            "id": o["id"], "nom": o["nom"], "voie": o["voie"], "fournisseur": _fournisseur(o, meshy_simule),
            "etapes": _puces(o, essai), "statut": texte, "ton": ton, "pct": pct,
            "essai": {"id": essai["id"], "numero": essai["numero"], "etat": essai["etat"], "erreur": essai["erreur"]} if essai else None,
            # Le rendu de l'objet fabriqué ; avant, la référence choisie aux Références.
            "vignette": vignette,
            "planche": f"/api/fichiers/essais/{essai['id']}/planche.png" if rendus and (rendus / "planche.png").is_file() else None,
            "asset_id": asset["id"] if asset else None,
            "peut_fabriquer": motif is None, "motif": motif,
            # Un objet en échec peut repartir d'une autre référence (variante, image), choisie aux Références.
            "peut_rechoisir": o["voie"] in ("code", "ia") and essai is not None and essai["etat"] == "echec"
            and motif is None})
    liste = [taches._charger(r) for r in db.toutes(conn, "SELECT * FROM taches WHERE lot_id = ? ORDER BY id DESC", (lot_id,))]
    credits = couts.credits_meshy_lot(conn, lot_id)
    prets = sum(1 for o in fabriques if o["etape"] in FINIES)
    return {
        "lot_id": lot_id,
        "tuiles": {
            "prets_revue": prets, "fabriques": len(fabriques),
            # Un objet mixte ou importé lancé attend la suite de l'étape 7 : rien ne tourne encore pour lui.
            "en_cours": sum(1 for o in fabriques if o["etape"] in ETAPES and not _en_attente_ia(conn, o)),
            # Relances de la file (une tâche refaite) et relances automatiques (un nouvel essai IA après un contrôle).
            "relances": sum(max(0, t["tentatives"] - 1) for t in liste) + int(db.une(
                conn, "SELECT COUNT(*) AS n FROM essais e JOIN objets o ON o.id = e.objet_id WHERE o.lot_id = ? "
                      "AND json_extract(e.source_json, '$.relance_de') IS NOT NULL", (lot_id,))["n"]),
            "credits_utilises": credits["credits"], "credits_simules": credits["simule"],
            "credits_prevus": int(lot["credits_prevus"] or 0),
        },
        "objets": lignes,
        "reutilises": [o["nom"] for o in objets if o["voie"] == "reutilise"],
        "taches": [tache_vue(t) for t in liste],
        "generateurs": generateurs_branches(cfg),
        "worker": workers.etat(conn),
        "fabrication": {"autres_voies": sum(1 for o in fabriques if o["voie"] in ("mixte", "cc0")), "raison_ia": FABRICATION_IA},
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
            ecran = "references" if t["type"] in ("references_images", "references_variantes") else "generation"
            vue_t["contexte"] = {"libelle": nom, "lien": f"/lots/{t['lot_id']}/{ecran}"}
        elif t["type"] == "planche_style" and isinstance(t["params"], dict):
            code = t["params"].get("code", "")
            vue_t["contexte"] = {"libelle": f"Style {code}", "lien": f"/styles?style={code}"}
        else:
            vue_t["contexte"] = None
        out.append(vue_t)
    return out

