"""Demander des images à Meshy (une image par tâche Meshy), les attendre et les télécharger.

Sert à la planche d'un style (étape 2) et aux images de référence d'un objet (étape 6). Rien n'est payé deux fois :
chaque id Meshy lancé est noté dans la tâche de l'app (taches.noter_reprise) ; une reprise (arrêt du worker, coupure,
relance) relit ceux qui existent et ne lance que les manquants.
"""
from __future__ import annotations

import sqlite3
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

from api.adapters.meshy.base import RefusMeshy
from api.services import taches
from api.services.taches import TacheDefinitive

EXTENSIONS_IMAGE = (".png", ".jpg", ".jpeg", ".webp")


@dataclass(frozen=True)
class Demande:
    consigne: str
    references: Sequence[str | Path] = ()  # 1 à 5 images qui guident l'image ; aucune : texte seul
    nom: str = ""                          # ce qui est dessiné, pour les messages d'erreur


@dataclass(frozen=True)
class Image:
    rang: int
    fichier: Path      # téléchargé dans le dossier de travail, à ranger par l'appelant
    meshy_id: str
    credits: int


def _pluriel(n: int, singulier: str, pluriel: str) -> str:
    return f"{n} {pluriel if n > 1 else singulier}"


def _erreur(etat: dict) -> str:
    e = etat.get("task_error")
    if isinstance(e, dict):
        return str(e.get("message") or e)
    return str(e or etat.get("status"))


def generer(conn: sqlite3.Connection, meshy, demandes: Sequence[Demande], dossier: Path, *, tache_id: int | None = None,
            progression: Callable[[float, str], None] | None = None, arret: Callable[[], bool] | None = None,
            quoi: str = "images", attente_s: float = 0.5, max_lectures: int = 600) -> list[Image]:
    """Une tâche Meshy par demande ; renvoie les images téléchargées dans `dossier/<rang>/`, dans l'ordre.

    Progression de 0 à 90 % (le rangement est à l'appelant). Lève TacheDefinitive si Meshy refuse (crédits, clé),
    RuntimeError si une image échoue (une relance ne redemande que celle-là), InterruptedError à l'arrêt du worker.
    """
    simule = getattr(meshy, "mode", "") == "simule"
    service = "Meshy simulé" if simule else "Meshy"
    reprise = taches.lire_reprise(conn, tache_id) if tache_id is not None else {}
    lances = {int(k): str(v) for k, v in (reprise.get("meshy") or {}).items() if int(k) < len(demandes)}

    def noter() -> None:
        if tache_id is not None:
            taches.noter_reprise(conn, tache_id, {**taches.lire_reprise(conn, tache_id),
                                                  "meshy": {str(k): v for k, v in sorted(lances.items())}})

    def avancer(pct: float, texte: str) -> None:
        if progression:
            progression(pct, f"{service} : {texte}")

    for i, d in enumerate(demandes):
        if i in lances:
            continue
        try:
            lances[i] = meshy.image_vers_image(d.consigne, list(d.references) or None)
        except RefusMeshy as e:
            raise TacheDefinitive(f"{e} : {quoi} impossibles ({_pluriel(len(demandes), 'image', 'images')})") from e
        noter()
    avancer(10, _pluriel(len(demandes), "image demandée", "images demandées"))

    etats: dict[int, dict] = {}
    for _ in range(max_lectures):
        if arret is not None and arret():
            raise InterruptedError(f"arrêt du worker pendant l'attente de {service}")
        for i, mid in lances.items():
            if etats.get(i, {}).get("status") != "SUCCEEDED":
                etats[i] = meshy.etat_tache(mid)
        echecs = [i for i, e in sorted(etats.items()) if e.get("status") in ("FAILED", "CANCELED")]
        if echecs:
            message = _erreur(etats[echecs[0]])
            for i in echecs:  # une relance en redemandera une ; les images réussies sont gardées
                del lances[i]
            noter()
            nom = demandes[echecs[0]].nom or f"image {echecs[0] + 1}"
            raise RuntimeError(f"{service} a échoué sur « {nom} » : {message}")
        finies = sum(1 for e in etats.values() if e.get("status") == "SUCCEEDED")
        if finies == len(demandes):
            break
        pct = sum(float(e.get("progress") or 0) for e in etats.values()) / len(demandes)
        avancer(10 + 0.8 * pct, f"{finies} sur {_pluriel(len(demandes), 'image', 'images')} · {round(pct)} %")
        time.sleep(attente_s)
    else:
        raise RuntimeError(f"{service} ne finit pas (délai dépassé)")

    images = []
    for i, d in enumerate(demandes):
        sous = dossier / str(i)
        meshy.telecharger(lances[i], sous)
        fichiers = sorted(p for p in sous.iterdir() if p.suffix.lower() in EXTENSIONS_IMAGE)
        if not fichiers:
            raise RuntimeError(f"{service} n'a rendu aucune image pour « {d.nom or f'image {i + 1}'} »")
        images.append(Image(i, fichiers[0], lances[i], int(etats[i].get("consumed_credits") or meshy.credits_image)))
    avancer(90, _pluriel(len(images), "image reçue", "images reçues"))
    return images
