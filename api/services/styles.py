"""Styles (étape 2) : un dossier par style, `style/<code>/style.yaml` + `board/` + `inspiration/`.

La table `styles` indexe les fichiers (une ligne par version) ; le yaml reste la source des valeurs.
Un style se crée en brouillon, reçoit une planche de référence (images Meshy, simulées par défaut),
puis se valide. « Dupliquer en v1 » crée une nouvelle version : un nouveau dossier, l'ancien reste
lisible parce que des lots peuvent le garder (correction 11 du cahier des charges).
"""
from __future__ import annotations

import copy
import logging
import re
import shutil
import sqlite3
import time
import unicodedata
from pathlib import Path
from typing import Any

from api import chemins, db
from api.services import style_yaml, taches
from api.services.taches import TacheDefinitive

log = logging.getLogger("api.styles")

TYPE_TACHE_PLANCHE = "planche_style"
NB_IMAGES_PLANCHE = 6
_CODE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*-v(\d+)$")
_FICHIER = re.compile(r"^[A-Za-z0-9._-]+$")
ETATS = ("brouillon", "valide")


class StyleIntrouvable(LookupError):
    pass


class ConflitCode(ValueError):
    pass


class StyleUtilise(ValueError):
    """Un lot utilise cette version : on ne la modifie pas en place, on duplique."""


class AucuneImageGardee(ValueError):
    pass


# --- codes et chemins -------------------------------------------------------

def slug(texte: str) -> str:
    base = unicodedata.normalize("NFKD", texte or "").encode("ascii", "ignore").decode("ascii").lower()
    base = re.sub(r"[^a-z0-9]+", "-", base).strip("-")
    return base or "style"


def code_depuis_nom(nom: str, version: int = 0) -> str:
    return f"{slug(nom)}-v{version}"


def base_du_code(code: str) -> str:
    m = _CODE.match(code)
    if not m:
        raise ValueError(f"code de style invalide : {code!r} (attendu mot-cle-vN)")
    return code[: -len(f"-v{m.group(1)}")]


def valider_code(code: str) -> str:
    if not _CODE.match(code or ""):
        raise ValueError(f"code de style invalide : {code!r} (attendu des minuscules, chiffres et tirets, finissant par -vN)")
    return code


def dossier_style(code: str) -> Path:
    return chemins.dossier_styles() / valider_code(code)


def chemin_yaml(code: str) -> Path:
    return dossier_style(code) / "style.yaml"


def charger_style(code: str) -> style_yaml.Style:
    return style_yaml.charger(chemin_yaml(code))


# --- table ------------------------------------------------------------------

def _ligne(conn: sqlite3.Connection, style_id: int) -> dict:
    r = db.une(conn, "SELECT * FROM styles WHERE id = ?", (style_id,))
    if r is None:
        raise StyleIntrouvable(f"style {style_id} introuvable")
    return r


def par_code(conn: sqlite3.Connection, code: str) -> dict | None:
    return db.une(conn, "SELECT * FROM styles WHERE code = ?", (code,))


def _inserer(conn: sqlite3.Connection, brut: dict, code: str, etat: str, parent_id: int | None = None,
             racine_id: int | None = None) -> dict:
    sid = db.inserer(conn, "styles", {
        "nom": str(brut["nom"]), "theme": str(brut["theme"]), "version": int(brut["version"]),
        "chemin_yaml": f"{code}/style.yaml", "cree_le": db.maintenant(), "parent_id": parent_id,
        "actif": 1, "code": code, "description": str(brut.get("description", "")),
        "direction": str(brut["direction"]), "note_version": str(brut.get("note_version", "")),
        "etat": etat, "valide_le": db.maintenant() if etat == "valide" else None, "racine_id": racine_id,
    })
    if racine_id is None:
        conn.execute("UPDATE styles SET racine_id = ? WHERE id = ?", (sid, sid))
    return _ligne(conn, sid)


