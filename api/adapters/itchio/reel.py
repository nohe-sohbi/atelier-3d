"""itch.io réel : appelle l'exécutable butler (clé API via la variable BUTLER_API_KEY, jamais en log).

Le test de connexion vérifie que butler est installé (`butler version`) puis que la clé API est
acceptée par itch.io (GET /api/1/key/me) et correspond au compte réglé. Aucune page de jeu n'est
supposée : chaque pack aura la sienne à l'étape 10.
"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

from api.adapters import _commun
from api.adapters.itchio.base import Itchio
from api.services import outils

URL_CLE = "https://itch.io/api/1/key/me"


class ItchioReel(Itchio):
    mode = "reel"

    def __init__(self, config: dict) -> None:
        itch = config.get("services", {}).get("itchio", {})
        self._cle = str(itch.get("cle_api", "") or "")
        self.compte = str(itch.get("compte", "") or "")
        self.canal = str(itch.get("canal", "assets") or "assets")
        self.butler = str(config.get("butler", {}).get("chemin", "butler") or "butler")

    def _env(self) -> dict:
        env = dict(os.environ)
        if self._cle:
            env["BUTLER_API_KEY"] = self._cle
        return env

    def _lancer(self, *args: str, timeout: float = 60) -> subprocess.CompletedProcess:
        exe = outils.resoudre_chemin(self.butler)
        if exe is None:
            raise FileNotFoundError(f"butler introuvable ({self.butler})")
        return subprocess.run([exe, *args], capture_output=True, text=True, timeout=timeout,
                              env=self._env(), check=False)

    def tester_butler(self) -> dict:
        if outils.resoudre_chemin(self.butler) is None:
            return _commun.resultat_test(False, outils.INTROUVABLE,
                                         f"butler introuvable ({self.butler}) : installe-le (itch.io/docs/butler) "
                                         "et renseigne son chemin")
        try:
            v = self._lancer("version", timeout=20)
        except (OSError, subprocess.SubprocessError) as e:
            return _commun.resultat_test(False, "Erreur", f"butler : {type(e).__name__}")
        if v.returncode != 0:
            return _commun.resultat_test(False, "Erreur", f"butler version a échoué ({v.returncode})")
        sortie = (v.stdout or v.stderr).strip()
        version = sortie.splitlines()[0] if sortie else "?"
        if not self._cle:
            return _commun.resultat_test(False, "Erreur", f"butler {version} trouvé, mais aucune clé API itch.io",
                                         {"version": version})
        try:
            with _commun.client_http() as client:
                r = client.get(URL_CLE, headers={"Authorization": f"Bearer {self._cle}"})
                if r.status_code in (401, 403):
                    return _commun.resultat_test(False, "Erreur", "clé API itch.io refusée", {"version": version})
                r.raise_for_status()
                compte = str((r.json().get("user") or {}).get("username") or "")
        except Exception as e:  # noqa: BLE001 - un test de connexion répond toujours
            return _commun.resultat_test(False, "Erreur", f"itch.io : {_commun.erreur_http(e)}", {"version": version})
        details = {"version": version, "compte": compte}
        if self.compte and compte and self.compte.lower() != compte.lower():
            return _commun.resultat_test(False, "Erreur",
                                         f"la clé est celle du compte {compte}, pas de « {self.compte} » (Réglages)",
                                         {**details, "compte_regle": self.compte})
        return _commun.resultat_test(True, "Connecté", f"butler {version}, compte {compte or '(inconnu)'}", details)

    def pousser(self, dossier: str | Path, cible: str, canal: str) -> dict:
        dossier = Path(dossier)
        if not dossier.is_dir():
            raise FileNotFoundError(f"dossier à publier introuvable : {dossier}")
        r = self._lancer("push", str(dossier), f"{cible}:{canal}", timeout=1800)
        if r.returncode != 0:
            raise RuntimeError(f"butler push a échoué ({r.returncode}) : {(r.stderr or r.stdout).strip()[-500:]}")
        nb = sum(1 for p in dossier.rglob("*") if p.is_file())
        return {"ok": True, "cible": cible, "canal": canal, "fichiers": nb, "message": r.stdout.strip()[-500:]}
