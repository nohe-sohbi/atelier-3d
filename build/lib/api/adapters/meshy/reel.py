"""Meshy réel : API https://api.meshy.ai (Bearer). Jamais de clé dans les logs."""
from __future__ import annotations

import base64
import mimetypes
from pathlib import Path

from api.adapters import _commun
from api.adapters.meshy.base import Meshy

BASE_URL = "https://api.meshy.ai"


class MeshyReel(Meshy):
    mode = "reel"

    def __init__(self, config: dict) -> None:
        meshy = config.get("services", {}).get("meshy", {})
        self._cle = str(meshy.get("cle_api", "") or "")
        self.credits_mensuels = int(meshy.get("credits_mensuels", 1000))
        self.base_url = str(meshy.get("url", BASE_URL) or BASE_URL)

    def _client(self, timeout: float = _commun.TIMEOUT_S):
        if not self._cle:
            raise RuntimeError("clé API Meshy absente : renseigne-la dans Réglages")
        return _commun.client_http(timeout, base_url=self.base_url,
                                   headers={"Authorization": f"Bearer {self._cle}"})

    def solde(self) -> dict:
        with self._client() as c:
            r = c.get("/openapi/v1/balance")
            r.raise_for_status()
            data = r.json()
        restants = int(data.get("balance", data.get("result", 0)) or 0)
        return {"restants": restants, "total": self.credits_mensuels}

    def tester_connexion(self) -> dict:
        try:
            s = self.solde()
        except Exception as e:  # noqa: BLE001 - un test de connexion répond toujours
            return _commun.resultat_test(False, "Erreur", f"Meshy : {_commun.erreur_http(e)}")
        return _commun.resultat_test(True, "Connecté", f"Meshy : {s['restants']} / {s['total']} crédits",
                                     {"mode": "reel", "solde": s})

    @staticmethod
    def _image_url(image: str | Path) -> str:
        s = str(image)
        if s.startswith(("http://", "https://", "data:")):
            return s
        p = Path(s)
        mime = mimetypes.guess_type(p.name)[0] or "image/png"
        return f"data:{mime};base64," + base64.b64encode(p.read_bytes()).decode("ascii")

    def image_vers_3d(self, image: str | Path, options: dict | None = None) -> str:
        corps = {"image_url": self._image_url(image), "should_texture": True, "enable_pbr": True,
                 "ai_model": "latest", **(options or {})}
        with self._client(120) as c:
            r = c.post("/openapi/v1/image-to-3d", json=corps)
            r.raise_for_status()
            return str(r.json()["result"])

    def etat_tache(self, task_id: str) -> dict:
        chemin = "/openapi/v1/image-to-image/" if task_id.startswith("img:") else "/openapi/v1/image-to-3d/"
        with self._client() as c:
            r = c.get(chemin + task_id.removeprefix("img:"))
            r.raise_for_status()
            return r.json()

    def telecharger(self, task_id: str, dossier: str | Path) -> Path:
        etat = self.etat_tache(task_id)
        if etat.get("status") != "SUCCEEDED":
            raise RuntimeError(f"tâche {task_id} pas finie ({etat.get('status')})")
        dossier = Path(dossier)
        dossier.mkdir(parents=True, exist_ok=True)
        with _commun.client_http(300) as c:
            urls = etat.get("image_urls")
            if urls:
                for i, url in enumerate(urls):
                    r = c.get(url)
                    r.raise_for_status()
                    (dossier / f"{task_id.removeprefix('img:')}_{i + 1}.png").write_bytes(r.content)
                return dossier
            url = (etat.get("model_urls") or {}).get("glb")
            if not url:
                raise RuntimeError(f"tâche {task_id} : pas de GLB dans la réponse")
            r = c.get(url)
            r.raise_for_status()
            cible = dossier / f"{task_id}.glb"
            cible.write_bytes(r.content)
            vignette = etat.get("thumbnail_url")
            if vignette:
                rv = c.get(vignette)
                if rv.status_code == 200:
                    (dossier / f"{task_id}.png").write_bytes(rv.content)
        return cible

    def image_vers_image(self, prompt: str, image: str | Path | None, n: int = 4) -> str:
        # Point d'entrée à confirmer sur la documentation Meshy à l'étape 6 (Références).
        corps = {"prompt": prompt, "num_images": max(1, int(n))}
        if image:
            corps["image_url"] = self._image_url(image)
        with self._client(120) as c:
            r = c.post("/openapi/v1/image-to-image", json=corps)
            r.raise_for_status()
            return "img:" + str(r.json()["result"])
