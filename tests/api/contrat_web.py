"""Contrat interface/API : les réponses réelles de l'API, figées dans web/src/test/contrat.json.

Les tests de l'interface (Vitest) ne simulent l'API qu'avec ce fichier : si la forme d'une réponse
change côté Python, le fichier change aussi et les tests web le voient. C'est ce qui aurait évité la
page blanche de la cloche (interface codée contre un tableau, API répondant un objet).

    python -m tests.api.contrat_web --ecrire   # régénère web/src/test/contrat.json
    pytest tests/api/test_contrat_web.py        # vérifie qu'il est à jour

Les valeurs qui bougent (dates, texte de renouvellement) sont figées pour que le fichier soit stable.
"""
from __future__ import annotations

import copy
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path
from unittest import mock

RACINE = Path(__file__).resolve().parents[2]
CHEMIN_CONTRAT = RACINE / "web" / "src" / "test" / "contrat.json"
DATE_FIGEE = "2026-10-18T08:00:00Z"
RENOUVELLEMENT_FIGE = "Renouvelés le 1er novembre"
SERVICES_TESTES = ("meshy", "claude", "comfyui", "itchio", "blender", "gltf_validator")


def _remplir(conn, client) -> None:
    """Quelques lignes pour les variantes « #rempli » : des données de test, jamais montrées à l'utilisateur."""
    from api import config as cfgmod
    from api.adapters import get_meshy
    from api.services import evenements

    for nom, etat in (("Lot A", "en_cours"), ("Lot B", "en_cours"), ("Lot C", "en_cours"), ("Lot D", "termine")):
        conn.execute("INSERT INTO lots(nom, theme, etat, cree_le, maj_le) VALUES (?, 'TST', ?, ?, ?)",
                     (nom, etat, DATE_FIGEE, DATE_FIGEE))
    for aid, nom, statut in (("TST_PROP_Un_A", "Un", "garde"), ("TST_PROP_Deux_A", "Deux", "garde"),
                             ("TST_PROP_Trois_A", "Trois", "revue")):
        conn.execute("INSERT INTO assets(id, nom, theme, statut, cree_le, maj_le) VALUES (?, ?, 'TST', ?, ?, ?)",
                     (aid, nom, statut, DATE_FIGEE, DATE_FIGEE))
    conn.execute("INSERT INTO bancs(nom, generateur_a, generateur_b, etat, cree_le) VALUES ('banc', 'a', 'b', 'termine', ?)",
                 (DATE_FIGEE,))
    conn.execute("INSERT INTO collections(nom, couleur, epinglee) VALUES ('Collection test', '#B5582E', 1)")
    conn.execute("INSERT INTO collections(nom, couleur, epinglee) VALUES ('Non épinglée', '#000000', 0)")
    conn.execute("INSERT INTO collections_assets VALUES (1, 'TST_PROP_Un_A')")
    conn.execute("INSERT INTO collections_assets VALUES (1, 'TST_PROP_Deux_A')")
    conn.commit()
    meshy = get_meshy(cfgmod.charger())
    meshy.image_vers_3d("reference-1.png")  # 30 crédits simulés chacun
    meshy.image_vers_3d("reference-2.png")

    n1 = evenements.ecrire(conn, evenements.REVUE_PRETE, "Revue prête · Lot test", "4 objets à juger",
                           lien="/lots/1/revue")
    n2 = evenements.ecrire(conn, evenements.BANC_TERMINE, "Banc d'essai terminé", "", lien="/generateurs")
    assert n1 != n2
    evenements.marquer_lu(conn, n2)
    conn.commit()


def _faire_tourner_le_worker() -> None:
    """Un vrai passage du worker (adaptateurs simulés) : les réponses de tâches du contrat sont réelles."""
    from api import config as cfgmod
    from worker.main import Worker

    cfg = cfgmod.charger()
    w = Worker(verrou="contrat", tick_s=0.05, backoff_base_s=0, charger_config=lambda: cfg)
    try:
        w.tour()
        assert w.attendre_fin(30)
    finally:
        w.arreter(delai_s=1)


