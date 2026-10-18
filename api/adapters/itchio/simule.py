"""itch.io simulé : butler factice ; chaque envoi est consigné dans lots/.simule/itchio.json."""
from __future__ import annotations

from pathlib import Path

from api.adapters import _commun
from api.adapters.itchio.base import Itchio

VERSION_SIMULEE = "15.24.0 (simulé)"


class ItchioSimule(Itchio):
    mode = "simule"

    def __init__(self, config: dict, dossier_etat: Path | None = None) -> None:
        itch = config.get("services", {}).get("itchio", {})
        self.compte = str(itch.get("compte", "") or "")
        self.canal = str(itch.get("canal", "html") or "html")
        self.etat = _commun.EtatSimule("itchio", dossier_etat)

    def tester_butler(self) -> dict:
        compte = self.compte or "(compte non renseigné)"
        return _commun.resultat_test(True, "Connecté", f"butler simulé {VERSION_SIMULEE}, compte {compte}",
                                     {"mode": "simule", "version": VERSION_SIMULEE, "compte": self.compte})

    def pousser(self, dossier: str | Path, cible: str, canal: str) -> dict:
        dossier = Path(dossier)
        if not dossier.is_dir():
            raise FileNotFoundError(f"dossier à publier introuvable : {dossier}")
        fichiers = sorted(p.relative_to(dossier).as_posix() for p in dossier.rglob("*") if p.is_file())
        with self.etat.modifier() as e:
            numero = e.get("compteur", 0) + 1
            e["compteur"] = numero
            build_id = "sim-build-" + _commun.empreinte(cible, canal, fichiers, numero)
            e.setdefault("envois", []).append({"build_id": build_id, "cible": cible, "canal": canal,
                                               "fichiers": fichiers})
        return {"ok": True, "cible": cible, "canal": canal, "fichiers": len(fichiers), "build_id": build_id,
                "message": f"{len(fichiers)} fichier{'s' if len(fichiers) > 1 else ''} poussés sur {cible}:{canal} (simulé)"}
