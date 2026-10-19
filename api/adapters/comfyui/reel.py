"""ComfyUI réel : API HTTP locale (/system_stats, /prompt, /history, /view)."""
from __future__ import annotations

from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

from api.adapters import _commun
from api.adapters.comfyui.base import ComfyUI


class ComfyUIReel(ComfyUI):
    mode = "reel"

    def __init__(self, config: dict) -> None:
        self.url = str(config.get("services", {}).get("comfyui", {}).get("url", "http://127.0.0.1:8188")).rstrip("/")

    def _client(self, timeout: float = 10.0):
        return _commun.client_http(timeout, base_url=self.url)

    @property
    def url_affichable(self) -> str:
        """L'adresse sans identifiants (user:mdp@) : elle finit dans les messages et le journal."""
        u = urlsplit(self.url)
        hote = u.hostname or ""
        if u.port:
            hote += f":{u.port}"
        return urlunsplit((u.scheme, hote, u.path, u.query, ""))

    def tester_connexion(self) -> dict:
        try:
            with self._client() as c:
                r = c.get("/system_stats")
                r.raise_for_status()
                stats = r.json()
        except Exception as e:  # noqa: BLE001 - un test de connexion répond toujours
            return _commun.resultat_test(False, "Erreur", f"ComfyUI : {_commun.erreur_http(e)} ({self.url_affichable})")
        gpus = stats.get("devices", [])
        g = gpus[0] if gpus else {}
        details = {"mode": "reel", "gpu": g.get("name", "inconnue"),
                   "vram_total_mo": int(g.get("vram_total", 0) // (1024 * 1024)),
                   "vram_libre_mo": int(g.get("vram_free", 0) // (1024 * 1024)),
                   "version": stats.get("system", {}).get("comfyui_version", "?")}
        return _commun.resultat_test(True, "Joignable", f"ComfyUI : {details['gpu']}, "
                                     f"{details['vram_total_mo'] // 1024} Go", details)

    def lancer_workflow(self, workflow_json: dict) -> str:
        with self._client(60) as c:
            r = c.post("/prompt", json={"prompt": workflow_json})
            r.raise_for_status()
            return str(r.json()["prompt_id"])

    def etat(self, prompt_id: str) -> dict:
        with self._client() as c:
            r = c.get(f"/history/{prompt_id}")
            r.raise_for_status()
            hist = r.json().get(prompt_id)
            if hist:
                statut = hist.get("status", {})
                fichiers = [f for sortie in hist.get("outputs", {}).values()
                            for cle in ("images", "files", "gltf", "mesh") for f in sortie.get(cle, [])]
                ok = statut.get("completed", True) and statut.get("status_str") != "error"
                return {"prompt_id": prompt_id, "status": "termine" if ok else "erreur", "progress": 100,
                        "fichiers": fichiers, "messages": statut.get("messages", [])}
            q = c.get("/queue")
            q.raise_for_status()
            file = q.json()
            en_cours = any(p[1] == prompt_id for p in file.get("queue_running", []))
            return {"prompt_id": prompt_id, "status": "en_cours" if en_cours else "en_attente",
                    "progress": 50 if en_cours else 0, "fichiers": []}

    def recuperer_fichiers(self, prompt_id: str, dossier: str | Path) -> list[Path]:
        e = self.etat(prompt_id)
        if e["status"] != "termine":
            raise RuntimeError(f"workflow {prompt_id} pas fini ({e['status']})")
        dossier = Path(dossier)
        dossier.mkdir(parents=True, exist_ok=True)
        sorties = []
        with self._client(300) as c:
            for f in e["fichiers"]:
                nom = f.get("filename")
                if not nom:
                    continue
                r = c.get("/view", params={"filename": nom, "subfolder": f.get("subfolder", ""),
                                           "type": f.get("type", "output")})
                r.raise_for_status()
                cible = dossier / nom
                cible.write_bytes(r.content)
                sorties.append(cible)
        return sorties
