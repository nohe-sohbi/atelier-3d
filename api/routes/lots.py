"""Écrans Lots et Brief : lots, objets proposés, voies, demande pour Claude Code, validation du brief."""
from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field

from api.dependances import Config, Db
from api.services import brief, demandes
from api.services import lots as lots_svc

router = APIRouter(prefix="/lots", tags=["lots"])
Groupe = Literal["tous", "en_cours", "termines", "brouillons"]
Etape = Literal["brief", "references", "generation", "revue"]


class _Modele(BaseModel):
    model_config = ConfigDict(extra="ignore")


class LotIn(_Modele):
    nom: str = Field("", max_length=120)
    theme: str = Field("", max_length=80)
    besoin: str = Field("", max_length=4000)
    style_id: int | None = None


class LotModif(_Modele):
    nom: str | None = Field(None, max_length=120)
    theme: str | None = Field(None, max_length=80)
    besoin: str | None = Field(None, max_length=4000)
    style_id: int | None = None


class ObjetModif(_Modele):
    retenu: bool | None = None
    voie: Literal["ia", "code", "a_creer"] | None = None


def _erreurs(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except lots_svc.LotIntrouvable as e:
        raise HTTPException(404, str(e)) from e
    except lots_svc.BriefIncomplet as e:
        raise HTTPException(409, str(e)) from e
    except ValueError as e:
        raise HTTPException(422, str(e)) from e


@router.get("")
def lister(conn: Db, groupe: Groupe = "tous") -> dict:
    return lots_svc.lister(conn, groupe)


@router.post("", status_code=201)
def creer(lot: LotIn, conn: Db) -> dict:
    return _erreurs(lots_svc.creer, conn, lot.nom, lot.theme, lot.besoin, lot.style_id)


@router.get("/{lot_id}")
def lire(lot_id: int, conn: Db, etape: Etape = "brief") -> dict:
    return _erreurs(lots_svc.en_tete, conn, lot_id, etape)


@router.patch("/{lot_id}")
def modifier(lot_id: int, champs: LotModif, conn: Db) -> dict:
    return _erreurs(lots_svc.modifier, conn, lot_id, champs.model_dump(exclude_none=True))


@router.post("/{lot_id}/dupliquer", status_code=201)
def dupliquer(lot_id: int, conn: Db) -> dict:
    return _erreurs(lots_svc.dupliquer, conn, lot_id)


@router.post("/{lot_id}/proposition", status_code=202)
def proposition(lot_id: int, conn: Db, cfg: Config) -> dict:
    tache_id = _erreurs(brief.proposer, conn, cfg, lot_id)
    return {"tache_id": tache_id}


def _objets(conn, lot_id: int) -> dict:
    lot = lots_svc._ligne(conn, lot_id)
    objets = lots_svc.objets_du_lot(conn, lot_id)
    tache = None
    if lot["proposition_tache_id"]:
        from api.services import taches
        try:
            t = taches.lire_tache(conn, lot["proposition_tache_id"])
            tache = {"id": t["id"], "etat": t["etat"], "erreur": t["erreur"]}
        except taches.TacheIntrouvable:
            tache = None
    simule = any(True for c in conn.execute(
        "SELECT detail FROM couts WHERE service = 'claude' AND detail LIKE ? AND detail LIKE '%\"simule\": true%'",
        (f'%"lot_id": {lot_id}%',)))
    return {"lot_id": lot_id, "objets": objets, "resume": lots_svc.resume_brief(objets), "proposition": tache,
            "simule": bool(simule) and bool(objets)}


@router.get("/{lot_id}/objets")
def objets(lot_id: int, conn: Db) -> dict:
    return _erreurs(_objets, conn, lot_id)


@router.patch("/{lot_id}/objets/{objet_id}")
def modifier_objet(lot_id: int, objet_id: int, corps: ObjetModif, conn: Db) -> dict:
    _erreurs(lots_svc.retenir_objet, conn, lot_id, objet_id, corps.retenu, corps.voie)
    return _erreurs(_objets, conn, lot_id)


@router.get("/{lot_id}/objets/{objet_id}/demande")
def demande(lot_id: int, objet_id: int, conn: Db) -> dict:
    return _erreurs(demandes.etat, conn, lot_id, objet_id)


@router.post("/{lot_id}/objets/{objet_id}/demande", status_code=201)
def ecrire_demande(lot_id: int, objet_id: int, conn: Db) -> dict:
    return _erreurs(demandes.ecrire, conn, lot_id, objet_id)


@router.post("/{lot_id}/valider-brief")
def valider_brief(lot_id: int, conn: Db) -> dict:
    return _erreurs(lots_svc.valider_brief, conn, lot_id)


@router.get("/{lot_id}/appliquer-style")
def appliquer_style(lot_id: int, conn: Db, style_id: int = Query(...)) -> dict:
    return _erreurs(lots_svc.estimation_appliquer_style, conn, lot_id, style_id)
