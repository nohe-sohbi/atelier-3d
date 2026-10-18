"""Lecture et écriture de config.local.yaml.

Valeurs par défaut = config.local.example.yaml. Les clés API ne sortent jamais d'ici en clair :
`vers_reglages()` les remplace par un aperçu (`••••ab12`).
"""
from __future__ import annotations

import copy
import threading
from typing import Any

import yaml

from api import chemins

MODES = ("simule", "reel")
MODELES_CLAUDE = ("claude-sonnet-5-5", "claude-haiku-5-5")
RENOUVELLEMENT_JOURS = (1, 15)
ALERTES_PCT = (80, 90, 0)
FILES = ("gpu", "meshy", "blender")
LIMITE_FILE_API = 4
_verrou = threading.Lock()

EN_TETE = (
    "# Réglages locaux d'Atelier 3D : clés d'API et chemins de ta machine.\n"
    "# Fichier ignoré par Git ; modifié par l'écran Réglages.\n"
)


def _fusionner(defaut: dict, surcharge: dict) -> dict:
    out = copy.deepcopy(defaut)
    for k, v in (surcharge or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _fusionner(out[k], v)
        else:
            out[k] = v
    return out


def defauts() -> dict:
    with open(chemins.chemin_config_exemple(), encoding="utf-8") as f:
        return yaml.safe_load(f) or {}



def charger() -> dict:
    """Config complète (défauts + fichier local). Lue à chaque appel : toujours à jour."""
    chemin = chemins.chemin_config()
    local: dict = {}
    if chemin.exists():
        with open(chemin, encoding="utf-8") as f:
            local = yaml.safe_load(f) or {}
    return _fusionner(defauts(), local)


def enregistrer(cfg: dict) -> None:
    chemin = chemins.chemin_config()
    chemin.parent.mkdir(parents=True, exist_ok=True)
    with _verrou:
        tmp = chemin.with_suffix(".yaml.tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(EN_TETE)
            yaml.safe_dump(cfg, f, allow_unicode=True, sort_keys=False)
        tmp.replace(chemin)


def apercu_cle(cle: str | None) -> str:
    cle = (cle or "").strip()
    if not cle:
        return ""
    return "••••" + cle[-4:] if len(cle) > 4 else "••••"


def service(cfg: dict, nom: str) -> dict:
    return cfg.get("services", {}).get(nom, {})


def mode(cfg: dict, nom: str) -> str:
    return "reel" if service(cfg, nom).get("mode") == "reel" else "simule"


def limites_files(cfg: dict) -> dict[str, int]:
    files = cfg.get("files", {})
    out = {f: max(1, int(files.get(f, 1))) for f in FILES}
    out["api"] = LIMITE_FILE_API
    return out


def relances_max(cfg: dict) -> int:
    return max(0, int(cfg.get("files", {}).get("relances_max", 3)))


# --- Contrat de l'écran Réglages --------------------------------------------

def vers_reglages(cfg: dict) -> dict[str, Any]:
    """Structure renvoyée par GET /api/reglages (sans "etat"). Jamais de clé en clair."""
    s = cfg.get("services", {})
    meshy, claude, comfy, itch = (s.get(k, {}) for k in ("meshy", "claude", "comfyui", "itchio"))
    outils = cfg
    return {
        "services": {
            "meshy": {
                "mode": mode(cfg, "meshy"),
                "cle_api_definie": bool(meshy.get("cle_api")),
                "cle_api_apercu": apercu_cle(meshy.get("cle_api")),
                "credits_mensuels": int(meshy.get("credits_mensuels", 1000)),
                "renouvellement_jour": int(meshy.get("renouvellement_jour", 1)),
                "alerte_pct": int(meshy.get("alerte_pct", 80)),
            },
            "claude": {
                "mode": mode(cfg, "claude"),
                "cle_api_definie": bool(claude.get("cle_api")),
                "cle_api_apercu": apercu_cle(claude.get("cle_api")),
                "modele": str(claude.get("modele", MODELES_CLAUDE[0])),
                "plafond_mensuel_usd": float(claude.get("plafond_mensuel_usd", 5.0)),
            },
            "comfyui": {
                "mode": mode(cfg, "comfyui"),
                "url": str(comfy.get("url", "http://127.0.0.1:8188")),
            },
            "itchio": {
                "mode": mode(cfg, "itchio"),
                "cle_api_definie": bool(itch.get("cle_api")),
                "cle_api_apercu": apercu_cle(itch.get("cle_api")),
                "compte": str(itch.get("compte", "") or ""),
                "canal": str(itch.get("canal", "assets") or "assets"),
            },
        },
        "outils": {
            "blender": {
                "chemin": str(outils.get("blender", {}).get("chemin", "") or ""),
            },
            "gltf_validator": {"chemin": str(outils.get("gltf_validator", {}).get("chemin", "") or "")},
            "butler": {"chemin": str(outils.get("butler", {}).get("chemin", "") or "")},
        },
        "bibliotheque": {
            "dossier": str(cfg.get("bibliotheque", {}).get("dossier", "assets")),
            "purge_rejets_jours": int(cfg.get("bibliotheque", {}).get("purge_rejets_jours", 30)),
        },
        "files": {
            **{f: int(cfg.get("files", {}).get(f, 1)) for f in FILES},
            "relances_max": relances_max(cfg),
        },
        "notifications": {
            "app": bool(cfg.get("notifications", {}).get("app", True)),
            "bureau": bool(cfg.get("notifications", {}).get("bureau", False)),
        },
    }


_ABSENT = object()


def appliquer_reglages(cfg: dict, reglages: dict) -> dict:
    """Reporte un PUT /api/reglages (déjà validé) dans la config.

    Pour chaque service, `cle_api` : chaîne non vide → remplace ; absente ou "" → inchangée ;
    None → effacée.
    """
    cfg = copy.deepcopy(cfg)
    services = cfg.setdefault("services", {})
    for nom, champs in reglages.get("services", {}).items():
        cible = services.setdefault(nom, {})
        for k, v in champs.items():
            if k == "cle_api":
                if v is None:
                    cible["cle_api"] = ""
                elif isinstance(v, str) and v.strip():
                    cible["cle_api"] = v.strip()
            elif k not in ("cle_api_definie", "cle_api_apercu"):
                cible[k] = v
    for outil, champs in reglages.get("outils", {}).items():
        cfg.setdefault(outil, {}).update(champs)
    for section in ("bibliotheque", "files", "notifications"):
        if section in reglages:
            cfg.setdefault(section, {}).update(reglages[section])
    return cfg
