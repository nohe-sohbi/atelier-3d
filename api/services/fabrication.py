"""Fabrication par code (étape 5) : générer → finir → contrôler → rendre, pour un objet en voie code.

Un essai (table essais) est une tentative de fabrication d'un objet, rangée dans lots/<lot>/<objet>/essai-<n>/.
La tâche `fabriquer_code` (file Blender) enchaîne les quatre étapes et l'étape de l'objet les suit (generation,
finition, tests, rendus, puis revue). Chaque étape faite est notée dans la tâche : après une coupure ou un arrêt du
worker, on reprend à la suivante. Un objet conforme devient un asset « en revue », avec sa version.

Un générateur code est rejouable (mêmes paramètres, même résultat) : un contrôle bloquant en échec ou une erreur du
script ne se corrige pas en relançant, la tâche échoue tout de suite avec le motif.
"""
from __future__ import annotations

import json
import re
import shutil
import sqlite3
import unicodedata
from pathlib import Path
from typing import Any

from api import chemins, db
from api.services import evenements, generateurs_registre, taches
from api.services import lots as lots_svc
from api.services import styles as styles_svc
from api.services.routage import VOIES_SANS_FABRICATION
from api.services.taches import TacheDefinitive

TYPE_TACHE = "fabriquer_code"
ETAPES = ("generation", "finition", "tests", "rendus")
LIBELLES = {"generation": "Génération", "finition": "Finition", "tests": "Tests", "rendus": "Rendus"}
ETAPES_RELANCABLES = ("references", *ETAPES)
VARIANTE_PAR_DEFAUT = "A"  # objet sans référence choisie (lot d'avant l'étape 6) : la première variante du générateur
FICHIERS_PUBLICS = ("vignette.png", "planche.png", "face.png", "dos.png", "profil.png", "trois_quarts.png", "dessus.png")


class FabricationImpossible(RuntimeError):
    pass


# --- identifiants et dossiers ---------------------------------------------------------------------------

def _mot(texte: str) -> str:
    """'bouclier rond' -> 'BouclierRond' (ASCII, pour un nom d'asset)."""
    ascii_ = unicodedata.normalize("NFKD", texte or "").encode("ascii", "ignore").decode("ascii")
    return "".join(m.capitalize() for m in re.split(r"[^A-Za-z0-9]+", ascii_) if m) or "Objet"


def identifiant(conn: sqlite3.Connection, theme: str, categorie: str, type_objet: str, objet_id: int) -> str:
    """<THEME>_<CATEGORIE>_<Nom>_<Variante> (CLAUDE.md) ; un objet garde son identifiant d'un essai à l'autre."""
    deja = db.une(conn, "SELECT id FROM assets WHERE objet_id = ?", (objet_id,))
    if deja:
        return deja["id"]
    base = f"{_mot(theme).upper()}_{'ARCHI' if categorie == 'module_archi' else 'PROP'}_{_mot(type_objet)}"
    for lettre in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
        if not db.une(conn, "SELECT 1 FROM assets WHERE id = ?", (f"{base}_{lettre}",)):
            return f"{base}_{lettre}"
    raise FabricationImpossible(f"plus de variante libre pour {base}")


def dossier_essai(essai: dict) -> Path:
    return chemins.dossier_lots() / essai["dossier"]


def fichier_public(essai_id: int, fichier: str) -> Path:
    """Un rendu d'un essai servi à l'interface (liste fermée de noms : aucune traversée possible)."""
    if fichier not in FICHIERS_PUBLICS:
        raise FileNotFoundError(fichier)
    conn = db.connexion()
    try:
        essai = db.une(conn, "SELECT * FROM essais WHERE id = ?", (essai_id,))
    finally:
        conn.close()
    if essai is None:
        raise FileNotFoundError(fichier)
    chemin = dossier_essai(essai) / "asset" / "rendus" / fichier
    if not chemin.is_file():
        raise FileNotFoundError(fichier)
    return chemin


# --- lancer -----------------------------------------------------------------------------------------------

def _tache_active(conn: sqlite3.Connection, objet_id: int) -> bool:
    return db.une(conn, "SELECT 1 FROM taches WHERE objet_id = ? AND type = ? AND etat IN ('en_attente', 'en_cours')",
                  (objet_id, TYPE_TACHE)) is not None


