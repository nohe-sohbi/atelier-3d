"""Références (étape 6, B4) : pour chaque objet du lot, des propositions à choisir avant la fabrication.

- Objet IA, ou pièce IA d'un objet mixte (correction 2) : 4 images Meshy dans le style du lot. La consigne est écrite
  par l'app (gabarit du style + description de l'objet) ; l'utilisateur peut la réécrire. Les images sont guidées par
  la planche du style, ou par une image que l'utilisateur a donnée (« 4 images d'après celle-ci »).
- Objet code : 4 variantes de réglages du générateur, rendues par Blender, gratuites (correction 1).
- L'utilisateur peut aussi donner sa propre image et la choisir telle quelle.

Les propositions arrivent au « Générer les références » du Brief ; « 4 autres » en redemande une série. Le choix sert
d'entrée à la fabrication : « Lancer la génération 3D » fabrique les objets code avec la variante choisie et met les
envoie l'image des objets IA à Meshy, puis la même chaîne. Un objet sans référence au lancement est mis de côté.
"""
from __future__ import annotations

import io
import json
import os
import random
import re
import shutil
import sqlite3
from pathlib import Path
from typing import Any

from api import chemins, db
from api import config as cfgmod
from api.adapters import get_meshy
from api.adapters.meshy.base import IMAGES_REFERENCE_PAR_OBJET
from api.services import couts, evenements, fabrication, generateurs_registre, images_meshy, taches
from api.services import lots as lots_svc
from api.services import styles as styles_svc
from api.services.routage import VOIES_SANS_FABRICATION
from api.services.taches import TacheDefinitive

TYPE_IMAGES = "references_images"
TYPE_VARIANTES = "references_variantes"
PAR_SERIE = IMAGES_REFERENCE_PAR_OBJET  # 4 propositions par série
MAX_MODELES_STYLE = 4      # images de la planche envoyées à Meshy avec la consigne (limite de l'API : 5 en tout)
MAX_CONSIGNE = 1000
MAX_IMAGE_OCTETS = 20 * 1024 * 1024  # limite de Meshy pour une image
MIN_IMAGE_PX = 32                     # Meshy refuse une image de référence sous 32 × 32 px
TAILLE_APERCU_PX = 384
# Deux aperçus sont « la même image » quand moins de 0,4 % de leurs pixels changent nettement (réglage invisible : la
# profondeur des cannelures d'une colonne lisse). Mesuré : 0 à 0,33 % pour ces cas, 0,53 % pour un chapiteau en moins.
IDENTIQUE = 0.004
EXTENSIONS = (".png", ".jpg", ".jpeg", ".webp")
_FICHIER = re.compile(r"^[A-Za-z0-9._-]+$")


class ReferenceImpossible(RuntimeError):
    """L'action ne peut pas se faire maintenant (objet déjà lancé, déjà en préparation, sans référence…)."""


# --- objets et dossiers ------------------------------------------------------------------------------------

def genre_de(o: dict) -> str | None:
    """« images » (voie IA ou mixte), « variantes » (voie code), ou None : pas de référence à choisir."""
    if o["retire"] or o["voie"] in VOIES_SANS_FABRICATION:
        return None
    return {"ia": "images", "mixte": "images", "code": "variantes"}.get(o["voie"])


def _objet(conn: sqlite3.Connection, lot_id: int, objet_id: int) -> dict:
    o = next((x for x in lots_svc.objets_du_lot(conn, lot_id) if x["id"] == objet_id), None)
    if o is None:
        raise lots_svc.LotIntrouvable(f"objet {objet_id} introuvable dans le lot {lot_id}")
    return o


def dossier_references(lot_id: int, objet_id: int) -> Path:
    return chemins.dossier_lots() / str(lot_id) / str(objet_id) / "references"


def _style_du_lot(conn: sqlite3.Connection, lot: dict):
    r = db.une(conn, "SELECT id, code FROM styles WHERE id = ?", (lot["style_id"],)) if lot["style_id"] else None
    if r is None:
        raise ReferenceImpossible("le lot n'a pas de style : choisis-en un dans le Brief")
    return r, styles_svc.charger_style(r["code"])


def _piece_ia(o: dict) -> dict | None:
    return next((p for p in o["pieces"] if p["voie"] == "ia"), None) if o["voie"] == "mixte" else None


def _tache_active(conn: sqlite3.Connection, objet_id: int) -> dict | None:
    r = db.une(conn, "SELECT * FROM taches WHERE objet_id = ? AND type IN (?, ?) AND etat IN ('en_attente', 'en_cours') "
                     "ORDER BY id DESC LIMIT 1", (objet_id, TYPE_IMAGES, TYPE_VARIANTES))
    return taches._charger(r) if r else None


# --- consigne ----------------------------------------------------------------------------------------------

