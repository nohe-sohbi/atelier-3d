"""Écran Réglages : lecture/écriture de config.local.yaml, tests de connexion."""
from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from api import config as cfgmod
from api import db
from api.adapters import get_claude, get_comfyui, get_itchio, get_meshy
from api.dependances import get_config, get_db
from api.services import couts, evenements, outils

router = APIRouter(prefix="/reglages", tags=["reglages"])

Mode = Literal["simule", "reel"]


class _Modele(BaseModel):
    model_config = ConfigDict(extra="ignore")


class MeshyIn(_Modele):
    mode: Mode = "simule"
    cle_api: str | None = ""
    credits_mensuels: int = Field(1000, ge=0, le=1_000_000)
    renouvellement_jour: Literal[1, 15] = 1
    alerte_pct: Literal[80, 90, 0] = 80


class ClaudeIn(_Modele):
    mode: Mode = "simule"
    cle_api: str | None = ""
    modele: Literal["claude-sonnet-5-5", "claude-haiku-5-5"] = "claude-sonnet-5-5"
    plafond_mensuel_usd: float = Field(5.0, ge=0, le=10_000)


class ComfyUIIn(_Modele):
    mode: Mode = "simule"
    url: str = Field("http://127.0.0.1:8188", pattern=r"^https?://\S+$")


class ItchioIn(_Modele):
    mode: Mode = "simule"
    cle_api: str | None = ""
    compte: str = Field("", max_length=100, pattern=r"^[A-Za-z0-9_.-]*$")
    canal: str = Field("html", min_length=1, max_length=50, pattern=r"^[A-Za-z0-9_-]+$")


class ServicesIn(_Modele):
    meshy: MeshyIn = MeshyIn()
    claude: ClaudeIn = ClaudeIn()
    comfyui: ComfyUIIn = ComfyUIIn()
    itchio: ItchioIn = ItchioIn()


class BlenderIn(_Modele):
    chemin: str = ""
    python_bpy: str = ""


class CheminIn(_Modele):
    chemin: str = ""


class OutilsIn(_Modele):
    blender: BlenderIn = BlenderIn()
    gltf_validator: CheminIn = CheminIn(chemin="gltf_validator")
    butler: CheminIn = CheminIn(chemin="butler")


class BibliothequeIn(_Modele):
    dossier: str = Field("assets", min_length=1, max_length=200)
    purge_rejets_jours: int = Field(30, ge=0, le=3650)


class FilesIn(_Modele):
    gpu: int = Field(1, ge=1, le=8)
    meshy: int = Field(3, ge=1, le=10)
    blender: int = Field(2, ge=1, le=8)
    relances_max: int = Field(3, ge=0, le=5)


class NotificationsIn(_Modele):
    app: bool = True
    bureau: bool = False


class ReglagesIn(_Modele):
    services: ServicesIn
    outils: OutilsIn
    bibliotheque: BibliothequeIn
    files: FilesIn
    notifications: NotificationsIn


# --- état (solde Meshy, dépense Claude) ----------------------------------

def _etat(conn, cfg: dict) -> dict:
    solde = None
    try:
        s = get_meshy(cfg).solde()
        solde = {"restants": int(s["restants"]), "total": int(s["total"]), "lu_le": db.maintenant()}
    except Exception as e:
        titre = "Solde Meshy illisible"
        if not evenements.recent_existe(conn, "meshy_injoignable", minutes=10):
            evenements.ecrire(conn, "meshy_injoignable", titre, f"{type(e).__name__}: {e}"[:300],
                              niveau="alerte", lien="/reglages")
    return {"meshy_solde": solde, "claude_depense_mois": couts.depense_claude_mois(conn)}


def _reponse(conn, cfg: dict) -> dict:
    return {**cfgmod.vers_reglages(cfg), "etat": _etat(conn, cfg)}


@router.get("")
def lire_reglages(conn=Depends(get_db), cfg: dict = Depends(get_config)) -> dict:
    return _reponse(conn, cfg)


@router.put("")
def ecrire_reglages(reglages: ReglagesIn, conn=Depends(get_db), cfg: dict = Depends(get_config)) -> dict:
    nouveau = cfgmod.appliquer_reglages(cfg, reglages.model_dump(exclude_unset=False))
    cfgmod.enregistrer(nouveau)
    evenements.ecrire(conn, "reglages_enregistres", "Réglages enregistrés", niveau="debug")
    return _reponse(conn, cfgmod.charger())


# --- tests de connexion ----------------------------------------------------

Service = Literal["meshy", "claude", "comfyui", "itchio", "blender", "gltf_validator", "butler"]


@router.post("/tester/{service}")
def tester(service: Service, conn=Depends(get_db), cfg: dict = Depends(get_config)) -> dict:
    try:
        if service == "meshy":
            res = get_meshy(cfg).tester_connexion()
        elif service == "claude":
            res = get_claude(cfg).tester_connexion()
        elif service == "comfyui":
            res = get_comfyui(cfg).tester_connexion()
        elif service in ("itchio", "butler"):
            res = get_itchio(cfg).tester_butler()
        elif service == "blender":
            res = outils.tester_blender(cfg)
        elif service == "gltf_validator":
            res = outils.tester_gltf_validator(cfg)
        else:  # pragma: no cover
            raise HTTPException(404, f"service inconnu : {service}")
    except HTTPException:
        raise
    except Exception as e:
        res = {"ok": False, "etat": "Erreur", "message": f"{type(e).__name__}: {e}"[:300], "details": {}}
    if not res.get("ok"):
        evenements.ecrire(conn, "test_connexion_echec", f"Test {service} : {res.get('message', '')}"[:200],
                          niveau="alerte", lien="/reglages")
    return res