def importer_dossier(conn: sqlite3.Connection) -> list[str]:
    """Au démarrage : chaque `style/<code>/style.yaml` absent de la table y entre (livré avec le dépôt)."""
    importes = []
    racine = chemins.dossier_styles()
    if not racine.is_dir():
        return importes
    for fichier in sorted(racine.glob("*/style.yaml")):
        code = fichier.parent.name
        if not _CODE.match(code) or par_code(conn, code):
            continue
        try:
            s = style_yaml.charger(fichier)
        except (style_yaml.StyleInvalide, OSError, ValueError) as e:
            log.warning("style %s ignoré : %s", code, e)
            continue
        if s.nom != code:
            log.warning("style %s ignoré : le champ `style` du yaml vaut %r", code, s.nom)
            continue
        # Une version livrée avec le dépôt est complète : validée. Sa famille : la v0 du même code de base.
        parent = db.une(conn, "SELECT id, racine_id FROM styles WHERE code LIKE ? ORDER BY version DESC LIMIT 1",
                        (base_du_code(code) + "-v%",))
        _inserer(conn, s.brut, code, "valide", parent_id=parent["id"] if parent else None,
                 racine_id=parent["racine_id"] if parent else None)
        importes.append(code)
    return importes


# --- lecture ------------------------------------------------------------------

def _palette(s: style_yaml.Style) -> list[dict]:
    return [{"nom": nom, "hex": hexa} for nom, hexa in s.palette.items()]


def _usage(conn: sqlite3.Connection, style_id: int) -> dict:
    lots = db.une(conn, "SELECT COUNT(*) AS n FROM lots WHERE style_id = ?", (style_id,))["n"]
    assets = db.une(conn, """SELECT COUNT(*) AS n FROM assets a JOIN lots l ON l.id = a.lot_id
                             WHERE l.style_id = ? AND a.statut != 'archive'""", (style_id,))["n"]
    return {"lots": int(lots), "assets": int(assets)}


def _resume(conn: sqlite3.Connection, r: dict) -> dict:
    s = charger_style(r["code"])
    return {"id": r["id"], "code": r["code"], "nom": r["nom"], "version": r["version"], "etat": r["etat"],
            "direction": r["direction"], "description": r["description"], "palette": _palette(s),
            "usage": _usage(conn, r["id"]), "cree_le": r["cree_le"], "valide_le": r["valide_le"]}


def lister(conn: sqlite3.Connection) -> list[dict]:
    rows = db.toutes(conn, "SELECT * FROM styles ORDER BY racine_id, version, id")
    out = []
    for r in rows:
        try:
            out.append(_resume(conn, r))
        except (style_yaml.StyleInvalide, OSError, ValueError) as e:
            out.append({"id": r["id"], "code": r["code"], "nom": r["nom"], "version": r["version"],
                        "etat": r["etat"], "direction": r["direction"], "description": r["description"],
                        "palette": [], "usage": _usage(conn, r["id"]), "cree_le": r["cree_le"],
                        "valide_le": r["valide_le"], "erreur": f"fichier illisible : {e}"})
    return out


def _images(conn: sqlite3.Connection, r: dict) -> list[dict]:
    rows = db.toutes(conn, "SELECT * FROM planche_images WHERE style_id = ? AND remplacee = 0 ORDER BY id", (r["id"],))
    return [{"id": i["id"], "fichier": i["fichier"], "objet": i["objet_generique"], "gardee": bool(i["gardee"]),
             "simule": bool(i["simule"]), "credits": i["credits"], "cree_le": i["cree_le"],
             "url": f"/api/fichiers/styles/{r['code']}/board/{i['fichier']}"} for i in rows]