def consigne_par_defaut(style, o: dict) -> str:
    """Le gabarit du style (prop ou archi) rempli avec l'objet (ou sa pièce IA) et sa description."""
    gabarits = style.prompts_reference
    gabarit = gabarits.get("archi" if o["categorie"] == "module_archi" else "prop") \
        or next(iter(gabarits.values()), "{objet}, couleurs {palette}")
    piece = _piece_ia(o)
    sujet = f"{piece['nom']} ({o['nom']})" if piece else o["nom"]
    if o["description"]:
        sujet = f"{sujet} : {o['description'].rstrip('.')}"
    palette = ", ".join(nom.replace("_", " ") for nom in style.palette)
    return gabarit.replace("{objet}", sujet).replace("{palette}", palette)


def consigne(style, o: dict) -> str:
    return o["consigne"] or consigne_par_defaut(style, o)


def modifier_consigne(conn: sqlite3.Connection, lot_id: int, objet_id: int, texte: str | None) -> dict:
    """Ta consigne pour les prochaines images de cet objet ; vide : celle de l'app revient."""
    o = _objet(conn, lot_id, objet_id)
    if genre_de(o) != "images":
        raise ReferenceImpossible("seuls les objets faits par IA ont une consigne d'image")
    texte = " ".join((texte or "").split())
    if len(texte) > MAX_CONSIGNE:
        raise ValueError(f"consigne trop longue ({len(texte)} caractères, {MAX_CONSIGNE} au plus)")
    conn.execute("UPDATE objets SET consigne = ? WHERE id = ?", (texte or None, objet_id))
    conn.commit()
    return objet_vue(conn, lot_id, objet_id)


# --- variantes d'un générateur -----------------------------------------------------------------------------

def _nombre(v: float) -> str:
    return f"{v:.2f}".rstrip("0").rstrip(".").replace(".", ",")


def _libelle_param(nom: str) -> str:
    return nom.removesuffix("_m").replace("_", " ").capitalize()


def legende(m: dict, params: dict) -> str:
    """Ce qui distingue le plus ces réglages de ceux par défaut du générateur, en deux éléments au plus : les choix
    d'abord, puis les nombres qui s'écartent le plus de leur défaut (rapporté à leur plage)."""
    diffs: list[tuple[float, str]] = []
    for nom, schema in m["parametres"].items():
        if nom not in params or params[nom] == schema.get("defaut") or schema.get("style_dim"):
            continue
        v = params[nom]
        if schema["type"] == "choix":
            diffs.append((2.0, f"{_libelle_param(nom)} {str(v).replace('_', ' ')}"))
        elif schema["type"] == "bool":
            diffs.append((2.0, f"{'Avec' if v else 'Sans'} {_libelle_param(nom).lower()}"))
        else:
            plage = float(schema.get("max", 1) or 1) - float(schema.get("min", 0) or 0)
            ecart = abs(float(v) - float(schema["defaut"])) / (plage or 1.0)
            unite = " m" if nom.endswith("_m") else ""
            diffs.append((ecart, f"{_libelle_param(nom)} {_nombre(float(v))}{unite}"))
    diffs.sort(key=lambda d: -d[0])
    return " · ".join(t for _, t in diffs[:2]) or "Réglages par défaut"


def _tirage(m: dict, rng: random.Random) -> dict:
    """Des réglages tirés au hasard (rejouable : le tirage dépend du générateur, de la série et du rang).

    Les choix et les cases varient librement ; les nombres décimaux autour de leur défaut (la moitié centrale de leur
    plage) ; les entiers (finesse, nombre d'éléments) et les dimensions (celles du style) gardent leur valeur."""
    params = {}
    for nom, schema in m["parametres"].items():
        if schema.get("style_dim"):
            continue
        t = schema["type"]
        if t == "choix":
            params[nom] = rng.choice(list(schema["choix"]))
        elif t == "bool":
            params[nom] = rng.random() < 0.5
        elif t == "float" and schema.get("min") is not None and schema.get("max") is not None:
            lo, hi = float(schema["min"]), float(schema["max"])
            d = float(schema["defaut"])
            ecart = (hi - lo) / 4
            params[nom] = round(min(hi, max(lo, d + rng.uniform(-ecart, ecart))), 3)
    return params


ECART_MIN = 0.2  # un tirage doit se voir : un choix différent, ou un décimal éloigné d'un cinquième de sa plage


def _ecart(m: dict, a: dict, b: dict) -> float:
    """Le plus grand écart entre deux réglages : 1 pour un choix ou une case différents, l'écart relatif à la plage pour
    un décimal (plusieurs petits écarts invisibles ne font pas une différence visible)."""
    ecart = 0.0
    for nom, schema in m["parametres"].items():
        va, vb = a.get(nom, schema.get("defaut")), b.get(nom, schema.get("defaut"))
        if schema["type"] == "float" and schema.get("min") is not None and schema.get("max") is not None:
            ecart = max(ecart, abs(float(va) - float(vb)) / max(1e-9, float(schema["max"]) - float(schema["min"])))
        elif va != vb:
            ecart = max(ecart, 1.0)
    return ecart


