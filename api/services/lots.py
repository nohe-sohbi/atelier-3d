"""Lots (B1) : création, liste par état, étape calculée depuis les objets, duplication, validation du brief.

L'étape d'un lot est celle de son objet le moins avancé (correction 6) ; les objets réutilisés et hors
périmètre ne comptent pas. Rien n'est inventé : un lot sans objet est au Brief.
"""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime

from api import chemins, db
from api.adapters.meshy.base import CREDITS_3D, CREDITS_IMAGE, IMAGES_REFERENCE_PAR_OBJET
from api.services import evenements
from api.services.routage import VOIES_SANS_FABRICATION

RANG = {"brief": 1, "references": 2, "generation": 3, "finition": 3, "tests": 3, "rendus": 3, "revue": 4,
        "garde": 5, "rejete": 5, "archive": 5}
ETAPES = ("brief", "references", "generation", "revue")
LIBELLES_ETAPES = {"brief": "Brief", "references": "Références", "generation": "Génération", "revue": "Revue"}
GROUPES = ("tous", "en_cours", "termines", "brouillons")
CREDITS_PAR_OBJET_IA = CREDITS_3D + CREDITS_IMAGE * IMAGES_REFERENCE_PAR_OBJET  # 30 + 4 × 3 = 42


class LotIntrouvable(LookupError):
    pass


class BriefIncomplet(ValueError):
    pass


# --- lecture ---------------------------------------------------------------------

def _ligne(conn: sqlite3.Connection, lot_id: int) -> dict:
    r = db.une(conn, "SELECT * FROM lots WHERE id = ?", (lot_id,))
    if r is None:
        raise LotIntrouvable(f"lot {lot_id} introuvable")
    return r


def objets_du_lot(conn: sqlite3.Connection, lot_id: int) -> list[dict]:
    rows = db.toutes(conn, "SELECT * FROM objets WHERE lot_id = ? ORDER BY ordre, id", (lot_id,))
    for r in rows:
        r["dimensions"] = json.loads(r.pop("dimensions_json") or "null")
        r["pieces"] = db.toutes(conn, "SELECT id, ordre, nom, nature, type_objet, voie, generateur, etape FROM pieces "
                                      "WHERE objet_id = ? ORDER BY ordre, id", (r["id"],))
        r["materiaux"] = json.loads(r.pop("materiaux_json") or "[]")
        r["parametres"] = json.loads(r.pop("parametres_json") or "[]")
        r.pop("pieces_json", None)
        r["retire"] = bool(r["retire"])
        r["voie_forcee"] = bool(r["voie_forcee"])
    return rows


def _fabriques(objets: list[dict]) -> list[dict]:
    """Les objets qui comptent pour l'étape : retenus, et pas réutilisés ni hors périmètre."""
    return [o for o in objets if not o["retire"] and o["voie"] not in VOIES_SANS_FABRICATION]


def etape_du_lot(objets: list[dict]) -> int:
    """1 Brief, 2 Références, 3 Génération, 4 Revue, 5 Terminé : celle de l'objet le moins avancé."""
    fab = _fabriques(objets)
    if not fab:
        return 1
    rangs = [RANG.get(o["etape"], 1) for o in fab]
    return 5 if all(r == 5 for r in rangs) else min(rangs)


def _compter(objets: list[dict]) -> dict:
    fab = _fabriques(objets)
    return {
        "total": len([o for o in objets if not o["retire"]]),
        "fabriques": len(fab),
        "reutilises": len([o for o in objets if not o["retire"] and o["voie"] == "reutilise"]),
        "hors_perimetre": len([o for o in objets if not o["retire"] and o["voie"] == "hors_perimetre"]),
        "a_creer": len([o for o in fab if o["voie"] == "a_creer"]),
        "references_a_choisir": len([o for o in fab if o["etape"] == "references" and o["voie"] != "cc0"
                                     and o.get("reference_id") is None]),
        "references_choisies": len([o for o in fab if o["voie"] != "cc0" and (
            o.get("reference_id") is not None or RANG.get(o["etape"], 1) > 2)]),
        "cc0": len([o for o in fab if o["voie"] == "cc0"]),
        "en_generation": len([o for o in fab if RANG.get(o["etape"], 1) == 3]),
        "prets_revue": len([o for o in fab if o["etape"] == "revue"]),
        "gardes": len([o for o in fab if o["etape"] == "garde"]),
        "rejetes": len([o for o in fab if o["etape"] == "rejete"]),
        "finis": len([o for o in fab if RANG.get(o["etape"], 1) == 5]),
    }