def detail(conn: sqlite3.Connection, style_id: int) -> dict:
    r = _ligne(conn, style_id)
    s = charger_style(r["code"])
    palette = s.palette
    materiaux = [{"nom": nom, "base": m.get("base"), "hex": palette.get(m.get("base"), ""),
                  "roughness": m.get("roughness"), "metallic": m.get("metallic"), "usage_assets": 0}
                 for nom, m in s.materiaux.items()]
    budgets = [{"cle": c, "libelle": s.libelle_categorie(c), "tris": s.budgets_tris.get(c),
                "textures_px": s.textures_px.get(c)} for c in style_yaml.CATEGORIES]
    versions = db.toutes(conn, "SELECT * FROM styles WHERE racine_id = ? ORDER BY version, id", (r["racine_id"],))
    lots = db.toutes(conn, "SELECT id, nom FROM lots WHERE style_id = ? ORDER BY id", (style_id,))
    images = _images(conn, r)
    return {
        **_resume(conn, r),
        "theme": s.theme, "note_version": r["note_version"], "parent_id": r["parent_id"], "racine_id": r["racine_id"],
        "materiaux": materiaux, "budgets": budgets, "texel_density": s.texel_density, "unite": "1 = 1 m",
        "tolerances": s.tolerances, "dimensions_m": s.dimensions_m, "objets_planche": s.objets_planche,
        "prompts_reference": s.prompts_reference,
        "planche": images,
        "credits_planche": int(db.une(conn, "SELECT COALESCE(SUM(credits), 0) AS c FROM planche_images WHERE style_id = ?",
                                      (style_id,))["c"]),
        "inspirations": [f"/api/fichiers/styles/{r['code']}/inspiration/{p.name}"
                         for p in sorted((dossier_style(r["code"]) / "inspiration").glob("*")) if p.is_file()],
        "versions": [{"id": v["id"], "code": v["code"], "version": v["version"], "note": v["note_version"],
                      "date": v["cree_le"], "etat": v["etat"]} for v in versions],
        "lots": [{"id": lot["id"], "nom": lot["nom"]} for lot in lots],
        "peut_modifier": not lots,
    }


# --- création, modification, versions -------------------------------------------

def _materiaux_depuis_palette(palette: dict[str, str], reference: dict | None) -> dict:
    """Un matériau par couleur de la palette ; quand la référence a un matériau sur la même couleur de base,
    on garde son nom, sa rugosité et son aspect métallique."""
    par_base = {m.get("base"): (nom, m) for nom, m in (reference or {}).items()}
    out: dict = {}
    for couleur in palette:
        if couleur in par_base:
            nom, m = par_base[couleur]
            out[nom] = {"base": couleur, "roughness": m.get("roughness", 0.8), "metallic": m.get("metallic", 0.0)}
        else:
            out[couleur] = {"base": couleur, "roughness": 0.8, "metallic": 0.0}
    return out


