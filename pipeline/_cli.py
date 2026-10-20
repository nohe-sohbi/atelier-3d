"""Petits outils partagés par l'app et les scripts Blender (sans bpy, sans PyYAML) : racine du dépôt,
arguments après `--`, JSON, commit courant."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any


def racine_projet() -> Path:
    """Dossier du dépôt (parent de pipeline/)."""
    return Path(__file__).resolve().parent.parent


def args_apres_double_tiret(argv: list[str] | None = None) -> list[str]:
    """Les arguments situés après `--` (convention Blender : `blender -b -P script.py -- args`)."""
    argv = list(sys.argv if argv is None else argv)
    if "--" in argv:
        return argv[argv.index("--") + 1:]
    return argv[1:]


def lire_json(chemin: str | Path) -> Any:
    with Path(chemin).open("r", encoding="utf-8") as f:
        return json.load(f)


def ecrire_json(chemin: str | Path, donnees: Any) -> Path:
    chemin = Path(chemin)
    chemin.parent.mkdir(parents=True, exist_ok=True)
    tmp = chemin.with_suffix(chemin.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(donnees, f, ensure_ascii=False, indent=2, default=str)
        f.write("\n")
    tmp.replace(chemin)
    return chemin


def commit_courant(court: bool = True) -> str:
    """Hash du commit HEAD du dépôt, ou 'inconnu' si git ne répond pas."""
    try:
        args = ["git", "rev-parse", "--short", "HEAD"] if court else ["git", "rev-parse", "HEAD"]
        r = subprocess.run(args, cwd=racine_projet(), capture_output=True, text=True, timeout=10, check=False)
        if r.returncode == 0 and r.stdout.strip():
            return r.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        pass
    return "inconnu"