def variantes_candidates(m: dict, serie: int, n: int = 3 * PAR_SERIE) -> list[tuple[dict, str]]:
    """Jusqu'à n jeux de réglages qui se distinguent à l'œil : la 1re série commence par les variantes nommées du
    générateur (A, B, C…), puis des tirages assez éloignés de tout ce qui précède ; les séries suivantes ne sont
    que des tirages (rejouables : ils dépendent du générateur, de la série et du rang)."""
    out: list[tuple[dict, str]] = []
    if serie == 1:
        for lettre, params in (m.get("variantes") or {}).items():
            p = {"variante": lettre, **dict(params)}
            if all(_ecart(m, p, q) > 0 for q, _ in out):
                out.append((p, legende(m, p)))
    k = 0
    while len(out) < n and k < 50 * n:
        p = _tirage(m, random.Random(f"{m['nom']}:{m['version']}:{serie}:{k}"))
        k += 1
        if all(_ecart(m, p, q) >= ECART_MIN for q, _ in out):
            out.append((p, legende(m, p)))
    return out[:n]


# --- préparer une série ------------------------------------------------------------------------------------

def _serie_suivante(conn: sqlite3.Connection, objet_id: int) -> int:
    return 1 + int(db.une(conn, "SELECT COALESCE(MAX(serie), 0) AS n FROM propositions WHERE objet_id = ?", (objet_id,))["n"])


def preparer(conn: sqlite3.Connection, cfg: dict, lot_id: int, objet_id: int, modele_id: int | None = None) -> int:
    """Demande 4 propositions pour un objet (la série suivante) ; renvoie l'id de la tâche.

    modele_id : une image donnée par l'utilisateur, qui guide les 4 images à la place de la planche du style."""
    lot = lots_svc._ligne(conn, lot_id)
    o = _objet(conn, lot_id, objet_id)
    genre = genre_de(o)
    if genre is None:
        raise ReferenceImpossible("cet objet n'a pas de référence à choisir (import, réutilisé ou retiré)")
    if o["etape"] != "references":
        raise ReferenceImpossible("valide d'abord le brief" if o["etape"] == "brief"
                                  else "déjà lancé : sa référence ne change plus")
    if _tache_active(conn, objet_id):
        raise ReferenceImpossible("des propositions sont déjà en préparation pour cet objet")
    _, style = _style_du_lot(conn, lot)
    params: dict[str, Any] = {"objet_id": objet_id, "serie": _serie_suivante(conn, objet_id)}
    if genre == "variantes":
        if modele_id is not None:
            raise ReferenceImpossible("un objet fait par code se règle par ses variantes, pas par une image")
        if not o["generateur"]:
            raise ReferenceImpossible("aucun générateur pour cet objet")
        return taches.creer_tache(conn, TYPE_VARIANTES, "blender", params, lot_id=lot_id, objet_id=objet_id, cfg=cfg)
    if modele_id is not None:
        p = db.une(conn, "SELECT id FROM propositions WHERE id = ? AND objet_id = ? AND genre = 'perso'", (modele_id, objet_id))
        if p is None:
            raise lots_svc.LotIntrouvable(f"image {modele_id} introuvable pour cet objet")
        params["modele_id"] = modele_id
    params["consigne"] = consigne(style, o)
    return taches.creer_tache(conn, TYPE_IMAGES, "meshy", params, lot_id=lot_id, objet_id=objet_id, cfg=cfg)


def preparer_lot(conn: sqlite3.Connection, cfg: dict, lot_id: int) -> list[int]:
    """Après « Générer les références » : une première série pour chaque objet qui n'en a pas encore."""
    ids = []
    for o in lots_svc.objets_du_lot(conn, lot_id):
        if o["etape"] != "references" or genre_de(o) is None or _tache_active(conn, o["id"]):
            continue
        if db.une(conn, "SELECT 1 FROM propositions WHERE objet_id = ? AND serie > 0", (o["id"],)):
            continue
        try:
            ids.append(preparer(conn, cfg, lot_id, o["id"]))
        except ReferenceImpossible:
            continue
    return ids


# --- exécuter (worker) -------------------------------------------------------------------------------------

