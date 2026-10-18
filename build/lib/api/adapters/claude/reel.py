"""API Claude réelle (https://api.anthropic.com, x-api-key + anthropic-version), via httpx.

La clé n'apparaît jamais dans un log ni dans un message d'erreur.
"""
from __future__ import annotations

import base64
import json
import mimetypes
from pathlib import Path

from api.adapters import _commun
from api.adapters.claude.base import Claude

BASE_URL = "https://api.anthropic.com"
VERSION_API = "2023-06-01"
MAX_TOKENS = 16000


class ClaudeReel(Claude):
    mode = "reel"

    def __init__(self, config: dict) -> None:
        claude = config.get("services", {}).get("claude", {})
        self._cle = str(claude.get("cle_api", "") or "")
        self.modele = str(claude.get("modele", "claude-sonnet-5-5"))
        self.base_url = str(claude.get("url", BASE_URL) or BASE_URL)

    def _client(self, timeout: float = _commun.TIMEOUT_S):
        if not self._cle:
            raise RuntimeError("clé API Claude absente : renseigne-la dans Réglages")
        return _commun.client_http(timeout, base_url=self.base_url, headers={
            "x-api-key": self._cle, "anthropic-version": VERSION_API, "content-type": "application/json"})

    def tester_connexion(self) -> dict:
        try:
            with self._client() as c:
                r = c.get("/v1/models")
                r.raise_for_status()
                modeles = [m.get("id") for m in r.json().get("data", [])]
        except Exception as e:  # noqa: BLE001 - un test de connexion répond toujours
            return _commun.resultat_test(False, "Erreur", f"API Claude : {_commun.erreur_http(e)}")
        ok_modele = self.modele in modeles
        message = f"API Claude : {len(modeles)} modèle{'s' if len(modeles) > 1 else ''} accessible"
        if not ok_modele:
            message += f" ; le modèle réglé ({self.modele}) n'est pas dans la liste"
        return _commun.resultat_test(True, "Connecté", message,
                                     {"mode": "reel", "modeles": modeles, "modele": self.modele})

    def _messages(self, corps: dict, timeout: float = 300) -> tuple[dict, dict]:
        with self._client(timeout) as c:
            r = c.post("/v1/messages", json={"model": self.modele, "max_tokens": MAX_TOKENS, **corps})
            r.raise_for_status()
            data = r.json()
        if data.get("stop_reason") == "refusal":
            raise RuntimeError("l'API Claude a refusé la demande")
        usage = data.get("usage", {})
        return data, {"tokens_entree": int(usage.get("input_tokens", 0)),
                      "tokens_sortie": int(usage.get("output_tokens", 0)), "modele": data.get("model", self.modele)}

    @staticmethod
    def _texte(data: dict) -> str:
        return "".join(b.get("text", "") for b in data.get("content", []) if b.get("type") == "text")

    def completer_json(self, system: str, user: str, schema: dict) -> tuple[dict, dict]:
        data, usage = self._messages({
            "system": system,
            "messages": [{"role": "user", "content": user}],
            "output_config": {"format": {"type": "json_schema", "schema": schema}},
        })
        return json.loads(self._texte(data)), usage

    def avis_rendus(self, images: list[str | Path], contexte: str) -> tuple[str, dict]:
        contenu = []
        for img in images:
            p = Path(str(img))
            mime = mimetypes.guess_type(p.name)[0] or "image/png"
            contenu.append({"type": "image", "source": {"type": "base64", "media_type": mime,
                                                        "data": base64.b64encode(p.read_bytes()).decode("ascii")}})
        contenu.append({"type": "text", "text": contexte})
        data, usage = self._messages({"messages": [{"role": "user", "content": contenu}]})
        return self._texte(data), usage