def creer(conn: sqlite3.Connection, donnees: dict) -> dict:
    """Nouveau style en brouillon. `donnees` : nom, code?, description, palette {nom: hex}, direction?,
    budgets_depuis (id d'un style de référence) ou budgets {categorie: tris} + texel_density + dimensions_m."""
    nom = str(donnees.get("nom", "")).strip()
    if not nom:
        raise style_yaml.StyleInvalide("le nom est obligatoire")
    code = valider_code(str(donnees.get("code") or code_depuis_nom(nom)))
    if par_code(conn, code) or dossier_style(code).exists():
        raise ConflitCode(f"le code {code} existe déjà")
    reference = None
    if donnees.get("budgets_depuis") is not None:
        reference = charger_style(_ligne(conn, int(donnees["budgets_depuis"]))["code"]).brut
    palette = {slug(k).replace("-", "_"): v for k, v in dict(donnees.get("palette") or {}).items()}
    brut: dict[str, Any] = {
        "style": code, "nom": nom,
        "theme": str(donnees.get("theme") or (reference or {}).get("theme") or slug(nom)[:3].upper()),
        "version": int(code.rsplit("-v", 1)[1]),
        "direction": str(donnees.get("direction") or (reference or {}).get("direction") or "stylise"),
        "description": str(donnees.get("description", "")),
        "note_version": "Version initiale.",
        "units": "meters", "conventions": {"haut": "+Z", "face_avant": "-Y"},
        "texel_density_px_per_m": donnees.get("texel_density") or (reference or {}).get("texel_density_px_per_m"),
        "palette": palette,
        "materiaux": _materiaux_depuis_palette(palette, (reference or {}).get("materiaux")),
        "budgets_tris": donnees.get("budgets") or (reference or {}).get("budgets_tris"),
        "textures_px": donnees.get("textures_px") or (reference or {}).get("textures_px"),
        "lod_ratios": (reference or {}).get("lod_ratios") or [1.0, 0.5, 0.25],
        "usure": (reference or {}).get("usure") or {"aretes": 0.4, "cavites": 0.3},
        "tolerances": donnees.get("tolerances") or (reference or {}).get("tolerances")
        or {"dimensions_pct": 5, "texel_pct": 15, "symetrie_m": 0.005, "lod_pct": 10},
        "dimensions_m": donnees.get("dimensions_m") or (reference or {}).get("dimensions_m"),
        "objets_planche": (reference or {}).get("objets_planche"),
        "pivot": (reference or {}).get("pivot") or {"defaut": "sol_centre", "armes": "poignee", "outils": "poignee"},
        "prompts_reference": (reference or {}).get("prompts_reference") or {
            "prop": "{objet}, " + (str(donnees.get("description", "")).rstrip(".") or "style de jeu vidéo")
                    + ", prop de jeu vidéo, formes lisibles, couleurs {palette}, fond neutre uni, vue trois-quarts, sans texte",
        },
    }
    brut = {k: v for k, v in brut.items() if v is not None}
    if brut.get("dimensions_m") is None:
        raise style_yaml.StyleInvalide("dimensions_m manquant : choisis un style de référence ou saisis les budgets et dimensions")
    style_yaml.ecrire(brut, chemin_yaml(code))
    (dossier_style(code) / "board").mkdir(exist_ok=True)
    return _inserer(conn, brut, code, "brouillon")


CHAMPS_MODIFIABLES = ("nom", "description", "palette", "materiaux", "budgets_tris", "textures_px",
                      "texel_density_px_per_m", "tolerances", "dimensions_m", "objets_planche", "prompts_reference")


def modifier(conn: sqlite3.Connection, style_id: int, champs: dict) -> dict:
    r = _ligne(conn, style_id)
    if _usage(conn, style_id)["lots"]:
        raise StyleUtilise("un lot utilise cette version du style : duplique-la en nouvelle version pour la modifier")
    brut = copy.deepcopy(charger_style(r["code"]).brut)
    for k, v in champs.items():
        if k in CHAMPS_MODIFIABLES and v is not None:
            brut[k] = v
    style_yaml.ecrire(brut, chemin_yaml(r["code"]))
    conn.execute("UPDATE styles SET nom = ?, description = ? WHERE id = ?",
                 (str(brut["nom"]), str(brut.get("description", "")), style_id))
    return detail(conn, style_id)


def dupliquer(conn: sqlite3.Connection, style_id: int, note: str = "") -> dict:
    """« Dupliquer en v1 » : nouvelle version du même style, l'ancienne reste telle quelle."""
    r = _ligne(conn, style_id)
    base = base_du_code(r["code"])
    derniere = db.une(conn, "SELECT MAX(version) AS v FROM styles WHERE racine_id = ?", (r["racine_id"],))["v"]
    version = int(derniere if derniere is not None else r["version"]) + 1
    code = f"{base}-v{version}"
    if par_code(conn, code) or dossier_style(code).exists():
        raise ConflitCode(f"le code {code} existe déjà")
    shutil.copytree(dossier_style(r["code"]), dossier_style(code))
    brut = copy.deepcopy(charger_style(r["code"]).brut)
    brut.update({"style": code, "version": version, "note_version": note or f"Version {version}, copiée de la v{r['version']}."})
    style_yaml.ecrire(brut, chemin_yaml(code))
    nouveau = _inserer(conn, brut, code, r["etat"], parent_id=style_id, racine_id=r["racine_id"])
    # La planche suit la copie : mêmes fichiers, même état « gardée ».
    for i in db.toutes(conn, "SELECT * FROM planche_images WHERE style_id = ? AND remplacee = 0 ORDER BY id", (style_id,)):
        db.inserer(conn, "planche_images", {k: i[k] for k in ("fichier", "objet_generique", "gardee", "credits", "simule", "cree_le")} | {"style_id": nouveau["id"]})
    return detail(conn, nouveau["id"])


