"""Écran Styles : lister, créer, modifier, versionner un style ; planche de référence ; validation."""
from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel, ConfigDict, Field

from api.adapters import get_meshy
from api.dependances import Config, Db
from api.services import style_yaml, styles

router = APIRouter(prefix="/styles", tags=["styles"])


class _Modele(BaseModel):
    model_config = ConfigDict(extra="ignore")


class StyleIn(_Modele):
    nom: str = Field(min_length=1, max_length=120)
    code: str | None = Field(None, max_length=80)
    description: str = Field("", max_length=2000)
    direction: Literal["stylise", "semi_realiste"] | None = None
    theme: str | None = Field(None, max_length=12)
    palette: dict[str, str] = Field(min_length=8, max_length=12)
    budgets_depuis: int | None = None
    budgets: dict[str, int] | None = None
    textures_px: dict[str, int] | None = None
    texel_density: float | None = Field(None, gt=0)
    tolerances: dict[str, float] | None = None
    dimensions_m: dict[str, list[float]] | None = None


class ModifIn(_Modele):
    nom: str | None = Field(None, min_length=1, max_length=120)
    description: str | None = Field(None, max_length=2000)
    palette: dict[str, str] | None = None
    materiaux: dict[str, dict] | None = None
    budgets_tris: dict[str, int] | None = None
    textures_px: dict[str, int] | None = None
    texel_density_px_per_m: float | None = Field(None, gt=0)
    tolerances: dict[str, float] | None = None
    dimensions_m: dict[str, list[float]] | None = None
    objets_planche: list[str] | None = None
    prompts_reference: dict[str, str] | None = None


class VersionIn(_Modele):
    note: str = Field("", max_length=500)


class ImageIn(_Modele):
    gardee: bool


def _erreurs(fn, *args):
    try:
        return fn(*args)
    except styles.StyleIntrouvable as e:
        raise HTTPException(404, str(e)) from e
    except (styles.ConflitCode, styles.StyleUtilise, styles.AucuneImageGardee) as e:
        raise HTTPException(409, str(e)) from e
    except (style_yaml.StyleInvalide, ValueError) as e:
        raise HTTPException(422, f"Style invalide : {e}") from e


@router.get("")
def lister(conn: Db) -> dict:
    return {"styles": styles.lister(conn)}


@router.get("/estimation-planche")
def estimation_planche(cfg: Config) -> dict:
    """Tarif de l'adaptateur Meshy (réel ou simulé) : l'interface n'affiche que ces chiffres."""
    meshy = get_meshy(cfg)
    return {"credits_par_image": meshy.credits_image, "images_max": styles.NB_IMAGES_PLANCHE,
            "simule": meshy.mode == "simule"}


@router.get("/{style_id}")
def lire(style_id: int, conn: Db) -> dict:
    return _erreurs(styles.detail, conn, style_id)


@router.post("", status_code=201)
def creer(style: StyleIn, conn: Db) -> dict:
    r = _erreurs(styles.creer, conn, style.model_dump())
    return styles.detail(conn, r["id"])


@router.put("/{style_id}")
def modifier(style_id: int, champs: ModifIn, conn: Db) -> dict:
    return _erreurs(styles.modifier, conn, style_id, champs.model_dump(exclude_none=True))


@router.post("/{style_id}/versions", status_code=201)
def dupliquer(style_id: int, corps: VersionIn, conn: Db) -> dict:
    return _erreurs(styles.dupliquer, conn, style_id, corps.note)


@router.post("/{style_id}/planche", status_code=202)
def planche(style_id: int, conn: Db, cfg: Config) -> dict:
    tache_id, n = _erreurs(styles.demander_planche, conn, cfg, style_id)
    return {"tache_id": tache_id, "credits_estimes": n * get_meshy(cfg).credits_image}


@router.post("/{style_id}/planche/{image_id}/refaire", status_code=202)
def refaire(style_id: int, image_id: int, conn: Db, cfg: Config) -> dict:
    tache_id, n = _erreurs(styles.demander_planche, conn, cfg, style_id, image_id)
    return {"tache_id": tache_id, "credits_estimes": n * get_meshy(cfg).credits_image}


@router.put("/{style_id}/planche/{image_id}")
def garder(style_id: int, image_id: int, corps: ImageIn, conn: Db) -> dict:
    return _erreurs(styles.garder_image, conn, style_id, image_id, corps.gardee)


@router.post("/{style_id}/valider")
def valider(style_id: int, conn: Db) -> dict:
    return _erreurs(styles.valider, conn, style_id)


@router.post("/{style_id}/inspirations", status_code=201)
async def inspirations(style_id: int, conn: Db, fichiers: Annotated[list[UploadFile], File()]) -> dict:
    noms: list[str] = []
    for f in fichiers:
        contenu = await f.read()
        if len(contenu) > 20 * 1024 * 1024:
            raise HTTPException(413, f"{f.filename} dépasse 20 Mo")
        noms = _erreurs(styles.ajouter_inspiration, conn, style_id, f.filename or "image", contenu)
    return {"inspirations": noms}
