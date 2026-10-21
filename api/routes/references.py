"""Écran Références d'un lot : propositions par objet, choix, consigne, image donnée, lancement de la génération."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel, ConfigDict, Field

from api.dependances import Config, Db
from api.services import fabrication, references
from api.services import lots as lots_svc

router = APIRouter(prefix="/lots", tags=["references"])


class _Modele(BaseModel):
    model_config = ConfigDict(extra="ignore")


class PropositionsIn(_Modele):
    modele_id: int | None = None


class ChoixIn(_Modele):
    proposition_id: int


class ConsigneIn(_Modele):
    consigne: str = Field("", max_length=references.MAX_CONSIGNE * 2)


def _erreurs(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except lots_svc.LotIntrouvable as e:
        raise HTTPException(404, str(e)) from e
    except (references.ReferenceImpossible, fabrication.FabricationImpossible) as e:
        raise HTTPException(409, str(e)) from e
    except ValueError as e:
        raise HTTPException(422, str(e)) from e


@router.get("/{lot_id}/references")
def vue(lot_id: int, conn: Db, cfg: Config) -> dict:
    return _erreurs(references.vue, conn, cfg, lot_id)


@router.post("/{lot_id}/objets/{objet_id}/propositions", status_code=202)
def propositions(lot_id: int, objet_id: int, corps: PropositionsIn, conn: Db, cfg: Config) -> dict:
    """« 4 autres » (ou les 4 premières) ; avec modele_id : 4 images d'après l'image donnée."""
    tache_id = _erreurs(references.preparer, conn, cfg, lot_id, objet_id, corps.modele_id)
    return {"tache_id": tache_id, "objet": references.objet_vue(conn, lot_id, objet_id)}


@router.put("/{lot_id}/objets/{objet_id}/reference")
def choisir(lot_id: int, objet_id: int, corps: ChoixIn, conn: Db) -> dict:
    return _erreurs(references.choisir, conn, lot_id, objet_id, corps.proposition_id)


@router.put("/{lot_id}/objets/{objet_id}/consigne")
def consigne(lot_id: int, objet_id: int, corps: ConsigneIn, conn: Db) -> dict:
    return _erreurs(references.modifier_consigne, conn, lot_id, objet_id, corps.consigne)


@router.post("/{lot_id}/objets/{objet_id}/image", status_code=201)
async def image(lot_id: int, objet_id: int, conn: Db, fichier: Annotated[UploadFile, File()]) -> dict:
    contenu = await fichier.read()
    return _erreurs(references.ajouter_image, conn, lot_id, objet_id, fichier.filename or "image", contenu)


@router.post("/{lot_id}/objets/{objet_id}/rouvrir")
def rouvrir(lot_id: int, objet_id: int, conn: Db) -> dict:
    """« Choisir une autre version » (code) ou « une autre image » (IA) : un objet en échec revient aux Références."""
    return _erreurs(references.rouvrir, conn, lot_id, objet_id)


@router.post("/{lot_id}/lancer", status_code=202)
def lancer(lot_id: int, conn: Db, cfg: Config) -> dict:
    """« Lancer la génération 3D » depuis les Références."""
    return _erreurs(references.lancer, conn, cfg, lot_id)
