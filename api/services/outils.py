"""Outils sur la machine : Blender, glTF-Validator. Chaque test lance l'exécutable et lit sa version."""
from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

from api.adapters._commun import resultat_test


def _executable(chemin: str) -> str | None:
    chemin = (chemin or "").strip()
    if not chemin:
        return None
    if Path(chemin).exists():
        return chemin
    return shutil.which(chemin)


def _lancer(args: list[str], timeout: float) -> subprocess.CompletedProcess:
    return subprocess.run(args, capture_output=True, text=True, timeout=timeout, check=False)


def detecter_blender() -> str | None:
    """Chemin de Blender trouvé sur cette machine, ou None. Sert au premier lancement (dev.py)."""
    return shutil.which("blender")


def blender_disponible(cfg: dict) -> bool:
    return _executable(cfg.get("blender", {}).get("chemin", "")) is not None


def tester_blender(cfg: dict) -> dict:
    """`<chemin> -b --version`."""
    b = cfg.get("blender", {})
    exe = _executable(b.get("chemin", ""))
    if exe is None:
        if b.get("chemin"):
            return resultat_test(False, "Erreur", "Blender introuvable : vérifie le chemin de l'exécutable")
        return resultat_test(False, "Erreur", "Aucun chemin Blender renseigné")
    try:
        r = _lancer([exe, "-b", "--version"], 90)
    except subprocess.TimeoutExpired:
        return resultat_test(False, "Erreur", "Blender ne répond pas (délai dépassé)")
    except OSError as e:
        return resultat_test(False, "Erreur", f"Blender : {type(e).__name__}")
    sortie = (r.stdout + "\n" + r.stderr)
    m = re.search(r"Blender\s+(\d+\.\d+(?:\.\d+)?\s*(?:LTS)?)", sortie)
    if r.returncode != 0 or not m:
        return resultat_test(False, "Erreur", f"Blender a répondu sans version lisible (code {r.returncode})",
                             {"sortie": sortie.strip()[-300:]})
    version = m.group(1).strip()
    return resultat_test(True, "Détecté", f"Blender {version}", {"version": version, "chemin": exe})


def tester_gltf_validator(cfg: dict) -> dict:
    """`<chemin> --version` (ou la commande gltf_validator du PATH)."""
    chemin = cfg.get("gltf_validator", {}).get("chemin", "") or "gltf_validator"
    exe = _executable(chemin)
    if exe is None:
        return resultat_test(False, "Erreur", f"glTF-Validator introuvable ({chemin})")
    try:
        r = _lancer([exe, "--version"], 30)
    except subprocess.TimeoutExpired:
        return resultat_test(False, "Erreur", "glTF-Validator ne répond pas (délai dépassé)")
    except OSError as e:
        return resultat_test(False, "Erreur", f"glTF-Validator : {type(e).__name__}")
    sortie = (r.stdout + r.stderr).strip()
    if r.returncode != 0 and not sortie:
        return resultat_test(False, "Erreur", f"glTF-Validator a échoué (code {r.returncode})")
    m = re.search(r"(\d+\.\d+\.\d+)", sortie)
    version = m.group(1) if m else sortie.splitlines()[0][:40] if sortie else "?"
    return resultat_test(True, "Détecté", f"glTF-Validator {version}", {"version": version, "chemin": exe})
