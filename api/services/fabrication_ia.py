"""Fabrication par IA (étape 7) : l'image choisie aux Références devient un objet 3D, puis la chaîne commune.

Deux tâches par essai, chacune dans sa file :
1. `generer_ia` (file Meshy) : l'image part à Meshy (image vers 3D, remaillée au budget du style, texturée), on attend
   l'objet, on télécharge le GLB dans le dossier de l'essai. Rien n'est payé deux fois : l'id Meshy est noté dans la
   tâche ; une reprise relit la tâche Meshy au lieu d'en relancer une. Une génération que Meshy rate est remboursée par
   Meshy et redemandée par la relance de la file.
2. `finir_ia` (file Blender) : import du GLB, puis la même chaîne que la voie code (fabrication.executer) : finition
   (échelle, débris, fissures, textures à la taille du style, LOD, collision, export), contrôles, rendus, revue.

Un contrôle bloquant en échec relance un nouvel essai, 3 fois au plus (Réglages : relances automatiques).
"""
from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path
from typing import Any

from api import config as cfgmod
from api import db
from api.adapters.meshy.base import RefusMeshy
from api.services import couts, evenements, fabrication, taches
from api.services import lots as lots_svc
from api.services import references as references_svc
from api.services import styles as styles_svc
from api.services.taches import TacheDefinitive

TYPE_GENERATION = "generer_ia"
TYPE_FINITION = "finir_ia"
ETAPES_RELANCABLES = ("generation", "finition", "tests", "rendus")


def options_meshy(style, categorie: str) -> dict[str, Any]:
    """Ce qu'on demande à Meshy : objet texturé (PBR, 2K, le moins cher qui soit texturé), remaillé en triangles au
    budget du style pour la catégorie (la finition n'a presque rien à réduire)."""
    return {"ai_model": "latest", "should_texture": True, "enable_pbr": True, "texture_resolution": "2k",
            "should_remesh": True, "topology": "triangle", "target_polycount": int(style.budget(categorie))}


def _reference(conn: sqlite3.Connection, o: dict) -> dict | None:
    if o.get("reference_id") is None:
        return None
    p = db.une(conn, "SELECT * FROM propositions WHERE id = ? AND objet_id = ?", (o["reference_id"], o["id"]))
    if p is None or p["genre"] not in ("image", "perso"):
        return None
    return {"proposition_id": p["id"], "genre": p["genre"], "fichier": p["fichier"], "simule": bool(p["simule"])}


def _tache_active(conn: sqlite3.Connection, objet_id: int) -> bool:
    return db.une(conn, "SELECT 1 FROM taches WHERE objet_id = ? AND type IN (?, ?) AND etat IN ('en_attente', 'en_cours')",
                  (objet_id, TYPE_GENERATION, TYPE_FINITION)) is not None


def motif_refus(conn: sqlite3.Connection, o: dict) -> str | None:
    """Pourquoi cet objet IA ne peut pas être fabriqué maintenant, ou None s'il le peut."""
    if o["voie"] != "ia":
        return "pas un objet fait par IA"
    if o["etape"] == "brief":
        return "valide d'abord le brief"
    if o["etape"] not in ("references", *ETAPES_RELANCABLES):
        return "déjà fabriqué : il attend la revue"
    if _tache_active(conn, o["id"]):
        return "déjà en cours de fabrication"
    if _reference(conn, o) is None:
        return "choisis d'abord sa référence (écran Références)"
    return None


def lancer(conn: sqlite3.Connection, cfg: dict, lot_id: int, objet_id: int, relance_de: int | None = None) -> int:
    """Un essai et sa tâche Meshy pour un objet IA ; renvoie l'id de la tâche."""
    lot = lots_svc._ligne(conn, lot_id)
    o = next((x for x in lots_svc.objets_du_lot(conn, lot_id) if x["id"] == objet_id), None)
    if o is None:
        raise lots_svc.LotIntrouvable(f"objet {objet_id} introuvable dans le lot {lot_id}")
    motif = motif_refus(conn, o)
    if motif:
        raise fabrication.FabricationImpossible(motif)
    style = styles_svc.charger_style(db.une(conn, "SELECT code FROM styles WHERE id = ?", (lot["style_id"],))["code"])
    numero = 1 + int(db.une(conn, "SELECT COALESCE(MAX(numero), 0) AS n FROM essais WHERE objet_id = ?", (objet_id,))["n"])
    source = {"reference": _reference(conn, o), "relance_de": relance_de}
    with db.transaction(conn):
        essai_id = db.inserer(conn, "essais", {
            "objet_id": objet_id, "numero": numero, "generateur": "meshy",
            "params_json": json.dumps(options_meshy(style, o["categorie"] or "prop_moyen"), ensure_ascii=False),
            "source_json": json.dumps(source, ensure_ascii=False), "etat": "en_attente",
            "dossier": f"{lot_id}/{objet_id}/essai-{numero}"})
        conn.execute("UPDATE objets SET etape = 'generation' WHERE id = ?", (objet_id,))
        conn.execute("UPDATE pieces SET etape = 'generation' WHERE objet_id = ?", (objet_id,))
    tid = taches.creer_tache(conn, TYPE_GENERATION, "meshy", {"essai_id": essai_id}, lot_id=lot_id, objet_id=objet_id,
                             essai_id=essai_id, cfg=cfg)
    lots_svc.synchroniser_etat(conn, lot_id)
    conn.commit()
    return tid


