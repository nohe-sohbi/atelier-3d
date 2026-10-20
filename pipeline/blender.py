"""Lancer Blender sans fenêtre depuis l'app (worker, file Blender) et lire son rapport.

    <blender> -b --factory-startup -noaudio -P pipeline/bpy_principal.py -- <entree.json> <sortie.json>

L'entrée porte la commande, ses paramètres et le style déjà lu (le Python de Blender n'a pas PyYAML) ; la sortie est
le rapport JSON du script. Le journal de Blender (sorties standard et d'erreur) est gardé à côté : ce sont les traces
de l'essai, lisibles depuis l'écran.
"""
from __future__ import annotations

import os
import subprocess
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from pipeline._cli import ecrire_json, lire_json, racine_projet

SCRIPT = Path(__file__).resolve().parent / "bpy_principal.py"
LIGNES_JOURNAL = 12


class BlenderIntrouvable(RuntimeError):
    """Aucun Blender utilisable : la tâche ne peut pas réussir en la relançant."""


class EchecBlender(RuntimeError):
    def __init__(self, message: str, journal: Path | None = None) -> None:
        super().__init__(message)
        self.journal = journal


def executable(cfg: dict) -> str:
    from api.services import outils

    exe = outils.chemin_blender(cfg)
    if exe is None:
        raise BlenderIntrouvable("Blender introuvable : renseigne son chemin dans Réglages (Outils sur ta machine)")
    return exe


def _fin_du_journal(journal: Path) -> str:
    if not journal.is_file():
        return ""
    lignes = [x for x in journal.read_text(encoding="utf-8", errors="replace").splitlines() if x.strip()]
    return " | ".join(lignes[-LIGNES_JOURNAL:])[-1500:]


def lancer(commande: str, entree: dict[str, Any], cfg: dict, dossier: str | Path, *, style=None,
           timeout: float = 900, arret: Callable[[], bool] | None = None) -> dict[str, Any]:
    """Exécute `commande` dans Blender ; renvoie son rapport. Lève BlenderIntrouvable, EchecBlender,
    ou InterruptedError si `arret()` devient vrai (Blender est alors arrêté)."""
    exe = executable(cfg)
    dossier = Path(dossier)
    dossier.mkdir(parents=True, exist_ok=True)
    fichier_entree = dossier / f"{commande}.entree.json"
    fichier_sortie = dossier / f"{commande}.sortie.json"
    journal = dossier / f"{commande}.journal.txt"
    fichier_sortie.unlink(missing_ok=True)
    ecrire_json(fichier_entree, {"commande": commande, "style": style.brut if style is not None else None, **entree})
    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join([str(racine_projet())] + ([env["PYTHONPATH"]] if env.get("PYTHONPATH") else []))
    env.setdefault("PYTHONIOENCODING", "utf-8")
    cmd = [exe, "-b", "--factory-startup", "-noaudio", "-P", str(SCRIPT), "--", str(fichier_entree), str(fichier_sortie)]
    debut = time.monotonic()
    with journal.open("w", encoding="utf-8") as sortie_journal:
        proc = subprocess.Popen(cmd, stdout=sortie_journal, stderr=subprocess.STDOUT, cwd=str(racine_projet()), env=env)
        try:
            while proc.poll() is None:
                if arret is not None and arret():
                    proc.kill()
                    proc.wait(10)
                    raise InterruptedError(f"Blender arrêté pendant « {commande} » (arrêt du worker)")
                if time.monotonic() - debut > timeout:
                    proc.kill()
                    proc.wait(10)
                    raise EchecBlender(f"Blender ne finit pas « {commande} » (délai dépassé : {timeout:.0f} s)", journal)
                time.sleep(0.2)
        finally:
            if proc.poll() is None:
                proc.kill()
    if not fichier_sortie.is_file():
        raise EchecBlender(f"Blender s'est arrêté sans rapport (code {proc.returncode}) : {_fin_du_journal(journal)}", journal)
    rapport = lire_json(fichier_sortie)
    if not rapport.get("ok"):
        raise EchecBlender(rapport.get("erreur") or f"« {commande} » a échoué dans Blender", journal)
    rapport["duree_s"] = round(time.monotonic() - debut, 2)
    rapport["journal"] = str(journal)
    return rapport
