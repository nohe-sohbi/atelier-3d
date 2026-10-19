"""API Claude simulée : réponses déterministes plausibles, tokens comptés (≈ 4 caractères par token)."""
from __future__ import annotations

import json
import re
from pathlib import Path

from api.adapters import _commun
from api.adapters.claude.base import Claude

MODELES_SIMULES = ["claude-sonnet-5-5", "claude-haiku-5-5"]
_LISTE = re.compile(r"^(Types connus|Palette|Matériaux disponibles)\s*:\s*(.*?)\.?\s*$", re.MULTILINE)


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


def _liste_du_prompt(system: str, cle: str) -> list[str]:
    """Lit « <cle> : a, b, c » dans le prompt système ; [] si absent ou « aucun »."""
    for m in _LISTE.finditer(system):
        if m.group(1) == cle:
            valeurs = [v.strip() for v in re.split(r"[,;]", m.group(2)) if v.strip()]
            return [v for v in valeurs if v.lower() != "aucun"]
    return []


def _dims(graine: int, base: tuple[float, float, float]) -> dict:
    """Dimensions plausibles, déterministes, autour d'une base (± 20 %)."""
    out = {}
    for i, (cle, b) in enumerate(zip(("largeur", "profondeur", "hauteur"), base, strict=True)):
        facteur = 0.8 + ((graine >> (4 * i)) & 0xF) / 15 * 0.4
        out[cle] = round(b * facteur, 2)
    return out


def proposition_brief_simulee(system: str, user: str) -> dict:
    """Liste déterministe (empreinte du besoin) qui exerce toutes les natures : géométrique sur un type connu,
    géométrique sur un type inconnu (« à créer »), ornemental, mixte à 2 pièces, personnage.

    Les noms disent qu'ils sont simulés : rien ne ressemble à une vraie proposition."""
    graine = int(_commun.empreinte(user, longueur=8), 16)
    types_connus = _liste_du_prompt(system, "Types connus")
    materiaux = _liste_du_prompt(system, "Matériaux disponibles")
    mat = (materiaux or ["materiau"])[:2]
    n_connus = 1 + graine % 2  # 1 ou 2 objets sur des types connus
    objets = []

    def ajouter(nom, type_objet, nature, categorie, base, pieces=(), sym="X", famille="props", params=()):
        objets.append({
            "nom": f"Objet simulé {len(objets) + 1} ({nom})", "type_objet": type_objet,
            "description": f"Réponse simulée de l'API Claude : objet {nom} d'exemple, {categorie.replace('_', ' ')}. "
                           "En mode réel, Claude décrit ici l'objet demandé.",
            "categorie": categorie, "nature": nature, "symetrique": sym, "famille": famille,
            "dimensions_m": _dims(graine >> (3 * len(objets)), base), "materiaux": mat,
            "pieces": list(pieces), "parametres_suggeres": list(params),
        })

    for i, t in enumerate(types_connus[: n_connus]):
        ajouter("géométrique, type connu", t, "geometrique", "prop_moyen" if i == 0 else "petit_prop", (0.6, 0.4, 0.5),
                params=("largeur", "hauteur", "usure"))
    ajouter("géométrique, type inconnu", f"objet simule {graine % 97}", "geometrique", "grand_prop", (1.2, 0.4, 1.6),
            famille="mobilier", params=("emplacements", "hauteur", "usure"))
    ajouter("ornemental", f"ornement simule {graine % 89}", "ornemental", "prop_moyen", (0.4, 0.4, 0.9), sym=None,
            famille="contenants")
    ajouter("mixte", f"mixte simule {graine % 83}", "mixte", "module_archi", (0.6, 0.6, 4.0), famille="archi",
            pieces=({"nom": "Fût simulé", "nature": "geometrique", "type_objet": f"fut simule {graine % 83}"},
                    {"nom": "Chapiteau simulé", "nature": "ornemental", "type_objet": f"chapiteau simule {graine % 83}"}),
            params=("hauteur", "cannelures"))
    if graine % 3:
        ajouter("ornemental", f"decor simule {graine % 79}", "ornemental", "petit_prop", (0.3, 0.3, 0.3), sym=None)
    ajouter("personnage", f"personnage simule {graine % 73}", "personnage", "prop_moyen", (0.6, 0.4, 1.8), sym=None)
    return {"nom_lot": f"Lot simulé {_commun.empreinte(user, longueur=4)}", "objets": objets}


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
        if schema.get("title") == "proposition_brief":
            reponse: object = proposition_brief_simulee(system, user)
        else:
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
