"""Meshy réel, sans réseau ni crédit : chaque appel est intercepté et comparé à la documentation de Meshy (21 oct. 2026).

Ce que ce fichier garantit avant le premier essai payant : les bons chemins, les bons champs, la clé dans l'en-tête et
jamais ailleurs, les images envoyées en data URI, les refus (clé, crédits, demande) qui ne se relancent pas, et les
réponses de Meshy (tâche, crédits consommés, GLB, images) bien lues.
"""
import base64
import json

import httpx
import pytest

from api.adapters import _commun
from api.adapters.meshy.base import RefusMeshy
from api.adapters.meshy.reel import MeshyReel
from api.services import fabrication_ia, style_yaml

CLE = "msy-cle-de-test-0000"


class FauxMeshy:
    """Répond comme api.meshy.ai d'après sa documentation ; garde chaque requête reçue."""

    def __init__(self):
        self.requetes: list[httpx.Request] = []
        self.etats: dict[str, dict] = {}
        self.refus: int | None = None

    def __call__(self, requete: httpx.Request) -> httpx.Response:
        self.requetes.append(requete)
        chemin = requete.url.path
        if requete.url.host == "fichiers.meshy.test":
            return httpx.Response(200, content=b"glTF-binaire" if chemin.endswith(".glb") else b"\x89PNG-image")
        if requete.headers.get("authorization") != f"Bearer {CLE}":
            return httpx.Response(401, json={"message": "Invalid API key"})
        if chemin == "/openapi/v1/balance":
            return httpx.Response(200, json={"balance": 958, "monthly_credits": 558, "permanent_credits": 400,
                                             "monthly_resets_at": 1793491200000})
        if requete.method == "POST":
            if self.refus:
                return httpx.Response(self.refus, json={"message": "Insufficient credits"})
            genre = chemin.rsplit("/", 1)[-1]
            tid = f"018a-{genre}-{len(self.etats)}"
            self.etats[tid] = {"genre": genre, "lectures": 0}
            return httpx.Response(202, json={"result": tid})
        tid = chemin.rsplit("/", 1)[-1]
        e = self.etats[tid]
        e["lectures"] += 1
        if e["lectures"] < 2:
            return httpx.Response(200, json={"id": tid, "status": "IN_PROGRESS", "progress": 40, "consumed_credits": 30})
        corps = {"id": tid, "status": "SUCCEEDED", "progress": 100, "task_error": {"message": ""}}
        if e["genre"] == "image-to-3d":
            corps.update({"consumed_credits": 30, "thumbnail_url": "https://fichiers.meshy.test/vignette.png",
                          "model_urls": {"glb": "https://fichiers.meshy.test/modele.glb"},
                          "texture_urls": [{"base_color": "https://fichiers.meshy.test/couleur.png"}]})
        else:
            corps.update({"consumed_credits": 3, "image_urls": ["https://fichiers.meshy.test/image.png"]})
        return httpx.Response(200, json=corps)


@pytest.fixture
def faux(monkeypatch):
    serveur = FauxMeshy()
    vrai = _commun.client_http

    def client_intercepte(timeout=_commun.TIMEOUT_S, **kwargs):
        return vrai(timeout, transport=httpx.MockTransport(serveur), **kwargs)

    monkeypatch.setattr(_commun, "client_http", client_intercepte)
    return serveur


def _meshy(cle=CLE) -> MeshyReel:
    return MeshyReel({"services": {"meshy": {"cle_api": cle, "credits_mensuels": 1000}}})


def _image(tmp_path):
    chemin = tmp_path / "reference.png"
    chemin.write_bytes(b"\x89PNG\r\n\x1a\n-une-image")
    return chemin


def test_solde_et_test_de_connexion(faux):
    assert _meshy().solde() == {"restants": 958, "total": 1000}
    assert _meshy().tester_connexion()["ok"] is True
    r = _meshy("mauvaise-cle").tester_connexion()
    assert r["ok"] is False and "mauvaise-cle" not in json.dumps(r)  # la clé ne fuit jamais dans un message


