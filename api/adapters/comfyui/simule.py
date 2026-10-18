"""ComfyUI simulé : GPU factice, workflow qui avance à chaque appel, GLB simulé en sortie."""
from __future__ import annotations

from pathlib import Path

from api.adapters import _commun
from api.adapters.comfyui.base import ComfyUI

GPU_SIMULE = {"gpu": "GPU simulée", "vram_total_mo": 12288, "vram_libre_mo": 11264,
              "modeles": ["Pixal3D", "Trellis.2"], "version": "simule"}
PAS_PROGRESSION = 50


class ComfyUISimule(ComfyUI):
    mode = "simule"

    def __init__(self, config: dict, dossier_etat: Path | None = None) -> None:
        self.url = str(config.get("services", {}).get("comfyui", {}).get("url", "http://127.0.0.1:8188"))
        self.etat_disque = _commun.EtatSimule("comfyui", dossier_etat)

    def tester_connexion(self) -> dict:
        return _commun.resultat_test(True, "Joignable", f"ComfyUI simulé ({GPU_SIMULE['gpu']}, "
                                     f"{GPU_SIMULE['vram_total_mo'] // 1024} Go)", {"mode": "simule", **GPU_SIMULE})

    def lancer_workflow(self, workflow_json: dict) -> str:
        with self.etat_disque.modifier() as e:
            numero = e.get("compteur", 0) + 1
            e["compteur"] = numero
            prompt_id = "sim-comfy-" + _commun.empreinte(workflow_json, numero)
            e.setdefault("prompts", {})[prompt_id] = {"prompt_id": prompt_id, "status": "en_attente",
                                                      "progress": 0, "appels": 0, "noeuds": len(workflow_json)}
        return prompt_id

    def etat(self, prompt_id: str) -> dict:
        with self.etat_disque.modifier() as e:
            p = e.get("prompts", {}).get(prompt_id)
            if p is None:
                raise LookupError(f"prompt ComfyUI inconnu : {prompt_id}")
            p["appels"] += 1
            p["progress"] = min(100, p["appels"] * PAS_PROGRESSION)
            p["status"] = "termine" if p["progress"] >= 100 else "en_cours"
            fichiers = [f"{prompt_id}.glb", f"{prompt_id}.png"] if p["status"] == "termine" else []
            return {"prompt_id": prompt_id, "status": p["status"], "progress": p["progress"], "fichiers": fichiers}

    def recuperer_fichiers(self, prompt_id: str, dossier: str | Path) -> list[Path]:
        p = self.etat_disque.charger().get("prompts", {}).get(prompt_id)
        if p is None:
            raise LookupError(f"prompt ComfyUI inconnu : {prompt_id}")
        if p["status"] != "termine":
            raise RuntimeError(f"workflow {prompt_id} pas fini ({p['status']}, {p['progress']} %)")
        dossier = Path(dossier)
        return [_commun.ecrire_glb_simule(dossier / f"{prompt_id}.glb", prompt_id),
                _commun.ecrire_png_simule(dossier / f"{prompt_id}.png", prompt_id)]
