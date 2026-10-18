"""Outils sur la machine : Blender, glTF-Validator, butler, Git LFS.

Règle de chemin unique pour tous les outils : un réglage « chemin » est soit un chemin de fichier
(il contient un séparateur ou existe tel quel : il doit alors exister), soit un nom de commande
résolu dans le PATH. `presence_outils()` ne lance aucun programme (l'écran l'appelle à
l'ouverture) ; `tester_*()` lance l'outil et lit sa version (au clic sur « Tester »).
Un outil absent est dit « Introuvable », jamais vert.
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from collections.abc import Callable, Mapping
from pathlib import Path

from api.resultat import resultat_test

VERSION_BLENDER_ATTENDUE = "5.2"  # CLAUDE.md : Blender 5.2 LTS, figé pour tout le projet
INTROUVABLE = "Introuvable"
EXTENSIONS_LFS = (".blend", ".glb", ".fbx", ".png")
Which = Callable[[str], str | None]


def resoudre_chemin(chemin: str | None, which: Which = shutil.which) -> str | None:
    """Chemin de fichier existant ou commande du PATH ; None sinon."""
    chemin = (chemin or "").strip()
    if not chemin:
        return None
    p = Path(chemin)
    if p.is_file():
        return str(p)
    if "/" in chemin or "\\" in chemin:
        return None  # un chemin de fichier doit exister
    return which(chemin)


def _lancer(args: list[str], timeout: float, cwd: Path | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(args, capture_output=True, text=True, timeout=timeout, check=False, cwd=cwd)


Lancer = Callable[..., subprocess.CompletedProcess]


# --- Blender ---------------------------------------------------------------

def candidats_blender(plateforme: str, environ: Mapping[str, str], home: Path) -> list[Path]:
    """Emplacements connus de Blender, par plateforme, la version attendue d'abord."""
    c: list[Path] = []
    if plateforme.startswith("win"):
        pf = Path(environ.get("ProgramFiles", r"C:\Program Files"))
        pf86 = Path(environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"))
        local = Path(environ.get("LOCALAPPDATA", str(home / "AppData" / "Local")))
        c.append(pf / "Blender Foundation" / f"Blender {VERSION_BLENDER_ATTENDUE}" / "blender.exe")
        for base in (pf / "Blender Foundation", local / "Programs" / "Blender Foundation"):
            c += sorted(base.glob("Blender*/blender.exe"), reverse=True)
        c.append(pf86 / "Steam" / "steamapps" / "common" / "Blender" / "blender.exe")
    elif plateforme == "darwin":
        c += [Path("/Applications/Blender.app/Contents/MacOS/Blender"),
              home / "Applications" / "Blender.app" / "Contents" / "MacOS" / "Blender"]
    else:
        c += [Path("/snap/bin/blender"), Path("/var/lib/flatpak/exports/bin/org.blender.Blender"),
              home / ".local" / "share" / "flatpak" / "exports" / "bin" / "org.blender.Blender",
              Path("/usr/bin/blender"), Path("/usr/local/bin/blender")]
        c += sorted(Path("/opt").glob("blender*/blender"), reverse=True)
    vus: set[str] = set()
    uniques: list[Path] = []
    for p in c:
        if str(p) not in vus:
            vus.add(str(p))
            uniques.append(p)
    return uniques


def detecter_blender(plateforme: str | None = None, which: Which = shutil.which,
                     environ: Mapping[str, str] | None = None, home: Path | None = None) -> str | None:
    """Blender trouvé sur cette machine (PATH, puis emplacements connus), ou None."""
    trouve = which("blender")
    if trouve:
        return trouve
    plateforme = plateforme or sys.platform
    environ = os.environ if environ is None else environ
    home = home or Path.home()
    for p in candidats_blender(plateforme, environ, home):
        if p.is_file():
            return str(p)
    return None


def chemin_blender(cfg: dict, which: Which = shutil.which) -> str | None:
    return resoudre_chemin(cfg.get("blender", {}).get("chemin", ""), which)


def blender_disponible(cfg: dict) -> bool:
    return chemin_blender(cfg) is not None


def tester_blender(cfg: dict, lancer: Lancer = _lancer) -> dict:
    """`<chemin> -b --version` ; Introuvable (avec une suggestion) si rien n'est configuré ou trouvable."""
    chemin = cfg.get("blender", {}).get("chemin", "")
    exe = resoudre_chemin(chemin)
    if exe is None:
        suggestion = detecter_blender()
        if chemin:
            message = f"Blender introuvable à « {chemin} »"
        else:
            message = "Aucun Blender renseigné : installe Blender 5.2 LTS (blender.org) ou colle le chemin de l'exécutable"
        if suggestion:
            message += f" ; trouvé sur cette machine : {suggestion}"
        return resultat_test(False, INTROUVABLE, message, {"suggestion": suggestion})
    try:
        r = lancer([exe, "-b", "--version"], 90)
    except subprocess.TimeoutExpired:
        return resultat_test(False, "Erreur", "Blender ne répond pas (délai dépassé)")
    except OSError as e:
        return resultat_test(False, "Erreur", f"Blender : {type(e).__name__}")
    sortie = r.stdout + "\n" + r.stderr
    m = re.search(r"Blender\s+(\d+\.\d+(?:\.\d+)?)\s*(LTS)?", sortie)
    if r.returncode != 0 or not m:
        return resultat_test(False, "Erreur", f"Blender a répondu sans version lisible (code {r.returncode})",
                             {"sortie": sortie.strip()[-300:], "chemin": exe})
    version = m.group(1)
    version_ok = version.startswith(VERSION_BLENDER_ATTENDUE + ".") or version == VERSION_BLENDER_ATTENDUE
    message = f"Blender {version}" + (" LTS" if m.group(2) else "")
    if not version_ok:
        message += f" trouvé ; le projet attend Blender {VERSION_BLENDER_ATTENDUE} LTS"
    return resultat_test(True, "Détecté", message, {"version": version, "version_ok": version_ok, "chemin": exe})


# --- glTF-Validator ---------------------------------------------------------

def tester_gltf_validator(cfg: dict, lancer: Lancer = _lancer) -> dict:
    """`<chemin> --version` (ou la commande gltf_validator du PATH)."""
    chemin = cfg.get("gltf_validator", {}).get("chemin", "") or "gltf_validator"
    exe = resoudre_chemin(chemin)
    if exe is None:
        return resultat_test(False, INTROUVABLE, f"glTF-Validator introuvable ({chemin}) : installe-le depuis "
                             "github.com/KhronosGroup/glTF-Validator et renseigne son chemin")
    try:
        r = lancer([exe, "--version"], 30)
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


# --- Git LFS -----------------------------------------------------------------

def extensions_lfs(gitattributes: Path) -> list[str]:
    """Extensions suivies par LFS d'après .gitattributes (`*.glb filter=lfs …`)."""
    if not gitattributes.is_file():
        return []
    out = []
    for ligne in gitattributes.read_text(encoding="utf-8", errors="replace").splitlines():
        parties = ligne.split()
        if len(parties) >= 2 and "filter=lfs" in parties[1:] and parties[0].startswith("*."):
            out.append(parties[0][1:])
    return out


def tester_git_lfs(racine: Path | None = None, lancer: Lancer = _lancer, which: Which = shutil.which) -> dict:
    """git présent, `git lfs version` répond, LFS activé dans ce dépôt, et les 4 extensions suivies."""
    from api import chemins

    racine = racine or chemins.racine()
    git = which("git")
    if git is None:
        return resultat_test(False, INTROUVABLE, "git introuvable : installe Git (git-scm.com) avec Git LFS")
    try:
        v = lancer([git, "lfs", "version"], 20, cwd=racine)
    except (OSError, subprocess.SubprocessError) as e:
        return resultat_test(False, "Erreur", f"git lfs version : {type(e).__name__}")
    if v.returncode != 0:
        return resultat_test(False, INTROUVABLE, "Git LFS n'est pas installé (git lfs version a échoué) : "
                             "installe-le depuis git-lfs.com")
    m = re.search(r"git-lfs/(\S+)", v.stdout + v.stderr)
    version = m.group(1) if m else "?"
    try:
        c = lancer([git, "config", "--get", "filter.lfs.clean"], 20, cwd=racine)
    except (OSError, subprocess.SubprocessError) as e:
        return resultat_test(False, "Erreur", f"git config : {type(e).__name__}")
    if not c.stdout.strip():
        return resultat_test(False, "Erreur", f"Git LFS {version} installé mais pas activé dans ce dépôt : "
                             "lance `git lfs install`", {"version": version})
    suivies = extensions_lfs(racine / ".gitattributes")
    manquantes = [e for e in EXTENSIONS_LFS if e not in suivies]
    if manquantes:
        return resultat_test(False, "Erreur", f"Git LFS {version} actif, mais .gitattributes ne suit pas "
                             + ", ".join(manquantes), {"version": version, "suivies": suivies})
    return resultat_test(True, "Détecté", f"Git LFS {version}, suit " + ", ".join(suivies),
                         {"version": version, "suivies": suivies})


# --- présence sans sous-processus (pour l'ouverture de l'écran) ----------------

def presence_outils(cfg: dict, which: Which = shutil.which) -> dict:
    """{outil: {"present": bool, …}} sans lancer aucun programme. Blender absent → une suggestion."""
    blender = chemin_blender(cfg, which)
    return {
        "blender": {"present": blender is not None,
                    "suggestion": None if blender else detecter_blender(which=which)},
        "gltf_validator": {"present": resoudre_chemin(cfg.get("gltf_validator", {}).get("chemin", "")
                                                      or "gltf_validator", which) is not None},
        "butler": {"present": resoudre_chemin(cfg.get("butler", {}).get("chemin", "") or "butler", which)
                   is not None},
        "git_lfs": {"present": which("git") is not None and which("git-lfs") is not None},
    }
