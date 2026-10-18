"""API Claude simulée : réponses déterministes plausibles, tokens comptés (≈ 4 caractères par token)."""
from __future__ import annotations

import json
from pathlib import Path

from api.adapters import _commun
from api.adapters.claude.base import Claude

MODELES_SIMULES = ["claude-sonnet-5-5", "claude-haiku-5-5"]


def _tokens(texte: str) -> int:
    return max(1, len(texte) // 4)


def _exemple(schema: dict, nom: str = "valeur", profondeur: int = 0) -> object:
    """Une valeur plausible et déterministe pour un schéma JSON."""
    if "enum" in schema:
        return schema["enum"][0]
    if "const" in schema:
        return schema["const"]
    t = schema.get("type", "object")
    if isinstance(t, list):
        t = next((x for x in t if x != "null"), "string")
    if t == "object":
        props = schema.get("properties", {})
        return {k: _exemple(v, k, profondeur + 1) for k, v in props.items()}
    if t == "array":
        if profondeur > 4:
            return []
        n = max(1, int(schema.get("minItems", 2)))
        items = schema.get("items", {"type": "string"})
        return [_exemple(items, f"{nom} {i + 1}", profondeur + 1) for i in range(n)]
    if t == "integer":
        return int(schema.get("minimum", 1))
    if t == "number":
        return float(schema.get("minimum", 1.0))
    if t == "boolean":
        return True
    if t == "null":
        return None
    return f"{nom} (simulé)"


class ClaudeSimule(Claude):
    mode = "simule"

    def __init__(self, config: dict) -> None:
        self.modele = str(config.get("services", {}).get("claude", {}).get("modele", MODELES_SIMULES[0]))

    def tester_connexion(self) -> dict:
        return _commun.resultat_test(True, "Connecté", f"API Claude simulée, modèle {self.modele}",
                                     {"mode": "simule", "modeles": MODELES_SIMULES, "modele": self.modele})

    def _usage(self, entree: str, sortie: str) -> dict:
        return {"tokens_entree": _tokens(entree), "tokens_sortie": _tokens(sortie), "modele": self.modele}

    def completer_json(self, system: str, user: str, schema: dict) -> tuple[dict, dict]:
        reponse = _exemple(schema)
        if not isinstance(reponse, dict):
            reponse = {"resultat": reponse}
        texte = json.dumps(reponse, ensure_ascii=False)
        return reponse, self._usage(system + user + json.dumps(schema), texte)

    def avis_rendus(self, images: list[str | Path], contexte: str) -> tuple[str, dict]:
        noms = [Path(str(i)).name for i in images]
        graine = _commun.empreinte(noms, contexte, longueur=6)
        avis = (f"Avis simulé ({graine}) sur {len(noms)} rendu{'s' if len(noms) > 1 else ''} : "
                "silhouette lisible, proportions cohérentes avec le style, matériaux plausibles. "
                "À vérifier en revue : la lecture de la face avant et l'usure des arêtes.")
        return avis, self._usage(contexte + " ".join(noms) + " image" * len(noms) * 400, avis)