def _planche_et_taches(client, contrat: dict, pilote: int) -> None:
    """Un style créé, sa planche simulée rangée par le worker, une tâche terminée et une tâche échouée."""
    from api import db
    from api.services import taches

    contrat["GET /api/styles/estimation-planche"] = client.get("/api/styles/estimation-planche").json()
    palette = {c["nom"]: c["hex"] for c in contrat["GET /api/styles/{id}"]["palette"]}
    cree = client.post("/api/styles", json={"nom": "Médiéval stylisé", "description": "Formes simples.",
                                             "palette": palette, "budgets_depuis": pilote}).json()
    contrat["POST /api/styles"] = cree
    lance = client.post(f"/api/styles/{cree['id']}/planche").json()
    contrat["POST /api/styles/{id}/planche"] = lance
    _faire_tourner_le_worker()
    contrat["GET /api/taches/{id}"] = client.get(f"/api/taches/{lance['tache_id']}").json()
    contrat["GET /api/styles/{id}#planche"] = client.get(f"/api/styles/{cree['id']}").json()
    conn = db.connexion()
    try:
        echec = taches.creer_tache(conn, "echec", "api", {"message": "Meshy a échoué sur « caisse » : contenu refusé"},
                                   max_tentatives=1)
    finally:
        conn.close()
    _faire_tourner_le_worker()
    contrat["GET /api/taches/{id}#echouee"] = client.get(f"/api/taches/{echec}").json()


def _lots(client, contrat: dict, pilote: int) -> None:
    """Un lot de bout en bout : créé vide, brief rempli, liste proposée (Claude simulé, vrai worker), demande pour
    Claude Code, un objet décoché, un refus de validation, l'« À créer » passé en IA, brief validé ; puis une
    version plus récente du style, pour « Appliquer la v1 »."""
    lot = client.post("/api/lots", json={}).json()
    contrat["POST /api/lots"] = lot
    lid = lot["id"]
    contrat["PATCH /api/lots/{id}"] = client.patch(f"/api/lots/{lid}", json={
        "theme": "Thème de test", "besoin": "Un besoin de test : des contenants, du mobilier et un peu de décor."}).json()
    contrat["GET /api/lots/{id}"] = client.get(f"/api/lots/{lid}", params={"etape": "brief"}).json()
    contrat["GET /api/lots/{id}/objets"] = client.get(f"/api/lots/{lid}/objets").json()
    contrat["POST /api/lots/{id}/proposition"] = client.post(f"/api/lots/{lid}/proposition").json()
    _faire_tourner_le_worker()
    objets = client.get(f"/api/lots/{lid}/objets").json()
    contrat["GET /api/lots/{id}/objets#propose"] = objets
    contrat["GET /api/lots/{id}#propose"] = client.get(f"/api/lots/{lid}", params={"etape": "brief"}).json()
    a_creer = next(o for o in objets["objets"] if o["voie"] == "a_creer")
    autre = next(o for o in objets["objets"] if o["voie"] in ("code", "ia", "mixte") and not o["retire"])
    contrat["GET /api/lots/{id}/objets/{oid}/demande"] = client.get(f"/api/lots/{lid}/objets/{a_creer['id']}/demande").json()
    contrat["POST /api/lots/{id}/objets/{oid}/demande"] = client.post(f"/api/lots/{lid}/objets/{a_creer['id']}/demande").json()
    contrat["PATCH /api/lots/{id}/objets/{oid}"] = client.patch(f"/api/lots/{lid}/objets/{autre['id']}", json={"retenu": False}).json()
    contrat["GET /api/routage/regles"] = client.get("/api/routage/regles").json()
    contrat["POST /api/lots/{id}/valider-brief#409"] = client.post(f"/api/lots/{lid}/valider-brief").json()
    for o in objets["objets"]:
        if o["voie"] == "a_creer":
            contrat["PATCH /api/lots/{id}/objets/{oid}#ia"] = client.patch(f"/api/lots/{lid}/objets/{o['id']}", json={"voie": "ia"}).json()
    contrat["POST /api/lots/{id}/valider-brief"] = client.post(f"/api/lots/{lid}/valider-brief").json()
    contrat["GET /api/lots/{id}/generation"] = client.get(f"/api/lots/{lid}/generation").json()
    proposition = contrat["GET /api/lots/{id}/generation"]["taches"][0]["id"]
    contrat["GET /api/taches/{id}/journal"] = client.get(f"/api/taches/{proposition}/journal").json()
    contrat["GET /api/worker"] = client.get("/api/worker").json()
    contrat["GET /api/worker/taches"] = client.get("/api/worker/taches").json()
    contrat["GET /api/lots#rempli"] = client.get("/api/lots").json()
    contrat["POST /api/lots/{id}/dupliquer"] = client.post(f"/api/lots/{lid}/dupliquer").json()
    v1 = client.post(f"/api/styles/{pilote}/versions", json={"note": "Version de test"}).json()
    contrat["GET /api/lots/{id}#style_plus_recent"] = client.get(f"/api/lots/{lid}", params={"etape": "references"}).json()
    contrat["GET /api/lots/{id}/appliquer-style"] = client.get(f"/api/lots/{lid}/appliquer-style",
                                                               params={"style_id": v1["id"]}).json()