def motif_refus(conn: sqlite3.Connection, o: dict, manifestes: dict) -> str | None:
    """Pourquoi cet objet ne peut pas être fabriqué maintenant, ou None s'il le peut."""
    if o["retire"] or o["voie"] in VOIES_SANS_FABRICATION:
        return "objet retiré, réutilisé ou hors périmètre : rien à fabriquer"
    if o["voie"] != "code":
        return "objet mixte ou import : leur fabrication arrive avec la suite de l'étape 7" if o["voie"] != "ia" \
            else "objet fait par IA : il passe par Meshy, pas par un script"
    if o["etape"] == "brief":
        return "valide d'abord le brief"
    if o["etape"] == "references" and o.get("reference_id") is None:
        return "choisis d'abord sa référence (écran Références)"
    if o["etape"] not in ETAPES_RELANCABLES:
        return "déjà fabriqué : il attend la revue"
    if _tache_active(conn, o["id"]):
        return "déjà en cours de fabrication"
    if not o["generateur"] or o["generateur"] not in manifestes:
        return f"générateur « {o['generateur'] or '?'} » introuvable dans generators/"
    return None


def pieces_declarees(m: dict, params: dict, racine: Path | None = None) -> int:
    """Pièces attendues : `pieces(params)` du générateur quand le nombre dépend des réglages, sinon le MANIFESTE."""
    try:
        f = getattr(generateurs_registre.charger(m["nom"], racine), "pieces", None)
    except KeyError:
        f = None
    return int(f(params)) if callable(f) else int(m["pieces_declarees"])


GENERATEURS_IA = ("meshy",)


def infos_objet(objet: dict) -> dict[str, Any]:
    """Voie IA : ce que la finition et les contrôles savent de l'objet (le brief, pas un MANIFESTE)."""
    dims = json.loads(objet["dimensions_json"] or "null") or {}
    dimensions = [dims.get("largeur"), dims.get("profondeur"), dims.get("hauteur")]
    return {"nom": objet["nom"], "categorie": objet["categorie"] or "prop_moyen", "famille": objet["famille"] or "props",
            "dimensions_type": objet["type_objet"], "symetrique": objet["symetrique"] if objet["symetrique"] in ("X", "Y") else None,
            "dimensions_m": [float(x) for x in dimensions] if all(isinstance(x, int | float) and x > 0 for x in dimensions)
            else None, "voie": "ia"}


def _echec_qualite(conn: sqlite3.Connection, cfg: dict, essai: dict, ia: bool, message: str, rapport: dict) -> dict:
    """Un contrôle bloquant en échec. Voie code : échec tout de suite (un générateur rejouable redonne le même
    objet). Voie IA : nouvel essai automatique tant qu'il en reste (cahier : « relance automatique, 3 au plus ») ;
    la tâche se termine sans alerte, l'essai garde son rapport."""
    erreur = _echec(conn, essai, message, rapport)
    if not ia:
        raise erreur
    from api.services import fabrication_ia

    suite = fabrication_ia.relancer_auto(conn, cfg, essai, message)
    if suite is None:
        n = int(db.une(conn, "SELECT COUNT(*) AS n FROM essais WHERE objet_id = ?", (essai["objet_id"],))["n"])
        raise TacheDefinitive(f"{message} (après {n - 1} relance{'s' if n > 2 else ''} automatique{'s' if n > 2 else ''})")
    return {"essai": essai["id"], "relance": suite, "motif": message}


def params_choisis(conn: sqlite3.Connection, o: dict, m: dict) -> dict:
    """Les réglages de la variante choisie aux Références ; sans choix, la première variante du générateur."""
    if o.get("reference_id") is not None:
        p = db.une(conn, "SELECT params_json FROM propositions WHERE id = ? AND genre = 'variante'", (o["reference_id"],))
        if p is not None:
            return dict(json.loads(p["params_json"] or "{}"))
    return {"variante": VARIANTE_PAR_DEFAUT, **dict((m.get("variantes") or {}).get(VARIANTE_PAR_DEFAUT) or {})}


