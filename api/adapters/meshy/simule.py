"""Meshy simulé : répond comme le vrai, sans réseau ni crédit réel.

- Identifiants déterministes (même séquence d'appels = mêmes ids).
- La progression avance à chaque appel de etat_tache().
- GLB simulé = petite boîte valide générée avec trimesh ; images = PNG unis.
- Crédits : 30 par objet texturé, 3 par image ; solde conservé dans lots/.simule/meshy.json.
"""
from __future__ import annotations

from pathlib import Path

from api.adapters import _commun
from api.adapters.meshy.base import Meshy
from api.services.couts import CREDITS_MESHY_3D, CREDITS_MESHY_IMAGE

PAS_PROGRESSION = 34


class MeshySimule(Meshy):
    mode = "simule"

    def __init__(self, config: dict, dossier_etat: Path | None = None) -> None:
        self.credits_mensuels = int(config.get("services", {}).get("meshy", {}).get("credits_mensuels", 1000))
        self.etat = _commun.EtatSimule("meshy", dossier_etat)

    # --- solde -----------------------------------------------------------
    def _utilises(self, e: dict) -> int:
        return int(e.get("credits_utilises", 0))

    def solde(self) -> dict:
        e = self.etat.charger()
        return {"restants": max(0, self.credits_mensuels - self._utilises(e)), "total": self.credits_mensuels}

    def tester_connexion(self) -> dict:
        s = self.solde()
        return _commun.resultat_test(True, "Connecté", f"Meshy simulé : {s['restants']} / {s['total']} crédits",
                                     {"mode": "simule", "solde": s})

    def _debiter(self, e: dict, credits: int) -> None:
        if self.credits_mensuels - self._utilises(e) < credits:
            raise RuntimeError("crédits Meshy insuffisants (simulé)")
        e["credits_utilises"] = self._utilises(e) + credits

    # --- tâches ----------------------------------------------------------
    def _creer(self, genre: str, credits: int, entree: dict) -> str:
        with self.etat.modifier() as e:
            taches = e.setdefault("taches", {})
            numero = e.get("compteur", 0) + 1
            e["compteur"] = numero
            task_id = f"sim-{genre}-{_commun.empreinte(genre, entree, numero)}"
            self._debiter(e, credits)
            taches[task_id] = {"id": task_id, "genre": genre, "status": "PENDING", "progress": 0,
                               "appels": 0, "credits": credits, "entree": entree}
        return task_id

    def image_vers_3d(self, image: str | Path, options: dict | None = None) -> str:
        return self._creer("3d", CREDITS_MESHY_3D, {"image": str(image), "options": options or {}})

    def image_vers_image(self, prompt: str, image: str | Path | None, n: int = 4) -> str:
        n = max(1, int(n))
        return self._creer("image", CREDITS_MESHY_IMAGE * n,
                           {"prompt": prompt, "image": str(image) if image else None, "n": n})

    def etat_tache(self, task_id: str) -> dict:
        with self.etat.modifier() as e:
            t = e.get("taches", {}).get(task_id)
            if t is None:
                raise LookupError(f"tâche Meshy inconnue : {task_id}")
            t["appels"] += 1
            t["progress"] = min(100, t["appels"] * PAS_PROGRESSION)
            t["status"] = "SUCCEEDED" if t["progress"] >= 100 else "IN_PROGRESS"
            return self._vue(t)

    def _vue(self, t: dict) -> dict:
        vue = {"id": t["id"], "status": t["status"], "progress": t["progress"], "task_error": None,
               "credits": t["credits"]}
        if t["status"] == "SUCCEEDED":
            if t["genre"] == "3d":
                vue["model_urls"] = {"glb": f"simule://{t['id']}.glb"}
                vue["thumbnail_url"] = f"simule://{t['id']}.png"
            else:
                vue["image_urls"] = [f"simule://{t['id']}_{i + 1}.png" for i in range(t["entree"]["n"])]
        return vue

    def telecharger(self, task_id: str, dossier: str | Path) -> Path:
        t = self.etat.charger().get("taches", {}).get(task_id)
        if t is None:
            raise LookupError(f"tâche Meshy inconnue : {task_id}")
        if t["status"] != "SUCCEEDED":
            raise RuntimeError(f"tâche {task_id} pas finie ({t['status']}, {t['progress']} %)")
        dossier = Path(dossier)
        if t["genre"] == "3d":
            _commun.ecrire_png_simule(dossier / f"{task_id}.png", task_id)
            return _commun.ecrire_glb_simule(dossier / f"{task_id}.glb", task_id)
        for i in range(t["entree"]["n"]):
            _commun.ecrire_png_simule(dossier / f"{task_id}_{i + 1}.png", f"{task_id}-{i}", taille=256)
        return dossier