def relancer_auto(conn: sqlite3.Connection, cfg: dict, essai: dict, motif: str) -> int | None:
    """Un nouvel essai après un contrôle en échec, s'il reste des relances ; None sinon."""
    objet = db.une(conn, "SELECT * FROM objets WHERE id = ?", (essai["objet_id"],))
    n = int(db.une(conn, "SELECT COUNT(*) AS n FROM essais WHERE objet_id = ?", (objet["id"],))["n"])
    if n >= 1 + cfgmod.relances_max(cfg):
        return None
    evenements.ecrire(conn, "relance_auto", f"Relance automatique : {objet['nom']}", motif[:500], niveau="alerte",
                      lien=f"/lots/{objet['lot_id']}/generation", lot_id=objet["lot_id"], objet_id=objet["id"])
    return lancer(conn, cfg, objet["lot_id"], objet["id"], relance_de=essai["id"])


def _erreur_meshy(etat: dict) -> str:
    e = etat.get("task_error")
    if isinstance(e, dict):
        return str(e.get("message") or e)
    return str(e or etat.get("status"))


def executer_generation(conn: sqlite3.Connection, meshy, cfg: dict, params: dict, tache_id: int | None = None,
                        progression=None, arret=None, attente_s: float = 3.0, max_lectures: int = 1200) -> dict:
    """Corps de la tâche `generer_ia` (file Meshy) : image → objet 3D, GLB téléchargé, finition mise en file."""
    essai = db.une(conn, "SELECT * FROM essais WHERE id = ?", (int(params["essai_id"]),))
    if essai is None:
        raise TacheDefinitive(f"essai {params['essai_id']} introuvable")
    objet = db.une(conn, "SELECT * FROM objets WHERE id = ?", (essai["objet_id"],))
    source = json.loads(essai["source_json"] or "{}")
    reference = source.get("reference") or {}
    image = references_svc.dossier_references(objet["lot_id"], objet["id"]) / str(reference.get("fichier") or "")
    if not reference.get("fichier") or not image.is_file():
        raise fabrication._echec(conn, essai, "image de référence introuvable : choisis-en une autre aux Références")
    simule = getattr(meshy, "mode", "") == "simule"
    service = "Meshy simulé" if simule else "Meshy"
    reprise = taches.lire_reprise(conn, tache_id) if tache_id is not None else {}

    def noter(**valeurs) -> None:
        reprise.update(valeurs)
        if tache_id is not None:
            taches.noter_reprise(conn, tache_id, reprise)

    def avancer(pct: float, texte: str) -> None:
        if progression:
            progression(pct, f"{service} : {texte}")

    conn.execute("UPDATE essais SET etat = 'generation', debute_le = COALESCE(debute_le, ?) WHERE id = ?",
                 (db.maintenant(), essai["id"]))
    conn.commit()
    meshy_id = reprise.get("meshy_id")
    if not meshy_id:
        try:
            meshy_id = meshy.image_vers_3d(image, json.loads(essai["params_json"] or "{}"))
        except RefusMeshy as e:
            raise fabrication._echec(conn, essai, f"{service} refuse : {e}") from e
        noter(meshy_id=meshy_id)
    avancer(5, "objet 3D demandé")
    etat: dict = {}
    for _ in range(max_lectures):
        if arret is not None and arret():
            raise InterruptedError(f"arrêt du worker pendant l'attente de {service}")
        etat = meshy.etat_tache(meshy_id)
        statut = etat.get("status")
        if statut == "SUCCEEDED":
            break
        if statut in ("FAILED", "CANCELED"):
            noter(meshy_id=None)  # Meshy rembourse un échec ; la relance de la file en redemande un
            raise RuntimeError(f"{service} n'a pas pu faire l'objet : {_erreur_meshy(etat)}")
        avancer(5 + 0.85 * float(etat.get("progress") or 0), f"objet 3D · {int(etat.get('progress') or 0)} %")
        time.sleep(attente_s)
    else:
        raise RuntimeError(f"{service} ne finit pas (délai dépassé)")

    dossier = fabrication.dossier_essai(essai) / "source"
    glb = Path(meshy.telecharger(meshy_id, dossier))
    credits = int(etat.get("consumed_credits") or meshy.credits_3d)
    with db.transaction(conn):
        if tache_id is not None:
            conn.execute("DELETE FROM couts WHERE tache_id = ? AND service = 'meshy'", (tache_id,))
        couts.enregistrer(conn, "meshy", "generation_3d", simule=simule, credits=credits, lot_id=objet["lot_id"],
                          tache_id=tache_id, detail={"objet_id": objet["id"], "essai_id": essai["id"], "meshy": meshy_id})
        source.update({"glb": str(glb.relative_to(fabrication.dossier_essai(essai))), "meshy_id": meshy_id,
                       "simule": simule})
        conn.execute("UPDATE essais SET source_json = ?, cout_credits = ? WHERE id = ?",
                     (json.dumps(source, ensure_ascii=False), credits, essai["id"]))
    avancer(95, "objet 3D reçu")
    suite = reprise.get("finition_tache")
    if not suite:
        suite = taches.creer_tache(conn, TYPE_FINITION, "blender", {"essai_id": essai["id"]}, lot_id=objet["lot_id"],
                                   objet_id=objet["id"], essai_id=essai["id"], cfg=cfg)
        noter(finition_tache=suite)
    avancer(100, "objet 3D reçu, finition en file")
    return {"essai": essai["id"], "meshy": meshy_id, "credits": credits, "simule": simule, "finition": suite}