def _pluriel(n: int, un: str, plusieurs: str) -> str:
    return f"{n} {plusieurs if n > 1 else un}"


def situation(lot: dict, objets: list[dict]) -> dict:
    """Étape, statut, ton, détail, lien et libellé d'action pour la liste des lots et l'en-tête."""
    etape = etape_du_lot(objets)
    c = _compter(objets)
    lid = lot["id"]
    if etape == 1:
        detail = "liste à valider" if c["total"] else "aucun objet pour l'instant"
        s = ("Brouillon", "idle", detail, f"/lots/{lid}/brief", "Reprendre")
    elif etape == 2:
        detail = (_pluriel(c["references_a_choisir"], "référence à choisir", "références à choisir")
                  if c["references_a_choisir"] else "références choisies : lance la génération")
        s = ("À toi", "warn", detail, f"/lots/{lid}/references", "Reprendre")
    elif etape == 3:
        s = ("En génération", "run", f"{c['fabriques'] - c['en_generation']} sur {c['fabriques']} générés",
             f"/lots/{lid}/generation", "Suivre")
    elif etape == 4:
        s = ("Revue prête", "accent", _pluriel(c["prets_revue"], "objet à juger", "objets à juger"), f"/lots/{lid}/revue", "Reprendre")
    else:
        rejets = "aucun jeté" if c["rejetes"] == 0 else _pluriel(c["rejetes"], "jeté", "jetés")
        s = ("Terminé", "good", f"{_pluriel(c['gardes'], 'gardé', 'gardés')}, {rejets}", f"/bibliotheque?lot={lid}", "Voir les assets")
    statut, ton, detail, lien, action = s
    return {"etape": etape, "libelle_etape": "Terminé" if etape == 5 else f"Étape {etape} sur 4 · {LIBELLES_ETAPES[ETAPES[etape - 1]]}",
            "statut": statut, "ton": ton, "detail": detail, "lien": lien, "action": action, "compteurs": c}


def ligne_etat(lot: dict, objets: list[dict], etape_courante: str) -> str:
    """La ligne sous le titre de l'en-tête, selon l'onglet ouvert (jamais de chiffre inventé)."""
    c = _compter(objets)
    n = _pluriel(c["total"], "objet", "objets")
    if etape_courante == "brief":
        return f"{n} · créé le {_date_courte(lot['cree_le'])}"
    if etape_courante == "references":
        sans = c["reutilises"] + c["hors_perimetre"] + c["cc0"]
        choisies = _pluriel(c["references_choisies"], "référence choisie", "références choisies")
        return f"{n} · {choisies} · {sans} sans référence (import, réutilisation)"
    if etape_courante == "generation":
        prets = _pluriel(c["prets_revue"] + c["finis"], "prêt", "prêts")
        return f"{n} · {prets} · {c['en_generation']} en cours · {_pluriel(c['reutilises'], 'réutilisé', 'réutilisés')}"
    return f"{n} · {_pluriel(c['gardes'], 'gardé', 'gardés')} · {c['prets_revue']} à décider · {_pluriel(c['reutilises'], 'réutilisé', 'réutilisés')}"


MOIS = ["janv.", "févr.", "mars", "avr.", "mai", "juin", "juil.", "août", "sept.", "oct.", "nov.", "déc."]


def _date_courte(iso: str) -> str:
    try:
        d = datetime.fromisoformat(iso)
    except ValueError:
        return iso
    return f"{d.day}{'er' if d.day == 1 else ''} {MOIS[d.month - 1]}"


def _style(conn: sqlite3.Connection, style_id: int | None) -> dict | None:
    if style_id is None:
        return None
    r = db.une(conn, "SELECT id, code, nom, version, racine_id FROM styles WHERE id = ?", (style_id,))
    return dict(r) if r else None


def resume(conn: sqlite3.Connection, lot: dict) -> dict:
    objets = objets_du_lot(conn, lot["id"])
    sit = situation(lot, objets)
    style = _style(conn, lot["style_id"])
    return {"id": lot["id"], "nom": lot["nom"], "theme": lot["theme"], "nb_objets": sit["compteurs"]["total"],
            "style": style, "etat": lot["etat"], "cree_le": lot["cree_le"], "maj_le": lot["maj_le"], **sit}