def _contexte(conn: sqlite3.Connection, params: dict) -> tuple[dict, dict, Any]:
    objet = db.une(conn, "SELECT lot_id FROM objets WHERE id = ?", (int(params["objet_id"]),))
    if objet is None:
        raise TacheDefinitive(f"objet {params['objet_id']} introuvable")
    lot = lots_svc._ligne(conn, objet["lot_id"])
    o = _objet(conn, lot["id"], int(params["objet_id"]))
    if o["etape"] != "references" or o["retire"]:
        raise TacheDefinitive("objet déjà lancé ou mis de côté : ces propositions ne serviraient plus")
    try:
        _, style = _style_du_lot(conn, lot)
    except ReferenceImpossible as e:
        raise TacheDefinitive(str(e)) from e
    return lot, o, style


def _modeles_du_style(conn: sqlite3.Connection, lot: dict) -> list[Path]:
    """Les images gardées de la planche du style ; à défaut ses images d'inspiration."""
    r, _ = _style_du_lot(conn, lot)
    board = styles_svc.dossier_style(r["code"]) / "board"
    gardees = [board / i["fichier"] for i in db.toutes(
        conn, "SELECT fichier FROM planche_images WHERE style_id = ? AND gardee = 1 AND remplacee = 0 ORDER BY id", (r["id"],))]
    return [p for p in gardees if p.is_file()] or styles_svc.inspirations(r["code"])


def _ranger(conn: sqlite3.Connection, lot: dict, o: dict, tache_id: int | None, serie: int,
            lignes: list[dict], credits_simules: bool | None = None) -> list[int]:
    """Remplace les propositions de cette tâche (le refaire ne double rien) et note les crédits Meshy."""
    with db.transaction(conn):
        if tache_id is not None:
            conn.execute("DELETE FROM propositions WHERE tache_id = ?", (tache_id,))
            conn.execute("DELETE FROM couts WHERE tache_id = ? AND service = 'meshy'", (tache_id,))
        ids = []
        for ligne in lignes:
            if ligne["credits"]:
                couts.enregistrer(conn, "meshy", "reference", simule=bool(credits_simules), credits=ligne["credits"],
                                  lot_id=lot["id"], tache_id=tache_id, detail={"objet_id": o["id"], "fichier": ligne["fichier"]})
            ids.append(db.inserer(conn, "propositions", {
                "objet_id": o["id"], "serie": serie, "rang": ligne["rang"], "genre": ligne["genre"],
                "fichier": ligne["fichier"], "legende": ligne["legende"],
                "params_json": json.dumps(ligne["params"], ensure_ascii=False), "credits": ligne["credits"],
                "simule": 1 if ligne.get("simule") else 0, "tache_id": tache_id, "cree_le": db.maintenant()}))
    _signaler_si_pret(conn, lot, tache_id)
    return ids


def executer_images(conn: sqlite3.Connection, meshy, params: dict, tache_id: int | None = None, progression=None,
                    arret=None, attente_s: float = 0.5, max_lectures: int = 600) -> dict:
    """Corps de la tâche `references_images` (file meshy) : 4 images d'après la consigne, rangées avec l'objet."""
    lot, o, _style = _contexte(conn, params)
    serie = int(params["serie"])
    modeles = _modeles_du_style(conn, lot)[:MAX_MODELES_STYLE]
    if params.get("modele_id") is not None:
        p = db.une(conn, "SELECT fichier FROM propositions WHERE id = ? AND objet_id = ?", (int(params["modele_id"]), o["id"]))
        if p is None:
            raise TacheDefinitive("l'image modèle a disparu : redonne-la")
        # L'image donnée guide ; la planche du style n'accompagne que pour la couleur (une image, pas plus).
        modeles = [dossier_references(lot["id"], o["id"]) / p["fichier"], *modeles[:1]]
    texte = str(params["consigne"])
    simule = getattr(meshy, "mode", "") == "simule"
    dossier = dossier_references(lot["id"], o["id"])
    dossier.mkdir(parents=True, exist_ok=True)
    tmp = dossier / f".tmp-{tache_id if tache_id is not None else 'direct'}"
    shutil.rmtree(tmp, ignore_errors=True)
    demandes = [images_meshy.Demande(texte, modeles, f"{o['nom']} · image {i + 1}") for i in range(PAR_SERIE)]
    try:
        recues = images_meshy.generer(conn, meshy, demandes, tmp, tache_id=tache_id, progression=progression,
                                      arret=arret, quoi="images de référence", attente_s=attente_s, max_lectures=max_lectures)
        lignes = []
        for image in recues:
            nom = f"s{serie}-{image.rang + 1}-{image.meshy_id[-8:]}{image.fichier.suffix.lower()}"
            os.replace(image.fichier, dossier / nom)
            lignes.append({"rang": image.rang, "genre": "image", "fichier": nom, "legende": "",
                           "params": {"consigne": texte, "modele_id": params.get("modele_id")},
                           "credits": image.credits, "simule": simule})
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    ids = _ranger(conn, lot, o, tache_id, serie, lignes, credits_simules=simule)
    if progression:
        progression(100, "images rangées")
    return {"propositions": ids, "credits": sum(x["credits"] for x in lignes), "simule": simule}