def lancer(conn: sqlite3.Connection, cfg: dict, lot_id: int, objet_id: int | None = None) -> list[int]:
    """Un essai et sa tâche (file Blender) par objet code prêt ; renvoie les ids des tâches créées."""
    lot = lots_svc._ligne(conn, lot_id)
    if lot["style_id"] is None:
        raise FabricationImpossible("le lot n'a pas de style")
    objets = [o for o in lots_svc.objets_du_lot(conn, lot_id) if objet_id is None or o["id"] == objet_id]
    if objet_id is not None and not objets:
        raise lots_svc.LotIntrouvable(f"objet {objet_id} introuvable dans le lot {lot_id}")
    manifestes, _ = generateurs_registre.manifestes()
    prets = [o for o in objets if motif_refus(conn, o, manifestes) is None]
    if not prets:
        raise FabricationImpossible(motif_refus(conn, objets[0], manifestes) if objet_id is not None
                                    else "aucun objet en voie code prêt à fabriquer dans ce lot")
    ids = []
    for o in prets:
        m = manifestes[o["generateur"]]
        numero = 1 + int(db.une(conn, "SELECT COALESCE(MAX(numero), 0) AS n FROM essais WHERE objet_id = ?",
                                (o["id"],))["n"])
        params = params_choisis(conn, o, m)
        with db.transaction(conn):
            essai_id = db.inserer(conn, "essais", {
                "objet_id": o["id"], "numero": numero, "generateur": o["generateur"],
                "params_json": json.dumps(params, ensure_ascii=False), "etat": "en_attente",
                "dossier": f"{lot_id}/{o['id']}/essai-{numero}"})
            conn.execute("UPDATE objets SET etape = 'generation' WHERE id = ?", (o["id"],))
        ids.append(taches.creer_tache(conn, TYPE_TACHE, "blender", {"essai_id": essai_id}, lot_id=lot_id,
                                      objet_id=o["id"], essai_id=essai_id, cfg=cfg))
    lots_svc.synchroniser_etat(conn, lot_id)
    conn.commit()
    return ids


# --- exécuter (worker) --------------------------------------------------------------------------------------

def _etape(conn: sqlite3.Connection, essai: dict, nom: str) -> None:
    conn.execute("UPDATE objets SET etape = ? WHERE id = ?", (nom, essai["objet_id"]))
    conn.execute("UPDATE essais SET etat = ?, debute_le = COALESCE(debute_le, ?) WHERE id = ?",
                 (nom, db.maintenant(), essai["id"]))
    conn.commit()


def _echec(conn: sqlite3.Connection, essai: dict, message: str, rapport: dict | None = None) -> TacheDefinitive:
    conn.execute("UPDATE essais SET etat = 'echec', erreur = ?, fini_le = ?, rapport_tests_json = COALESCE(?, rapport_tests_json) "
                 "WHERE id = ?", (message[:2000], db.maintenant(), json.dumps(rapport, ensure_ascii=False) if rapport else None,
                                  essai["id"]))
    conn.commit()
    return TacheDefinitive(message)


def _rendre(cfg: dict, blend: Path, dossier: Path, id_asset: str, style, travail: Path, arret) -> dict:
    """EEVEE d'abord ; Cycles sur le processeur si EEVEE n'a pas de carte graphique utilisable."""
    from pipeline import blender

    entree = {"blend": str(blend), "dossier": str(dossier), "id": id_asset}
    try:
        return blender.lancer("rendre", {**entree, "moteur": "eevee"}, cfg, travail, style=style, arret=arret)
    except blender.EchecBlender as e:
        r = blender.lancer("rendre", {**entree, "moteur": "cycles"}, cfg, travail, style=style, arret=arret)
        r["repli"] = f"EEVEE indisponible ({str(e)[:200]}) : rendu par Cycles"
        return r


