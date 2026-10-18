"""Lance un script bpy hors de l'application (sans importer bpy ici).

Deux façons de l'exécuter, choisies par config.local.yaml :
- `blender.chemin` renseigné : `<blender> -b --factory-startup -P <script> -- <args>` ;
- sinon `blender.python_bpy` renseigné : `<python_bpy> <script> -- <args>` (module bpy pip) ;
- sinon `BlenderIntrouvable`.

Le script est le même dans les deux cas : il lit ses arguments après `--`
(voir pipeline/_cli.py : args_apres_double_tiret).
"""
from __future__ import annotations

import os
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pipeline._cli import racine_projet


class BlenderIntrouvable(RuntimeError):
    """Ni blender.chemin ni blender.python_bpy ne sont utilisables."""


@dataclass
class ResultatBlender:
    code: int
    stdout: str
    stderr: str
    duree_s: float

    @property
    def ok(self) -> bool:
        return self.code == 0


def _section_blender(config: dict[str, Any]) -> dict[str, Any]:
    return dict((config or {}).get("blender") or {})


def commande(script: str | Path, args: list[str], config: dict[str, Any]) -> list[str]:
    """La ligne de commande qui sera lancée, selon la config."""
    b = _section_blender(config)
    chemin = (b.get("chemin") or "").strip()
    python_bpy = (b.get("python_bpy") or "").strip()
    script = str(Path(script))
    if chemin:
        if not Path(chemin).exists():
            raise BlenderIntrouvable(f"blender.chemin introuvable : {chemin}")
        return [chemin, "-b", "--factory-startup", "-P", script, "--", *map(str, args)]
    if python_bpy:
        if not Path(python_bpy).exists():
            raise BlenderIntrouvable(f"blender.python_bpy introuvable : {python_bpy}")
        return [python_bpy, script, "--", *map(str, args)]
    raise BlenderIntrouvable(
        "aucun Blender configuré : renseigne blender.chemin (exécutable) ou "
        "blender.python_bpy (Python avec le module bpy) dans config.local.yaml"
    )


def run_script(script: str | Path, args: list[str], config: dict[str, Any],
               timeout: float = 900, cwd: str | Path | None = None) -> ResultatBlender:
    """Exécute un script bpy et renvoie code, sorties et durée. Lève BlenderIntrouvable."""
    cmd = commande(script, args, config)
    env = dict(os.environ)
    # Le script doit pouvoir importer pipeline/ et generators/ même lancé par Blender.
    env["PYTHONPATH"] = os.pathsep.join(
        [str(racine_projet())] + ([env["PYTHONPATH"]] if env.get("PYTHONPATH") else [])
    )
    env.setdefault("PYTHONIOENCODING", "utf-8")
    debut = time.perf_counter()
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=timeout, env=env,
                           cwd=str(cwd or racine_projet()))
        code, out, err = r.returncode, r.stdout, r.stderr
    except subprocess.TimeoutExpired as e:
        out = (e.stdout or b"").decode("utf-8", "replace") if isinstance(e.stdout, bytes) else (e.stdout or "")
        err = (e.stderr or b"").decode("utf-8", "replace") if isinstance(e.stderr, bytes) else (e.stderr or "")
        code = 124
        err += f"\n[blender_run] délai dépassé après {timeout} s"
    return ResultatBlender(code=code, stdout=out, stderr=err, duree_s=time.perf_counter() - debut)


def version_blender(config: dict[str, Any], timeout: float = 120) -> str:
    """Version de Blender (ou du module bpy) tel que configuré, ex. '5.2.2 LTS'."""
    script = Path(__file__).resolve().parent / "_version_bpy.py"
    r = run_script(script, [], config, timeout=timeout)
    for ligne in reversed(r.stdout.splitlines()):
        if ligne.startswith("BPY_VERSION="):
            return ligne.split("=", 1)[1].strip()
    raise RuntimeError(f"impossible de lire la version de Blender (code {r.code}) : {r.stderr[-500:]}")