def _apercus(cfg: dict, fichier: Path, variantes: list[dict], style, travail: Path, arret) -> dict:
    """EEVEE d'abord ; Cycles sur le processeur si EEVEE n'a pas de carte graphique utilisable."""
    from pipeline import blender

    entree = {"fichier": str(fichier), "variantes": variantes, "taille_px": TAILLE_APERCU_PX}
    try:
        return blender.lancer("apercus", {**entree, "moteur": "eevee"}, cfg, travail, style=style, arret=arret)
    except blender.EchecBlender as e:
        if "délai dépassé" in str(e):
            raise
        return blender.lancer("apercus", {**entree, "moteur": "cycles"}, cfg, travail, style=style, arret=arret)


def _signature(chemin: Path):
    """L'aperçu réduit en 192 × 192 niveaux de gris, pour reconnaître deux images identiques."""
    import numpy as np
    from PIL import Image

    with Image.open(chemin) as im:
        return np.asarray(im.convert("L").resize((192, 192)), dtype=np.float32)


def _meme_image(a, b) -> bool:
    return float((abs(a - b) > 8).mean()) < IDENTIQUE


def executer_variantes(conn: sqlite3.Connection, cfg: dict, params: dict, tache_id: int | None = None,
                       progression=None, arret=None) -> dict:
    """Corps de la tâche `references_variantes` (file blender) : 4 réglages du générateur, une image chacun."""
    from pipeline import blender

    lot, o, style = _contexte(conn, params)
    serie = int(params["serie"])
    manifestes, _ = generateurs_registre.manifestes()
    m = manifestes.get(o["generateur"] or "")
    if m is None:
        raise TacheDefinitive(f"générateur « {o['generateur'] or '?'} » introuvable dans generators/")
    fichier = generateurs_registre.dossier() / f"{m['nom']}.py"
    dossier = dossier_references(lot["id"], o["id"])
    travail = dossier / f".tmp-{tache_id if tache_id is not None else 'direct'}"
    shutil.rmtree(travail, ignore_errors=True)
    candidates = variantes_candidates(m, serie)
    gardees: list[tuple[dict, str, Path]] = []
    signatures: list[Any] = []
    erreurs: list[str] = []
    identiques = 0
    try:
        curseur = 0
        while len(gardees) < PAR_SERIE and curseur < len(candidates):
            essai = candidates[curseur:curseur + PAR_SERIE - len(gardees)]
            if progression:
                progression(10 + 80 * curseur / len(candidates), f"Blender : {len(essai)} variantes à rendre")
            entree = [{"params": p, "seed": 0, "sortie": str(travail / f"v{curseur + i}.png")} for i, (p, _) in enumerate(essai)]
            curseur += len(essai)
            try:
                r = _apercus(cfg, fichier, entree, style, travail, arret)
            except blender.BlenderIntrouvable as e:
                raise TacheDefinitive(str(e)) from e
            except blender.EchecBlender as e:
                if "délai dépassé" in str(e):
                    raise RuntimeError(str(e)) from e  # une machine occupée : une relance peut passer
                raise TacheDefinitive(f"variantes impossibles : {e}") from e
            for (p, texte), v, e in zip(essai, r["variantes"], entree, strict=True):
                if not v.get("ok"):
                    erreurs.append(str(v.get("erreur")))
                    continue
                sig = _signature(Path(e["sortie"]))
                if any(_meme_image(sig, autre) for autre in signatures):
                    identiques += 1  # un réglage qui ne change rien à l'image : une autre variante prend sa place
                    continue
                signatures.append(sig)
                gardees.append((p, texte, Path(e["sortie"])))
        if not gardees:
            raise TacheDefinitive("aucune variante ne se construit : " + (erreurs[0] if erreurs else "motif inconnu"))
        lignes = []
        for rang, (p, texte, chemin) in enumerate(gardees[:PAR_SERIE]):
            nom = f"s{serie}-{rang + 1}.png"
            os.replace(chemin, dossier / nom)
            lignes.append({"rang": rang, "genre": "variante", "fichier": nom, "legende": texte, "params": p, "credits": 0})
    finally:
        shutil.rmtree(travail, ignore_errors=True)
    ids = _ranger(conn, lot, o, tache_id, serie, lignes)
    if progression:
        progression(100, "variantes rendues")
    return {"propositions": ids, "variantes": len(lignes), "refusees": len(erreurs), "identiques": identiques}