# --- planche de référence ---------------------------------------------------------

def demander_planche(conn: sqlite3.Connection, cfg: dict, style_id: int, image_id: int | None = None) -> int:
    """Crée la tâche Meshy (file meshy) : 6 images, ou 1 pour « Refaire » une image."""
    r = _ligne(conn, style_id)
    params: dict[str, Any] = {"style_id": style_id, "code": r["code"]}
    if image_id is not None:
        i = db.une(conn, "SELECT * FROM planche_images WHERE id = ? AND style_id = ?", (image_id, style_id))
        if i is None:
            raise StyleIntrouvable(f"image {image_id} introuvable")
        params.update({"image_id": image_id, "n": 1, "objets": [i["objet_generique"]]})
    else:
        params["n"] = NB_IMAGES_PLANCHE
    return taches.creer_tache(conn, TYPE_TACHE_PLANCHE, "meshy", params, cfg=cfg)


def prompt_planche(s: style_yaml.Style, objet: str) -> str:
    gabarit = s.prompts_reference.get("prop") or next(iter(s.prompts_reference.values()), "{objet}, couleurs {palette}")
    return gabarit.replace("{objet}", objet.replace("_", " ")).replace("{palette}", ", ".join(s.palette))


def executer_planche(conn: sqlite3.Connection, meshy, params: dict, progression=None, attente_s: float = 0.5) -> dict:
    """Corps de la tâche `planche_style` (worker) : génère, télécharge, range dans board/, consigne en base."""
    r = _ligne(conn, int(params["style_id"]))
    s = charger_style(r["code"])
    n = int(params.get("n", NB_IMAGES_PLANCHE))
    objets = list(params.get("objets") or s.objets_planche)[:n]
    if len(objets) < n:
        objets += [f"objet-{i + 1}" for i in range(len(objets), n)]
    prompt = prompt_planche(s, objets[0] if n == 1 else "objets génériques")
    try:
        tid = meshy.image_vers_image(prompt, None, n=n)
    except RuntimeError as e:
        if "insuffisant" in str(e):
            raise TacheDefinitive(f"crédits Meshy insuffisants pour {n} image(s) : {e}") from e
        raise
    if progression:
        progression(10, "images demandées à Meshy")
    for _ in range(600):
        etat = meshy.etat_tache(tid)
        if etat["status"] == "SUCCEEDED":
            break
        if etat["status"] == "FAILED":
            raise RuntimeError(f"Meshy a échoué : {etat.get('task_error')}")
        if progression:
            progression(10 + 0.8 * float(etat.get("progress", 0)), f"Meshy : {etat.get('progress', 0)} %")
        time.sleep(attente_s)
    else:
        raise RuntimeError("Meshy ne finit pas (délai dépassé)")
    board = dossier_style(r["code"]) / "board"
    tmp = board / f".tmp-{tid}"
    tmp.mkdir(parents=True, exist_ok=True)
    meshy.telecharger(tid, tmp)
    fichiers = sorted(p for p in tmp.iterdir() if p.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp"))
    credits_par_image = int(etat.get("credits", 0)) // max(1, n) if etat.get("credits") else 0
    simule = 1 if getattr(meshy, "mode", "") == "simule" else 0
    crees = []
    for i, src in enumerate(fichiers[:n]):
        objet = objets[i] if i < len(objets) else f"objet-{i + 1}"
        nom = f"{slug(objet)}-{tid[-8:]}{src.suffix.lower()}"
        shutil.move(str(src), str(board / nom))
        crees.append(db.inserer(conn, "planche_images", {
            "style_id": r["id"], "fichier": nom, "objet_generique": objet, "gardee": 0,
            "tache_id": None, "credits": credits_par_image, "simule": simule, "cree_le": db.maintenant()}))
    shutil.rmtree(tmp, ignore_errors=True)
    if params.get("image_id") is not None and crees:
        # « Refaire » : l'ancienne image est remplacée (fichier effacé) ; sa ligne reste pour compter ses crédits.
        ancienne = db.une(conn, "SELECT fichier FROM planche_images WHERE id = ?", (int(params["image_id"]),))
        if ancienne:
            (board / ancienne["fichier"]).unlink(missing_ok=True)
            conn.execute("UPDATE planche_images SET remplacee = 1, gardee = 0 WHERE id = ?", (int(params["image_id"]),))
    if progression:
        progression(100, "planche rangée")
    return {"images": crees, "simule": bool(simule), "credits": credits_par_image * len(crees)}


def garder_image(conn: sqlite3.Connection, style_id: int, image_id: int, gardee: bool) -> dict:
    _ligne(conn, style_id)
    cur = conn.execute("UPDATE planche_images SET gardee = ? WHERE id = ? AND style_id = ?",
                       (1 if gardee else 0, image_id, style_id))
    if cur.rowcount != 1:
        raise StyleIntrouvable(f"image {image_id} introuvable")
    return detail(conn, style_id)


def valider(conn: sqlite3.Connection, style_id: int) -> dict:
    r = _ligne(conn, style_id)
    gardees = db.toutes(conn, "SELECT fichier FROM planche_images WHERE style_id = ? AND gardee = 1 ORDER BY id", (style_id,))
    if not gardees:
        raise AucuneImageGardee("garde au moins une image de la planche avant de valider le style")
    brut = copy.deepcopy(charger_style(r["code"]).brut)
    brut["planche"] = [g["fichier"] for g in gardees]
    style_yaml.ecrire(brut, chemin_yaml(r["code"]))
    conn.execute("UPDATE styles SET etat = 'valide', valide_le = ? WHERE id = ?", (db.maintenant(), style_id))
    return detail(conn, style_id)


def ajouter_inspiration(conn: sqlite3.Connection, style_id: int, nom_fichier: str, contenu: bytes) -> list[str]:
    r = _ligne(conn, style_id)
    nom = re.sub(r"[^A-Za-z0-9._-]+", "-", Path(nom_fichier or "image").name).strip("-.") or "image"
    if Path(nom).suffix.lower() not in (".png", ".jpg", ".jpeg", ".webp"):
        raise ValueError("image attendue (.png, .jpg, .webp)")
    dossier = dossier_style(r["code"]) / "inspiration"
    dossier.mkdir(parents=True, exist_ok=True)
    cible = dossier / nom
    i = 1
    while cible.exists():
        cible = dossier / f"{Path(nom).stem}-{i}{Path(nom).suffix}"
        i += 1
    cible.write_bytes(contenu)
    return [p.name for p in sorted(dossier.glob("*")) if p.is_file()]


def fichier_public(code: str, dossier: str, fichier: str) -> Path:
    """Chemin d'un fichier servi à l'interface, ou FileNotFoundError ; refuse toute traversée."""
    if dossier not in ("board", "inspiration") or not _FICHIER.match(fichier or "") or fichier.startswith("."):
        raise FileNotFoundError(fichier)
    chemin = (dossier_style(code) / dossier / fichier).resolve()
    if chemins.dossier_styles().resolve() not in chemin.parents or not chemin.is_file():
        raise FileNotFoundError(fichier)
    return chemin