def _reglages_remplis(client, defaut: dict) -> dict:
    corps = copy.deepcopy({k: v for k, v in defaut.items() if k != "etat"})
    corps["services"]["meshy"]["cle_api"] = "msy-secret-ab12"
    corps["services"]["itchio"].update({"cle_api": "itch-secret-zz99", "compte": "mon-compte"})
    corps["outils"]["blender"]["chemin"] = "/usr/bin/blender"
    r = client.put("/api/reglages", json=corps)
    assert r.status_code == 200, r.text
    return r.json()


def generer() -> dict:
    """Interroge une API neuve dans un dossier temporaire et renvoie le contrat normalisé."""
    from fastapi.testclient import TestClient

    from api import chemins, db

    with tempfile.TemporaryDirectory() as tmp:
        racine = Path(tmp)
        config = racine / "config.local.yaml"
        shutil.copy(chemins.chemin_config_exemple(), config)
        (racine / "lots").mkdir()
        (racine / "generators").mkdir()
        shutil.copytree(chemins.racine() / "style" / "rome-stylise-v0", racine / "style" / "rome-stylise-v0")
        env = {"ATELIER_DB": str(racine / "atelier.db"), "ATELIER_CONFIG": str(config),
               "ATELIER_LOTS": str(racine / "lots"), "ATELIER_STYLES": str(racine / "style"),
               "ATELIER_GENERATEURS": str(racine / "generators")}
        # Machine figée : git présent, aucun autre outil (Blender, glTF-Validator, butler) ; le contrat ne dépend
        # pas de ce qui est installé là où il est généré ou vérifié.
        which_fige = lambda nom, *a, **k: "/usr/bin/git" if nom == "git" else None
        with mock.patch.dict(os.environ, env), mock.patch("api.db.maintenant", return_value=DATE_FIGEE), \
                mock.patch("shutil.which", which_fige), mock.patch("api.services.outils.detecter_blender", lambda *a, **k: None):
            db.initialiser()
            from api.main import create_app

            contrat: dict = {}
            with TestClient(create_app()) as client:
                contrat["GET /api/sante"] = client.get("/api/sante").json()
                contrat["GET /api/menu"] = client.get("/api/menu").json()
                contrat["GET /api/notifications"] = client.get("/api/notifications").json()
                contrat["GET /api/recherche?q="] = client.get("/api/recherche?q=").json()
                contrat["GET /api/reglages"] = client.get("/api/reglages").json()
                for service in SERVICES_TESTES:
                    contrat[f"POST /api/reglages/tester/{service}"] = client.post(f"/api/reglages/tester/{service}").json()
                contrat["GET /api/nexistepas"] = client.get("/api/nexistepas").json()
                contrat["GET /api/lots"] = client.get("/api/lots").json()
                contrat["GET /api/styles"] = client.get("/api/styles").json()
                pilote = contrat["GET /api/styles"]["styles"][0]["id"]
                contrat["GET /api/styles/{id}"] = client.get(f"/api/styles/{pilote}").json()

                conn = db.connexion()
                try:
                    _remplir(conn, client)
                finally:
                    conn.close()
                contrat["GET /api/menu#rempli"] = client.get("/api/menu").json()
                contrat["GET /api/notifications#rempli"] = client.get("/api/notifications").json()
                contrat["GET /api/reglages#rempli"] = _reglages_remplis(client, contrat["GET /api/reglages"])
                # En dernier : la planche dépense des crédits et l'échec écrit une notification.
                _planche_et_taches(client, contrat, pilote)
                _lots(client, contrat, pilote)
    return normaliser(contrat)


def normaliser(contrat: dict) -> dict:
    """Fige ce qui dépend du jour (texte de renouvellement de la jauge) et de la machine (durée d'une tâche)."""
    contrat = copy.deepcopy(contrat)
    for cle, valeur in contrat.items():
        if cle.startswith("GET /api/taches/") and isinstance(valeur.get("resultat"), dict) and "duree_s" in valeur["resultat"]:
            valeur["resultat"]["duree_s"] = 1.0
        if cle.startswith("GET /api/menu") and isinstance(valeur.get("credits"), dict) \
                and valeur["credits"].get("renouvellement"):
            valeur["credits"]["renouvellement"] = RENOUVELLEMENT_FIGE
    return contrat


def ecrire(chemin: Path = CHEMIN_CONTRAT) -> Path:
    chemin.write_text(json.dumps(generer(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return chemin


if __name__ == "__main__":
    if "--ecrire" in sys.argv:
        print(f"écrit : {ecrire()}")
    else:
        print(json.dumps(generer(), ensure_ascii=False, indent=2))