def _signaler_si_pret(conn: sqlite3.Connection, lot: dict, tache_finie: int | None = None) -> None:
    """« Références prêtes » quand chaque objet à choisir a ses propositions et que plus rien ne se prépare.

    Une tâche qui a déjà rangé ses propositions compte comme finie même si le worker ne l'a pas encore close : deux
    préparations qui finissent ensemble ne s'attendent pas l'une l'autre."""
    a_choisir = [o for o in lots_svc.objets_du_lot(conn, lot["id"]) if o["etape"] == "references" and genre_de(o)]
    if not a_choisir:
        return
    for o in a_choisir:
        if not db.une(conn, "SELECT 1 FROM propositions WHERE objet_id = ?", (o["id"],)):
            return
        active = _tache_active(conn, o["id"])
        if active and active["id"] != tache_finie and not db.une(
                conn, "SELECT 1 FROM propositions WHERE tache_id = ?", (active["id"],)):
            return
    if db.une(conn, "SELECT 1 FROM evenements WHERE type = ? AND lot_id = ?", (evenements.REFERENCES_PRETES, lot["id"])):
        return  # une fois par lot : « 4 autres » se demande depuis l'écran, inutile de re-prévenir
    n = len(a_choisir)
    evenements.ecrire(conn, evenements.REFERENCES_PRETES, f"Références prêtes · {lot['nom'] or 'lot ' + str(lot['id'])}",
                      f"{n} objet{'s' if n > 1 else ''} : choisis une référence pour chacun", niveau="succes",
                      lien=f"/lots/{lot['id']}/references", lot_id=lot["id"])
    conn.commit()


# --- choisir, donner son image -----------------------------------------------------------------------------

def choisir(conn: sqlite3.Connection, lot_id: int, objet_id: int, proposition_id: int) -> dict:
    o = _objet(conn, lot_id, objet_id)
    if o["etape"] != "references":
        raise ReferenceImpossible("déjà lancé : sa référence ne change plus")
    if not db.une(conn, "SELECT 1 FROM propositions WHERE id = ? AND objet_id = ?", (proposition_id, objet_id)):
        raise lots_svc.LotIntrouvable(f"proposition {proposition_id} introuvable pour cet objet")
    conn.execute("UPDATE objets SET reference_id = ? WHERE id = ?", (proposition_id, objet_id))
    conn.commit()
    return objet_vue(conn, lot_id, objet_id)


def ajouter_image(conn: sqlite3.Connection, lot_id: int, objet_id: int, nom_fichier: str, contenu: bytes) -> dict:
    """Ton image pour cet objet : elle rejoint ses propositions et devient la référence choisie."""
    from PIL import Image, UnidentifiedImageError

    o = _objet(conn, lot_id, objet_id)
    if genre_de(o) != "images":
        raise ReferenceImpossible("un objet fait par code se règle par ses variantes, pas par une image")
    if o["etape"] != "references":
        raise ReferenceImpossible("déjà lancé : sa référence ne change plus")
    extension = Path(nom_fichier or "").suffix.lower()
    if extension not in EXTENSIONS:
        raise ValueError("image attendue (.png, .jpg, .webp)")
    if len(contenu) > MAX_IMAGE_OCTETS:
        raise ValueError("image trop lourde (20 Mo au plus)")
    try:
        with Image.open(io.BytesIO(contenu)) as im:
            largeur, hauteur = im.size
            im.verify()
    except (UnidentifiedImageError, OSError, SyntaxError) as e:
        raise ValueError("ce fichier n'est pas une image lisible") from e
    if min(largeur, hauteur) < MIN_IMAGE_PX:  # Meshy refuse une image de référence plus petite
        raise ValueError(f"image trop petite ({largeur} × {hauteur} px) : {MIN_IMAGE_PX} × {MIN_IMAGE_PX} px au moins")
    dossier = dossier_references(lot_id, objet_id)
    dossier.mkdir(parents=True, exist_ok=True)
    rang = int(db.une(conn, "SELECT COUNT(*) AS n FROM propositions WHERE objet_id = ? AND genre = 'perso'", (objet_id,))["n"])
    nom = f"perso-{rang + 1}{'.jpg' if extension == '.jpeg' else extension}"
    (dossier / nom).write_bytes(contenu)
    with db.transaction(conn):
        pid = db.inserer(conn, "propositions", {
            "objet_id": objet_id, "serie": 0, "rang": rang, "genre": "perso", "fichier": nom, "legende": "Ton image",
            "params_json": json.dumps({"nom_origine": Path(nom_fichier).name}, ensure_ascii=False), "credits": 0,
            "simule": 0, "tache_id": None, "cree_le": db.maintenant()})
        conn.execute("UPDATE objets SET reference_id = ? WHERE id = ?", (pid, objet_id))
    return objet_vue(conn, lot_id, objet_id)


