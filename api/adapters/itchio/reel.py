"""itch.io réel : appelle l'exécutable butler (clé API via la variable BUTLER_API_KEY, jamais en log)."""
from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

from api.adapters import _commun
from api.adapters.itchio.base import Itchio


class ItchioReel(Itchio):
    mode = "reel"

    def __init__(self, config: dict) -> None:
        itch = config.get("services", {}).get("itchio", {})
        self._cle = str(itch.get("cle_api", "") or "")
        self.compte = str(itch.get("compte", "") or "")
        self.canal = str(itch.get("canal", "html") or "html")
        self.butler = str(config.get("butler", {}).get("chemin", "butler") or "butler")

    def _env(self) -> dict:
        env = dict(os.environ)
        if self._cle:
            env["BUTLER_API_KEY"] = self._cle
        return env

    def _lancer(self, *args: str, timeout: float = 60) -> subprocess.CompletedProcess:
        exe = shutil.which(self.butler) or self.butler
        return subprocess.run([exe, *args], capture_output=True, text=True, timeout=timeout,
                              env=self._env(), check=False)

    def tester_butler(self) -> dict:
        if not shutil.which(self.butler) and not Path(self.butler).exists():
            return _commun.resultat_test(False, "Erreur", f"butler introuvable ({self.butler})")
        try:
            v = self._lancer("version", timeout=20)
        except (OSError, subprocess.SubprocessError) as e:
            return _commun.resultat_test(False, "Erreur", f"butler : {type(e).__name__}")
        if v.returncode != 0:
            return _commun.resultat_test(False, "Erreur", f"butler version a échoué ({v.returncode})")
        version = (v.stdout or v.stderr).strip().splitlines()[0] if (v.stdout or v.stderr).strip() else "?"
        if not self._cle:
            return _commun.resultat_test(False, "Erreur", f"butler {version} trouvé, mais aucune clé API itch.io",
                                         {"version": version})
        cible = f"{self.compte}/atelier-3d" if self.compte else ""
        if not cible:
            return _commun.resultat_test(True, "Connecté", f"butler {version} ; renseigne le compte pour vérifier l'accès",
                                         {"version": version, "compte": ""})
        s = self._lancer("status", cible, timeout=60)
        if s.returncode != 0:
            return _commun.resultat_test(False, "Erreur", f"butler status {cible} a échoué : clé ou compte à vérifier",
                                         {"version": version, "compte": self.compte})
        return _commun.resultat_test(True, "Connecté", f"butler {version}, compte {self.compte}",
                                     {"version": version, "compte": self.compte})

    def pousser(self, dossier: str | Path, cible: str, canal: str) -> dict:
        dossier = Path(dossier)
        if not dossier.is_dir():
            raise FileNotFoundError(f"dossier à publier introuvable : {dossier}")
        r = self._lancer("push", str(dossier), f"{cible}:{canal}", timeout=1800)
        if r.returncode != 0:
            raise RuntimeError(f"butler push a échoué ({r.returncode}) : {(r.stderr or r.stdout).strip()[-500:]}")
        nb = sum(1 for p in dossier.rglob("*") if p.is_file())
        return {"ok": True, "cible": cible, "canal": canal, "fichiers": nb, "message": r.stdout.strip()[-500:]}
