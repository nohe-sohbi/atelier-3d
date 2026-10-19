"""Meshy réel : API https://api.meshy.ai (Bearer). Jamais de clé dans les logs.

Images (documentation Meshy, octobre 2026) : `text-to-image` sans image de référence, `image-to-image` avec
1 à 5 images de référence ; une image par tâche ; modèle `nano-banana` à 3 crédits l'image.
"""
from __future__ import annotations

import base64
import mimetypes
from pathlib import Path

from api.adapters import _commun
from api.adapters.meshy.base import CREDITS_IMAGE, Images, Meshy, RefusMeshy, liste_images

BASE_URL = "https://api.meshy.ai"
MODELE_IMAGE = "nano-banana"
MAX_REFERENCES = 5
# Préfixe de l'id d'une tâche image → chemin de l'API qui la lit.
CHEMINS_IMAGE = {"img:": "/openapi/v1/image-to-image/", "txt:": "/openapi/v1/text-to-image/"}
# Codes HTTP pour lesquels relancer la même demande n'y changera rien.
REFUS = {400: "demande refusée par Meshy", 401: "clé API Meshy refusée", 402: "crédits Meshy insuffisants",
         403: "clé API Meshy refusée"}


class MeshyReel(Meshy):
    mode = "reel"
    credits_image = CREDITS_IMAGE  # tarif du modèle MODELE_IMAGE

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
        with self._client(5.0) as c:  # lu à chaque ouverture d'écran : délai court
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

    def _lancer(self, chemin: str, corps: dict) -> str:
        """POST d'une nouvelle tâche ; un refus (clé, crédits, demande invalide) lève RefusMeshy."""
        try:
            client = self._client(120)
        except RuntimeError as e:  # clé absente
            raise RefusMeshy(str(e)) from e
        with client as c:
            r = c.post(chemin, json=corps)
        if r.status_code in REFUS:
            detail = ""
            try:
                detail = str(r.json().get("message") or "")[:300]
            except ValueError:
                pass
            raise RefusMeshy(f"{REFUS[r.status_code]} (HTTP {r.status_code}{' : ' + detail if detail else ''})")
        r.raise_for_status()
        return str(r.json()["result"])

    def image_vers_3d(self, image: str | Path, options: dict | None = None) -> str:
        corps = {"image_url": self._image_url(image), "should_texture": True, "enable_pbr": True,
                 "ai_model": "latest", **(options or {})}
        return self._lancer("/openapi/v1/image-to-3d", corps)

    @staticmethod
    def _id_meshy(task_id: str) -> tuple[str, str]:
        for prefixe, chemin in CHEMINS_IMAGE.items():
            if task_id.startswith(prefixe):
                return chemin, task_id.removeprefix(prefixe)
        return "/openapi/v1/image-to-3d/", task_id

    def etat_tache(self, task_id: str) -> dict:
        chemin, brut = self._id_meshy(task_id)
        with self._client() as c:
            r = c.get(chemin + brut)
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
                    (dossier / f"{self._id_meshy(task_id)[1]}_{i + 1}.png").write_bytes(r.content)
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

    def image_vers_image(self, prompt: str, image: Images = None, n: int = 1) -> str:
        if int(n) != 1:
            raise ValueError("Meshy produit une image par tâche : lance une tâche par image")
        corps = {"ai_model": MODELE_IMAGE, "prompt": prompt}
        references = [self._image_url(i) for i in liste_images(image)[:MAX_REFERENCES]]
        if references:
            return "img:" + self._lancer("/openapi/v1/image-to-image", {**corps, "reference_image_urls": references})
        return "txt:" + self._lancer("/openapi/v1/text-to-image", corps)