def fichier_public(proposition_id: int) -> Path:
    """Le fichier d'une proposition, servi à l'interface (chemin lu en base : aucune traversée possible)."""
    conn = db.connexion()
    try:
        p = db.une(conn, "SELECT p.fichier, o.lot_id, o.id AS objet_id FROM propositions p JOIN objets o ON o.id = p.objet_id "
                         "WHERE p.id = ?", (proposition_id,))
    finally:
        conn.close()
    if p is None or not _FICHIER.match(p["fichier"]) or p["fichier"].startswith("."):
        raise FileNotFoundError(str(proposition_id))
    chemin = dossier_references(p["lot_id"], p["objet_id"]) / p["fichier"]
    if not chemin.is_file():
        raise FileNotFoundError(str(proposition_id))
    return chemin


def rouvrir(conn: sqlite3.Connection, lot_id: int, objet_id: int) -> dict:
    """« Choisir une autre référence » depuis Génération : un objet dont la fabrication a échoué revient aux Références
    (un générateur refait toujours le même objet ; pour l'IA, une autre image change tout)."""
    from api.services import fabrication_ia

    o = _objet(conn, lot_id, objet_id)
    if o["voie"] not in ("code", "ia") or o["etape"] not in fabrication.ETAPES:
        raise ReferenceImpossible("seul un objet en échec de fabrication revient aux Références")
    essai = db.une(conn, "SELECT etat FROM essais WHERE objet_id = ? ORDER BY numero DESC LIMIT 1", (objet_id,))
    actif = fabrication._tache_active(conn, objet_id) or fabrication_ia._tache_active(conn, objet_id)
    if essai is None or essai["etat"] != "echec" or actif:
        raise ReferenceImpossible("sa fabrication n'a pas échoué : rien à rechoisir")
    with db.transaction(conn):
        conn.execute("UPDATE objets SET etape = 'references' WHERE id = ?", (objet_id,))
        conn.execute("UPDATE pieces SET etape = 'references' WHERE objet_id = ?", (objet_id,))
    lots_svc.synchroniser_etat(conn, lot_id)
    conn.commit()
    return objet_vue(conn, lot_id, objet_id)


# --- lancer la génération ----------------------------------------------------------------------------------

def lancer(conn: sqlite3.Connection, cfg: dict, lot_id: int) -> dict:
    """« Lancer la génération 3D » : chaque objet aux Références part avec sa référence choisie.

    Code : fabrication par Blender avec la variante choisie. IA : l'image choisie part à Meshy, puis la même chaîne.
    Mixte et import CC0 : en attente de leur fabrication (suite de l'étape 7). Sans référence choisie : mis de côté."""
    objets = [o for o in lots_svc.objets_du_lot(conn, lot_id)
              if o["etape"] == "references" and not o["retire"] and o["voie"] not in VOIES_SANS_FABRICATION]
    a_lancer = [o for o in objets if genre_de(o) is None or o["reference_id"] is not None]
    if not a_lancer:
        raise ReferenceImpossible("choisis d'abord une référence pour au moins un objet")
    mis_de_cote = [o for o in objets if o not in a_lancer]
    from api.services import fabrication_ia

    code = [o for o in a_lancer if o["voie"] == "code"]
    ia = [o for o in a_lancer if o["voie"] == "ia"]
    manifestes, _ = generateurs_registre.manifestes()
    refus = [f"{o['nom']} ({motif})" for o in code if (motif := fabrication.motif_refus(conn, o, manifestes))]
    refus += [f"{o['nom']} ({motif})" for o in ia if (motif := fabrication_ia.motif_refus(conn, o))]
    if refus:
        raise ReferenceImpossible("rien n'est lancé, ces objets ne peuvent pas partir : " + " ; ".join(refus))
    with db.transaction(conn):
        for o in mis_de_cote:
            conn.execute("UPDATE objets SET retire = 1 WHERE id = ?", (o["id"],))
        for o in a_lancer:
            if o["voie"] not in ("code", "ia"):
                conn.execute("UPDATE objets SET etape = 'generation' WHERE id = ?", (o["id"],))
                conn.execute("UPDATE pieces SET etape = 'generation' WHERE objet_id = ?", (o["id"],))
        if mis_de_cote:
            evenements.ecrire(conn, "objets_mis_de_cote", "Objets mis de côté au lancement",
                              ", ".join(o["nom"] for o in mis_de_cote), niveau="info", lot_id=lot_id)
    for o in objets:  # des propositions encore en file ne serviraient plus à rien
        t = _tache_active(conn, o["id"])
        if t and t["etat"] == "en_attente":
            taches.annuler_tache(conn, t["id"])
    taches_ids = []
    for o in code:
        taches_ids += fabrication.lancer(conn, cfg, lot_id, o["id"])
    for o in ia:
        taches_ids.append(fabrication_ia.lancer(conn, cfg, lot_id, o["id"]))
    lots_svc.synchroniser_etat(conn, lot_id)
    conn.commit()
    return {"taches": taches_ids, "lances": len(a_lancer), "par_code": len(code), "par_ia": len(ia),
            "en_attente": len(a_lancer) - len(code) - len(ia), "mis_de_cote": [o["nom"] for o in mis_de_cote]}