def groupe_de(etat: str) -> str:
    return {"brouillon": "brouillons", "en_cours": "en_cours", "termine": "termines", "archive": "termines"}.get(etat, "brouillons")


def lister(conn: sqlite3.Connection, groupe: str = "tous") -> dict:
    lots = [resume(conn, r) for r in db.toutes(conn, "SELECT * FROM lots ORDER BY maj_le DESC, id DESC")]
    compteurs = {g: 0 for g in GROUPES}
    compteurs["tous"] = len(lots)
    for lot in lots:
        compteurs[groupe_de(lot["etat"])] += 1
    if groupe != "tous":
        lots = [lot for lot in lots if groupe_de(lot["etat"]) == groupe]
    return {"compteurs": compteurs, "lots": lots}


def en_tete(conn: sqlite3.Connection, lot_id: int, etape_courante: str = "brief") -> dict:
    lot = _ligne(conn, lot_id)
    objets = objets_du_lot(conn, lot_id)
    sit = situation(lot, objets)
    style = _style(conn, lot["style_id"])
    version_plus_recente = None
    if style:
        r = db.une(conn, "SELECT id, code, version FROM styles WHERE racine_id = ? AND version > ? AND etat = 'valide' "
                         "ORDER BY version DESC LIMIT 1", (style["racine_id"], style["version"]))
        version_plus_recente = dict(r) if r else None
    etapes = []
    for i, cle in enumerate(ETAPES, start=1):
        etapes.append({"cle": cle, "libelle": LIBELLES_ETAPES[cle], "numero": i, "lien": f"/lots/{lot_id}/{cle}",
                       "atteinte": True if sit["etape"] >= 5 else i <= max(sit["etape"], 1),
                       "faite": i < sit["etape"]})
    return {"id": lot_id, "nom": lot["nom"], "theme": lot["theme"], "besoin": lot["besoin"], "style": style,
            "style_plus_recent": version_plus_recente, "etat": lot["etat"], "cree_le": lot["cree_le"], "maj_le": lot["maj_le"],
            "duplique_de_id": lot["duplique_de_id"], "credits_prevus": lot["credits_prevus"],
            "proposition_tache_id": lot["proposition_tache_id"], "nom_propose": lot["nom_propose"],
            "etape_courante": sit["etape"], "etapes": etapes, "ligne_etat": ligne_etat(lot, objets, etape_courante), **sit}


# --- écriture ----------------------------------------------------------------------

def _touch(conn: sqlite3.Connection, lot_id: int) -> None:
    conn.execute("UPDATE lots SET maj_le = ? WHERE id = ?", (db.maintenant(), lot_id))


def synchroniser_etat(conn: sqlite3.Connection, lot_id: int) -> str:
    """etat (brouillon, en_cours, termine) déduit de l'étape calculée ; relu par le badge du menu."""
    lot = _ligne(conn, lot_id)
    if lot["etat"] == "archive":
        return "archive"
    etape = etape_du_lot(objets_du_lot(conn, lot_id))
    etat = "brouillon" if etape == 1 else "termine" if etape == 5 else "en_cours"
    conn.execute("UPDATE lots SET etat = ? WHERE id = ?", (etat, lot_id))
    return etat


def style_par_defaut(conn: sqlite3.Connection) -> int | None:
    r = db.une(conn, "SELECT id FROM styles WHERE etat = 'valide' ORDER BY id LIMIT 1") or db.une(conn, "SELECT id FROM styles ORDER BY id LIMIT 1")
    return r["id"] if r else None


def creer(conn: sqlite3.Connection, nom: str = "", theme: str = "", besoin: str = "", style_id: int | None = None) -> dict:
    """Un lot vide, au Brief, avec son dossier lots/<id>/ (audit : « Nouveau lot crée un lot vide »)."""
    maintenant = db.maintenant()
    with db.transaction(conn):
        lot_id = db.inserer(conn, "lots", {
            "nom": nom.strip(), "theme": theme.strip(), "besoin": besoin.strip(), "direction": "",
            "style_id": style_id if style_id is not None else style_par_defaut(conn),
            "etat": "brouillon", "cree_le": maintenant, "maj_le": maintenant, "dossier": "",
        })
        dossier = chemins.dossier_lots() / str(lot_id)
        dossier.mkdir(parents=True, exist_ok=True)
        conn.execute("UPDATE lots SET dossier = ? WHERE id = ?", (f"lots/{lot_id}", lot_id))
        evenements.ecrire(conn, "lot_cree", f"Lot {nom.strip() or lot_id} créé", niveau="info", lot_id=lot_id)
    return en_tete(conn, lot_id)