def test_image_vers_3d_suit_la_documentation(faux, tmp_path):
    style = style_yaml.charger(__import__("api.chemins", fromlist=["racine"]).racine() / "style" / "rome-stylise-v0" / "style.yaml")
    options = fabrication_ia.options_meshy(style, "prop_moyen")
    m = _meshy()
    tid = m.image_vers_3d(_image(tmp_path), options)
    envoi = faux.requetes[-1]
    assert envoi.method == "POST" and envoi.url.path == "/openapi/v1/image-to-3d"
    corps = json.loads(envoi.content)
    assert corps["image_url"].startswith("data:image/png;base64,")
    assert base64.b64decode(corps["image_url"].split(",", 1)[1]) == _image(tmp_path).read_bytes()
    # Les réglages de la doc : modèle, texture PBR 2K, remaillage en triangles au budget du style.
    assert {k: corps[k] for k in ("ai_model", "should_texture", "enable_pbr", "texture_resolution", "should_remesh",
                                  "topology", "target_polycount")} == {
        "ai_model": "latest", "should_texture": True, "enable_pbr": True, "texture_resolution": "2k",
        "should_remesh": True, "topology": "triangle", "target_polycount": 6000}
    assert 100 <= corps["target_polycount"] <= 300000  # plage acceptée par Meshy avec remaillage
    assert CLE not in envoi.content.decode()  # la clé voyage dans l'en-tête seulement
    assert m.etat_tache(tid)["status"] == "IN_PROGRESS"
    assert faux.requetes[-1].url.path == f"/openapi/v1/image-to-3d/{tid}"
    fini = m.etat_tache(tid)
    assert fini["status"] == "SUCCEEDED" and fini["consumed_credits"] == 30
    glb = m.telecharger(tid, tmp_path / "source")
    assert glb.suffix == ".glb" and glb.read_bytes() == b"glTF-binaire" and (tmp_path / "source" / f"{tid}.png").is_file()


def test_images_de_reference_suivent_la_documentation(faux, tmp_path):
    m = _meshy()
    tid = m.image_vers_image("Une amphore, Rome antique stylisée", [_image(tmp_path)] * 7)
    envoi = faux.requetes[-1]
    corps = json.loads(envoi.content)
    assert envoi.url.path == "/openapi/v1/image-to-image" and corps["ai_model"] == "nano-banana"
    assert len(corps["reference_image_urls"]) == 5 and all(u.startswith("data:image/png;base64,") for u in corps["reference_image_urls"])
    m.etat_tache(tid)
    assert faux.requetes[-1].url.path.startswith("/openapi/v1/image-to-image/")
    texte = m.image_vers_image("Une amphore")  # sans image : texte vers image
    assert faux.requetes[-1].url.path == "/openapi/v1/text-to-image" and texte.startswith("txt:")
    m.etat_tache(texte)
    assert faux.requetes[-1].url.path.startswith("/openapi/v1/text-to-image/")
    m.etat_tache(texte)
    dossier = m.telecharger(texte, tmp_path / "images")
    assert sorted(p.name for p in dossier.iterdir()) == [f"{texte.split(':', 1)[1]}_1.png"]


@pytest.mark.parametrize(("code", "motif"), [(400, "demande refusée"), (401, "clé API Meshy refusée"),
                                              (402, "crédits Meshy insuffisants")])
def test_un_refus_ne_se_relance_pas(faux, tmp_path, code, motif):
    faux.refus = code
    with pytest.raises(RefusMeshy, match=motif):
        _meshy().image_vers_3d(_image(tmp_path), {})


def test_trop_de_requetes_se_relance(faux, tmp_path):
    faux.refus = 429  # limite de débit : la file réessaie plus tard (pas un refus définitif)
    with pytest.raises(httpx.HTTPStatusError):
        _meshy().image_vers_3d(_image(tmp_path), {})


def test_sans_cle_refus_clair(faux, tmp_path):
    with pytest.raises(RefusMeshy, match="clé API Meshy absente"):
        _meshy("").image_vers_3d(_image(tmp_path), {})