# --- vue de l'écran ----------------------------------------------------------------------------------------

def _proposition_vue(p: dict, choix_id: int | None) -> dict:
    return {"id": p["id"], "genre": p["genre"], "serie": p["serie"], "rang": p["rang"], "legende": p["legende"],
            "url": f"/api/fichiers/references/{p['id']}", "simule": bool(p["simule"]), "choisie": p["id"] == choix_id}


def _erreur_recente(conn: sqlite3.Connection, objet_id: int) -> dict | None:
    """La dernière préparation échouée, si aucune série n'est arrivée après elle."""
    t = db.une(conn, "SELECT * FROM taches WHERE objet_id = ? AND type IN (?, ?) ORDER BY id DESC LIMIT 1",
               (objet_id, TYPE_IMAGES, TYPE_VARIANTES))
    if t is None or t["etat"] not in ("echouee", "annulee"):
        return None
    return {"tache_id": t["id"], "message": t["erreur"] or ("annulée" if t["etat"] == "annulee" else "échec"),
            "peut_relancer": True}


def objet_vue(conn: sqlite3.Connection, lot_id: int, objet_id: int, style=None) -> dict:
    lot = lots_svc._ligne(conn, lot_id)
    o = _objet(conn, lot_id, objet_id)
    if style is None:
        _, style = _style_du_lot(conn, lot)
    genre = genre_de(o)
    toutes = db.toutes(conn, "SELECT * FROM propositions WHERE objet_id = ? ORDER BY serie, rang, id", (objet_id,))
    derniere = max((p["serie"] for p in toutes), default=0)
    visibles = [p for p in toutes if p["serie"] == derniere and derniere > 0]
    visibles += [p for p in toutes if p["genre"] == "perso"]
    choisie = next((p for p in toutes if p["id"] == o["reference_id"]), None)
    if choisie is not None and choisie not in visibles:
        visibles.insert(0, choisie)
    active = _tache_active(conn, objet_id)
    progression = (active["resultat"] or {}).get("progression") if active and isinstance(active["resultat"], dict) else None
    piece = _piece_ia(o)
    return {
        "id": o["id"], "nom": o["nom"], "voie": o["voie"], "genre": genre, "etape": o["etape"],
        "piece_ia": piece["nom"] if piece else None,
        "consigne": consigne(style, o) if genre == "images" else None,
        "consigne_modifiee": bool(o["consigne"]) if genre == "images" else False,
        "peut_changer": o["etape"] == "references" and genre is not None,
        "choix_id": o["reference_id"],
        "propositions": [_proposition_vue(p, o["reference_id"]) for p in visibles],
        "series": derniere,
        "preparation": {"tache_id": active["id"], "etat": active["etat"], "pct": (progression or {}).get("pct"),
                        "texte": (progression or {}).get("texte")} if active else None,
        "erreur": None if active else _erreur_recente(conn, objet_id),
    }


def vue(conn: sqlite3.Connection, cfg: dict, lot_id: int) -> dict:
    lot = lots_svc._ligne(conn, lot_id)
    r, style = _style_du_lot(conn, lot)
    tous = [o for o in lots_svc.objets_du_lot(conn, lot_id) if not o["retire"] and o["voie"] not in VOIES_SANS_FABRICATION]
    objets = [objet_vue(conn, lot_id, o["id"], style) for o in tous if genre_de(o)]
    a_choisir = [o for o in objets if o["peut_changer"]]
    meshy = get_meshy(cfg)
    detail = styles_svc.detail(conn, r["id"])
    return {
        "lot_id": lot_id,
        "objets": objets,
        "choisies": sum(1 for o in a_choisir if o["choix_id"] is not None),
        "a_choisir": len(a_choisir),
        "sans_choix": [o["nom"] for o in a_choisir if o["choix_id"] is None],
        "sans_reference": [o["nom"] for o in tous if not genre_de(o) and o["etape"] == "references"],
        "deja_lances": sum(1 for o in objets if not o["peut_changer"]),
        "peut_lancer": any(o["choix_id"] is not None for o in a_choisir)
                       or any(not genre_de(o) and o["etape"] == "references" for o in tous),
        "credits_serie": meshy.credits_image * PAR_SERIE,
        "meshy_simule": cfgmod.mode(cfg, "meshy") == "simule",
        "style": {"id": detail["id"], "code": detail["code"], "nom": detail["nom"], "palette": detail["palette"],
                  "materiaux": [m["nom"] for m in detail["materiaux"]],
                  "budgets": [{"libelle": b["libelle"], "tris": b["tris"]} for b in detail["budgets"]],
                  "texel_density": detail["texel_density"], "unite": detail["unite"]},
    }