CHAMPS_MODIFIABLES = ("nom", "theme", "besoin", "style_id")


def modifier(conn: sqlite3.Connection, lot_id: int, champs: dict) -> dict:
    _ligne(conn, lot_id)
    for k, v in champs.items():
        if k not in CHAMPS_MODIFIABLES or v is None:
            continue
        if k == "style_id" and db.une(conn, "SELECT 1 FROM styles WHERE id = ?", (v,)) is None:
            raise ValueError(f"style {v} introuvable")
        conn.execute(f"UPDATE lots SET {k} = ? WHERE id = ?", (v.strip() if isinstance(v, str) else v, lot_id))
    _touch(conn, lot_id)
    return en_tete(conn, lot_id)


def dupliquer(conn: sqlite3.Connection, lot_id: int) -> dict:
    """Copie le brief et les choix (objets retenus, voies forcées), sans essai ni tâche."""
    lot = _ligne(conn, lot_id)
    objets = objets_du_lot(conn, lot_id)
    maintenant = db.maintenant()
    with db.transaction(conn):
        nouveau = db.inserer(conn, "lots", {
            "nom": f"{lot['nom']} (copie)" if lot["nom"] else "", "theme": lot["theme"], "besoin": lot["besoin"],
            "direction": lot["direction"], "style_id": lot["style_id"], "etat": "brouillon", "cree_le": maintenant,
            "maj_le": maintenant, "dossier": "", "duplique_de_id": lot_id, "nom_propose": lot["nom_propose"],
        })
        (chemins.dossier_lots() / str(nouveau)).mkdir(parents=True, exist_ok=True)
        conn.execute("UPDATE lots SET dossier = ? WHERE id = ?", (f"lots/{nouveau}", nouveau))
        for o in objets:
            oid = db.inserer(conn, "objets", {
                "lot_id": nouveau, "nom": o["nom"], "type_objet": o["type_objet"], "description": o["description"],
                "categorie": o["categorie"], "nature": o["nature"], "dimensions_json": json.dumps(o["dimensions"]),
                "voie": o["voie"], "voie_forcee": 1 if o["voie_forcee"] else 0, "raison_voie": o["raison_voie"],
                "regle_id": o["regle_id"], "generateur": o["generateur"], "etape": "brief", "retire": 1 if o["retire"] else 0,
                "reutilise_asset_id": o["reutilise_asset_id"], "symetrique": o["symetrique"], "famille": o["famille"],
                "materiaux_json": json.dumps(o["materiaux"], ensure_ascii=False),
                "parametres_json": json.dumps(o["parametres"], ensure_ascii=False), "cc0_ref": o["cc0_ref"], "ordre": o["ordre"],
            })
            for p in o["pieces"]:
                db.inserer(conn, "pieces", {"objet_id": oid, "ordre": p["ordre"], "nom": p["nom"], "nature": p["nature"],
                                            "type_objet": p["type_objet"], "voie": p["voie"], "generateur": p["generateur"],
                                            "etape": "brief"})
        evenements.ecrire(conn, "lot_duplique", f"Lot {lot['nom'] or lot_id} dupliqué", niveau="info", lot_id=nouveau)
    return en_tete(conn, nouveau)


def estimation_credits(objets: list[dict]) -> int:
    """Voie IA ou mixte : 3D texturée + 4 images de référence. Code : variantes Blender gratuites (correction 1)."""
    return sum(CREDITS_PAR_OBJET_IA for o in objets if not o["retire"] and o["voie"] in ("ia", "mixte"))


def resume_brief(objets: list[dict]) -> dict:
    retenus = [o for o in objets if not o["retire"]]
    return {
        "retenus": len(retenus),
        "a_fabriquer": len([o for o in retenus if o["voie"] in ("code", "ia", "mixte", "a_creer")]),
        "cc0": len([o for o in retenus if o["voie"] == "cc0"]),
        "reutilises": len([o for o in retenus if o["voie"] == "reutilise"]),
        "hors_perimetre": len([o for o in retenus if o["voie"] == "hors_perimetre"]),
        "a_creer": len([o for o in retenus if o["voie"] == "a_creer"]),
        "credits_estimes": estimation_credits(objets),
        "credits_par_objet_ia": CREDITS_PAR_OBJET_IA,
    }