def executer(conn: sqlite3.Connection, cfg: dict, params: dict, tache_id: int | None = None, progression=None,
             arret=None) -> dict[str, Any]:
    from pipeline import blender, meta, planche, validate

    essai = db.une(conn, "SELECT * FROM essais WHERE id = ?", (int(params["essai_id"]),))
    if essai is None:
        raise TacheDefinitive(f"essai {params['essai_id']} introuvable")
    objet = db.une(conn, "SELECT * FROM objets WHERE id = ?", (essai["objet_id"],))
    lot = lots_svc._ligne(conn, objet["lot_id"])
    style_row = db.une(conn, "SELECT code FROM styles WHERE id = ?", (lot["style_id"],))
    style = styles_svc.charger_style(style_row["code"])
    ia = essai["generateur"] in GENERATEURS_IA
    params_essai = json.loads(essai["params_json"] or "{}")
    source = json.loads(essai["source_json"] or "{}")
    if ia:
        m = infos_objet(objet)
    else:
        manifestes, _ = generateurs_registre.manifestes()
        m = manifestes.get(essai["generateur"])
        if m is None:
            raise _echec(conn, essai, f"générateur « {essai['generateur']} » introuvable dans generators/")
        m = {**m, "pieces_declarees": pieces_declarees(m, params_essai)}  # selon les réglages (amphore sans anses)
    voie = "ia" if ia else "code"
    reprise = taches.lire_reprise(conn, tache_id) if tache_id is not None else {}
    faites: list[str] = list(reprise.get("faites") or [])
    id_asset = reprise.get("id") or identifiant(conn, style.theme, m["categorie"], objet["type_objet"] or m["nom"], objet["id"])
    dossier = dossier_essai(essai)
    asset = dossier / "asset"
    infos = {**m, "id": id_asset}

    def noter(nom: str, donnees: dict | None = None) -> None:
        faites.append(nom)
        reprise.update({"faites": faites, "id": id_asset, nom: donnees or {}})
        if tache_id is not None:
            taches.noter_reprise(conn, tache_id, reprise)

    def avancer(pct: float, texte: str) -> None:
        if progression:
            progression(pct, texte)

    etape_courante = "generation"
    try:
        if "generation" not in faites:
            _etape(conn, essai, etape_courante := "generation")
            if ia:
                avancer(5, "import : l'objet 3D reçu de Meshy")
                glb = dossier / str(source.get("glb") or "")
                if not source.get("glb") or not glb.is_file():
                    raise _echec(conn, essai, "objet 3D de Meshy introuvable : relance sa génération")
                r = blender.lancer("importer", {"glb": str(glb), "id": id_asset, "dossier": str(dossier)}, cfg, dossier,
                                   style=style, arret=arret)
            else:
                avancer(5, f"génération : generators/{m['nom']}.py")
                fichier = generateurs_registre.dossier() / f"{m['nom']}.py"
                r = blender.lancer("generer", {"fichier": str(fichier), "params": params_essai, "seed": 0, "id": id_asset,
                                               "dossier": str(dossier)}, cfg, dossier, style=style, arret=arret)
            noter("generation", {"blend": r["blend"], "tris": r["tris"]})
        if "finition" not in faites:
            _etape(conn, essai, etape_courante := "finition")
            avancer(30, "finition : échelle, débris, textures, LOD, collision, export" if ia
                    else "finition : échelle, matériaux du style, LOD, collision, export")
            if asset.exists():
                shutil.rmtree(asset)
            r = blender.lancer("finir", {"blend": reprise["generation"]["blend"], "dossier": str(asset), "id": id_asset,
                                         "infos": m, "voie": voie}, cfg, dossier, style=style, arret=arret)
            noter("finition", {k: r.get(k) for k in ("tris_lod0", "tris_lod1", "tris_lod2", "tris_collision")})
            interne = json.loads((asset / "rapport_interne.json").read_text(encoding="utf-8"))
            if ia:
                provenance = {
                    "generateur": f"meshy:{params_essai.get('ai_model', 'latest')}",
                    "parametres": {**params_essai, "reference": source.get("reference")},
                    "sources": [{"nom": "Meshy image-to-3d", "outil": "meshy", "licence": "Meshy-Pro",
                                 "tache": source.get("meshy_id"), "simule": bool(source.get("simule"))}],
                    "outils_ia": {"geometrie": "Meshy image-to-3d", "textures": "Meshy"},
                    "pieces_declarees": interne.get("pieces_declarees"), "textures": interne.get("textures") or None}
            else:
                provenance = {"generateur": meta.reference_generateur(m["nom"]), "parametres": params_essai,
                              "pieces_declarees": m["pieces_declarees"], "variante": params_essai.get("variante")}
            (asset / "meta.json").write_text(json.dumps(meta.construire_meta(
                id=id_asset, categorie=m["categorie"], voie=voie,
                dimensions_m=interne["normalisation"]["dimensions_m"], tris_lod0=interne["tris_lod0"],
                tris_lod1=interne["tris_lod1"], tris_lod2=interne["tris_lod2"], tris_collision=interne["tris_collision"],
                style=style.nom, version_style=style.version, seed=0, symetrique=m["symetrique"],
                dimensions_type=m["dimensions_type"], **provenance), ensure_ascii=False, indent=2), encoding="utf-8")
        if "tests" not in faites:
            _etape(conn, essai, etape_courante := "tests")
            avancer(55, "tests : les contrôles du cahier des charges")
            rapport = validate.valider(asset, style, infos, cfg)
            echecs = [f"{c.nom} ({c.detail})" for c in rapport.controles if c.bloquant and not c.ok and c.nom != "Rendus"]
            if echecs or not rapport.licence.get("ok", False):
                motifs = echecs + ([] if rapport.licence.get("ok") else [rapport.licence.get("detail", "licence")])
                return _echec_qualite(conn, cfg, essai, ia, "contrôles en échec : " + " ; ".join(motifs), rapport.to_dict())
            noter("tests")
        if "rendus" not in faites:
            _etape(conn, essai, etape_courante := "rendus")
            avancer(75, "rendus : 5 vues et planche de contact")
            r = _rendre(cfg, asset / f"{id_asset}.blend", asset / "rendus", id_asset, style, dossier, arret)
            planche.assembler(asset / "rendus", f"{id_asset} · {objet['nom']}")
            noter("rendus", {"moteur": r["moteur"], "repli": r.get("repli")})
        rapport = validate.valider(asset, style, infos, cfg)
        (asset / "rapport.json").write_text(rapport.to_json(), encoding="utf-8")
        if not rapport.bloquants_ok:
            return _echec_qualite(conn, cfg, essai, ia, "contrôles en échec : " + " ; ".join(
                f"{c.nom} ({c.detail})" for c in rapport.controles if c.bloquant and not c.ok), rapport.to_dict())
    except blender.BlenderIntrouvable as e:
        raise _echec(conn, essai, str(e)) from e
    except blender.EchecBlender as e:
        if "délai dépassé" in str(e):
            raise RuntimeError(str(e)) from e  # une machine occupée : une relance peut passer
        raise _echec(conn, essai, f"{LIBELLES[etape_courante]} : {e}") from e
    _ranger(conn, essai, objet, lot, style, id_asset, m, asset, rapport, voie)
    avancer(100, "prêt pour la revue")
    return {"asset": id_asset, "essai": essai["id"], "rendus": reprise.get("rendus", {}).get("moteur")}


