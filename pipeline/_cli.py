"""Petits helpers partagés par les scripts du pipeline (sans bpy).

- lecture des arguments passés après `--` (convention Blender : `blender -b -P script.py -- args`) ;
- lecture de config.local.yaml sous forme de dictionnaire, sans dépendre de api/ ;
- racine du dépôt.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import yaml


def racine_projet() -> Path:
    """Dossier du dépôt (parent de pipeline/)."""
    return Path(__file__).resolve().parent.parent


def args_apres_double_tiret(argv: list[str] | None = None) -> list[str]:
    """Les arguments situés après `--` ; tous les arguments s'il n'y a pas de `--`.

    Blender passe ses propres options avant `--` ; un script lancé directement par
    `python script.py -- args` suit la même convention.
    """
    argv = list(sys.argv if argv is None else argv)
    if "--" in argv:
        return argv[argv.index("--") + 1:]
    return argv[1:]


def charger_config(chemin: str | Path | None = None) -> dict[str, Any]:
    """Lit config.local.yaml (ou, à défaut, config.local.example.yaml) en dictionnaire."""
    candidats = [Path(chemin)] if chemin else [
        racine_projet() / "config.local.yaml",
        racine_projet() / "config.local.example.yaml",
    ]
    for c in candidats:
        if c.is_file():
            with c.open("r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
    return {}


def lire_json(chemin: str | Path) -> Any:
    with Path(chemin).open("r", encoding="utf-8") as f:
        return json.load(f)


def ecrire_json(chemin: str | Path, donnees: Any) -> Path:
    chemin = Path(chemin)
    chemin.parent.mkdir(parents=True, exist_ok=True)
    with chemin.open("w", encoding="utf-8") as f:
        json.dump(donnees, f, ensure_ascii=False, indent=2, default=str)
        f.write("\n")
    return chemin


def commit_courant(court: bool = True) -> str:
    """Hash du commit HEAD du dépôt, ou 'inconnu' si git ne répond pas."""
    try:
        args = ["git", "rev-parse", "--short" if court else "HEAD"]
        if court:
            args.append("HEAD")
        r = subprocess.run(args, cwd=racine_projet(), capture_output=True, text=True, timeout=10)
        if r.returncode == 0 and r.stdout.strip():
            return r.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        pass
    return "inconnu"