def retenir_objet(conn: sqlite3.Connection, lot_id: int, objet_id: int, retenu: bool | None = None,
                  voie: str | None = None) -> dict:
    """Case à cocher (retire l'objet du lot) et choix manuel de la voie (« Passer en voie IA »)."""
    o = db.une(conn, "SELECT * FROM objets WHERE id = ? AND lot_id = ?", (objet_id, lot_id))
    if o is None:
        raise LotIntrouvable(f"objet {objet_id} introuvable dans le lot {lot_id}")
    if retenu is not None:
        conn.execute("UPDATE objets SET retire = ? WHERE id = ?", (0 if retenu else 1, objet_id))
    if voie is not None:
        if voie not in ("ia", "code", "a_creer"):
            raise ValueError("voie choisie à la main : ia, code ou a_creer")
        conn.execute("UPDATE objets SET voie = ?, voie_forcee = 1, raison_voie = ?, generateur = ? WHERE id = ?",
                     (voie, "Voie choisie à la main", "meshy" if voie == "ia" else o["generateur"] if voie == "code" else None, objet_id))
    _touch(conn, lot_id)
    synchroniser_etat(conn, lot_id)
    return next(x for x in objets_du_lot(conn, lot_id) if x["id"] == objet_id)


def valider_brief(conn: sqlite3.Connection, lot_id: int) -> dict:
    """« Générer les références » : les objets retenus passent à l'étape Références ; les réutilisés sont
    déjà faits ; les hors périmètre sont retirés. Refus s'il reste un objet « À créer »."""
    lot = _ligne(conn, lot_id)
    objets = objets_du_lot(conn, lot_id)
    retenus = [o for o in objets if not o["retire"]]
    if not retenus:
        raise BriefIncomplet("aucun objet retenu : demande une liste à Claude et coche ce que tu veux fabriquer")
    a_creer = [o["nom"] for o in retenus if o["voie"] == "a_creer"]
    if a_creer:
        raise BriefIncomplet("générateur à écrire avant de lancer : " + ", ".join(a_creer)
                             + " (prépare la demande pour Claude Code, ou passe l'objet en voie IA)")
    with db.transaction(conn):
        for o in retenus:
            if o["voie"] == "hors_perimetre":
                conn.execute("UPDATE objets SET retire = 1 WHERE id = ?", (o["id"],))
            elif o["voie"] == "reutilise":
                conn.execute("UPDATE objets SET etape = 'garde' WHERE id = ?", (o["id"],))
            elif o["etape"] == "brief":
                conn.execute("UPDATE objets SET etape = 'references' WHERE id = ?", (o["id"],))
                conn.execute("UPDATE pieces SET etape = 'references' WHERE objet_id = ?", (o["id"],))
        conn.execute("UPDATE lots SET credits_prevus = ? WHERE id = ?", (estimation_credits(objets), lot_id))
        _touch(conn, lot_id)
        evenements.ecrire(conn, "brief_valide", f"Brief validé : {lot['nom'] or lot_id}",
                          f"{len(retenus)} objets retenus.", niveau="info", lot_id=lot_id)
    synchroniser_etat(conn, lot_id)
    return en_tete(conn, lot_id, "references")


def estimation_appliquer_style(conn: sqlite3.Connection, lot_id: int, style_id: int) -> dict:
    """Correction 11 : « Appliquer la vN » refait les objets code gratuitement et chiffre les objets IA."""
    _ligne(conn, lot_id)
    if db.une(conn, "SELECT 1 FROM styles WHERE id = ?", (style_id,)) is None:
        raise ValueError(f"style {style_id} introuvable")
    objets = [o for o in objets_du_lot(conn, lot_id) if not o["retire"] and RANG.get(o["etape"], 1) >= 3]
    code = [o["nom"] for o in objets if o["voie"] == "code"]
    ia = [o["nom"] for o in objets if o["voie"] in ("ia", "mixte")]
    return {"objets_code": code, "objets_ia": ia, "credits": len(ia) * CREDITS_3D,
            "lancement_possible": False,
            "raison": "Refaire les objets arrive avec la fabrication (étapes 5 et 7 du plan)"}