def _ranger(conn: sqlite3.Connection, essai: dict, objet: dict, lot: dict, style, id_asset: str, m: dict,
            asset: Path, rapport, voie: str = "code") -> None:
    """L'objet passe en revue ; l'asset et sa nouvelle version entrent en base ; « revue prête » si le lot l'est."""
    maintenant = db.maintenant()
    meta_json = (asset / "meta.json").read_text(encoding="utf-8")
    with db.transaction(conn):
        if db.une(conn, "SELECT 1 FROM assets WHERE id = ?", (id_asset,)) is None:
            db.inserer(conn, "assets", {"id": id_asset, "lot_id": lot["id"], "objet_id": objet["id"], "nom": objet["nom"],
                                        "theme": style.theme, "categorie": m["categorie"], "voie": voie, "statut": "revue",
                                        "cree_le": maintenant, "maj_le": maintenant})
        numero = 1 + int(db.une(conn, "SELECT COALESCE(MAX(numero), 0) AS n FROM versions WHERE asset_id = ?",
                                (id_asset,))["n"])
        version_id = db.inserer(conn, "versions", {
            "asset_id": id_asset, "essai_id": essai["id"], "numero": numero, "meta_json": meta_json,
            "dossier": str(Path(essai["dossier"]) / "asset"), "tris_lod0": json.loads(meta_json)["tris_lod0"],
            "cree_le": maintenant})
        conn.execute("UPDATE assets SET version_active_id = ?, maj_le = ?, statut = 'revue' WHERE id = ?",
                     (version_id, maintenant, id_asset))
        conn.execute("UPDATE essais SET etat = 'pret', fini_le = ?, erreur = NULL, rapport_tests_json = ? WHERE id = ?",
                     (maintenant, json.dumps(rapport.to_dict(), ensure_ascii=False), essai["id"]))
        conn.execute("UPDATE objets SET etape = 'revue' WHERE id = ?", (objet["id"],))
        evenements.ecrire(conn, "objet_pret", f"Prêt à valider : {objet['nom']}", id_asset, niveau="succes",
                          lien=f"/lots/{lot['id']}/generation", lot_id=lot["id"], objet_id=objet["id"])
    lots_svc.synchroniser_etat(conn, lot["id"])
    objets = [o for o in lots_svc.objets_du_lot(conn, lot["id"]) if not o["retire"] and o["voie"] not in VOIES_SANS_FABRICATION]
    tous_prets = objets and all(lots_svc.RANG.get(o["etape"], 1) >= 4 for o in objets)
    if tous_prets and not db.une(conn, "SELECT 1 FROM evenements WHERE type = ? AND lot_id = ?",
                                 (evenements.REVUE_PRETE, lot["id"])):
        evenements.ecrire(conn, evenements.REVUE_PRETE, f"À valider · {lot['nom'] or 'projet ' + str(lot['id'])}",
                          f"{len(objets)} objet{'s' if len(objets) > 1 else ''} à regarder", niveau="succes",
                          lien=f"/lots/{lot['id']}/revue", lot_id=lot["id"])
    conn.commit()
