"""Écran Styles : lister, créer, modifier, dupliquer, planche simulée, valider, fichiers."""
import copy

import pytest
import yaml

from api import config as cfgmod
from api.adapters import get_meshy
from api.services import styles, taches
from worker.main import Worker

PALETTE = {"Chêne": "#8A6A45", "Fer": "#5B5F66", "Pierre": "#9A968D", "Rouge": "#A63A2E", "Lin": "#D9CBB0",
           "Or": "#C9A13B", "Bleu nuit": "#2B3A55", "Ivoire": "#F1EBDD"}


def _pilote(client):
    j = client.get("/api/styles").json()
    assert len(j["styles"]) == 1, j
    return j["styles"][0]


def test_le_style_pilote_est_importe_au_demarrage(client):
    s = _pilote(client)
    assert s["code"] == "rome-stylise-v0" and s["etat"] == "valide" and s["version"] == 0
    assert s["usage"] == {"lots": 0, "assets": 0} and len(s["palette"]) == 10
    d = client.get(f"/api/styles/{s['id']}").json()
    assert [b["libelle"] for b in d["budgets"]] == ["Petit objet", "Objet moyen", "Grand objet", "Module d'architecture"]
    assert d["budgets"][1]["tris"] == 6000 and d["texel_density"] == 512 and d["unite"] == "1 = 1 m"
    assert d["materiaux"][0]["usage_assets"] == 0 and d["planche"] == [] and d["peut_modifier"] is True
    assert d["versions"] == [{"id": s["id"], "code": "rome-stylise-v0", "version": 0, "note": "Version initiale du thème pilote.",
                              "date": d["cree_le"], "etat": "valide"}]
    assert "chemin" not in str(d)  # aucun chemin de la machine dans la réponse


def test_lister_vide_quand_aucun_style(client, atelier, conn):
    conn.execute("DELETE FROM styles")
    conn.commit()
    assert client.get("/api/styles").json() == {"styles": []}


def test_creer_depuis_un_style_de_reference(client, atelier):
    pilote = _pilote(client)
    r = client.post("/api/styles", json={"nom": "Médiéval stylisé", "description": "Formes simples.",
                                         "palette": PALETTE, "budgets_depuis": pilote["id"]})
    assert r.status_code == 201, r.text
    d = r.json()
    assert d["code"] == "medieval-stylise-v0" and d["etat"] == "brouillon" and d["version"] == 0
    assert d["budgets"][0]["tris"] == 2000 and d["dimensions_m"]["scutum"] == [0.65, 0.2, 1.1]
    # un matériau par couleur ; « fer », « lin » et « pierre » reprennent nom et réglages du style de référence
    assert {m["base"] for m in d["materiaux"]} == {styles.slug(k).replace("-", "_") for k in PALETTE} and len(d["materiaux"]) == 8
    assert {m["nom"] for m in d["materiaux"]} >= {"fer", "tissu", "pierre", "chene", "or"}
    assert next(m for m in d["materiaux"] if m["nom"] == "fer")["metallic"] == 1.0
    fichier = atelier.styles / "medieval-stylise-v0" / "style.yaml"
    brut = yaml.safe_load(fichier.read_text(encoding="utf-8"))
    assert brut["style"] == "medieval-stylise-v0" and brut["theme"] == "ROM" and brut["description"] == "Formes simples."
    assert {s["code"] for s in client.get("/api/styles").json()["styles"]} == {"rome-stylise-v0", "medieval-stylise-v0"}


def test_creer_refuse_palette_trop_courte_et_code_pris(client):
    pilote = _pilote(client)
    r = client.post("/api/styles", json={"nom": "X", "palette": dict(list(PALETTE.items())[:6]), "budgets_depuis": pilote["id"]})
    assert r.status_code == 422 and r.json()["erreur"] == "Valeurs invalides"
    r = client.post("/api/styles", json={"nom": "X", "palette": {**PALETTE, "Mauvais": "rouge"}, "budgets_depuis": pilote["id"]})
    assert r.status_code == 422 and "Style invalide" in r.json()["erreur"]
    r = client.post("/api/styles", json={"nom": "Rome antique stylisée", "code": "rome-stylise-v0", "palette": PALETTE,
                                         "budgets_depuis": pilote["id"]})
    assert r.status_code == 409
    r = client.post("/api/styles", json={"nom": "Sans référence", "palette": PALETTE})
    assert r.status_code == 422 and "dimensions_m" in r.json()["erreur"]


def test_creer_a_la_main(client):
    r = client.post("/api/styles", json={
        "nom": "Science-fiction propre", "palette": PALETTE, "direction": "semi_realiste", "texel_density": 1024,
        "budgets": {"petit_prop": 4000, "prop_moyen": 12000, "grand_prop": 30000, "module_archi": 16000},
        "dimensions_m": {"caisse": [0.6, 0.4, 0.4]}})
    assert r.status_code == 201, r.text
    d = r.json()
    assert d["direction"] == "semi_realiste" and d["budgets"][2]["tris"] == 30000 and d["texel_density"] == 1024
    assert d["objets_planche"] == ["caisse"]


def test_modifier_puis_refus_si_un_lot_utilise(client, conn):
    pilote = _pilote(client)
    r = client.put(f"/api/styles/{pilote['id']}", json={"description": "Nouvelle description", "budgets_tris": {
        "petit_prop": 2500, "prop_moyen": 6000, "grand_prop": 15000, "module_archi": 8000}})
    assert r.status_code == 200 and r.json()["budgets"][0]["tris"] == 2500 and r.json()["description"] == "Nouvelle description"
    r = client.put(f"/api/styles/{pilote['id']}", json={"palette": dict(list(PALETTE.items())[:3])})
    assert r.status_code == 422
    conn.execute("INSERT INTO lots(nom, theme, style_id, cree_le, maj_le) VALUES ('L', 'ROM', ?, 'x', 'x')", (pilote["id"],))
    conn.commit()
    r = client.put(f"/api/styles/{pilote['id']}", json={"description": "encore"})
    assert r.status_code == 409 and "duplique" in r.json()["erreur"]
    d = client.get(f"/api/styles/{pilote['id']}").json()
    assert d["peut_modifier"] is False and d["lots"] == [{"id": 1, "nom": "L"}] and d["usage"]["lots"] == 1


def test_dupliquer_en_v1_laisse_la_v0_intacte(client, conn, atelier):
    pilote = _pilote(client)
    conn.execute("INSERT INTO lots(nom, theme, style_id, cree_le, maj_le) VALUES ('L', 'ROM', ?, 'x', 'x')", (pilote["id"],))
    conn.commit()
    r = client.post(f"/api/styles/{pilote['id']}/versions", json={"note": "Palette plus chaude"})
    assert r.status_code == 201, r.text
    v1 = r.json()
    assert v1["code"] == "rome-stylise-v1" and v1["version"] == 1 and v1["parent_id"] == pilote["id"]
    assert v1["racine_id"] == pilote["id"] and v1["note_version"] == "Palette plus chaude" and v1["etat"] == "valide"
    assert [v["code"] for v in v1["versions"]] == ["rome-stylise-v0", "rome-stylise-v1"]
    assert (atelier.styles / "rome-stylise-v1" / "style.yaml").exists()
    # le lot reste sur la v0 ; la v1 est modifiable, pas la v0
    assert conn.execute("SELECT style_id FROM lots").fetchone()["style_id"] == pilote["id"]
    assert client.get(f"/api/styles/{pilote['id']}").json()["peut_modifier"] is False
    assert client.put(f"/api/styles/{v1['id']}", json={"description": "v1"}).status_code == 200
    assert yaml.safe_load((atelier.styles / "rome-stylise-v0" / "style.yaml").read_text())["version"] == 0
    r = client.post(f"/api/styles/{pilote['id']}/versions", json={})
    assert r.json()["code"] == "rome-stylise-v2"


def _worker_tourne(conn, cfg):
    w = Worker(verrou="test", tick_s=0.05, backoff_base_s=0, charger_config=lambda: cfg)
    try:
        w.tour()
        assert w.attendre_fin(30)
    finally:
        w.arreter(delai_s=1)


def test_planche_simulee_refaire_valider(client, conn, cfg, atelier):
    pilote = _pilote(client)
    r = client.post("/api/styles", json={"nom": "Planche test", "palette": PALETTE, "budgets_depuis": pilote["id"]})
    sid = r.json()["id"]
    assert client.post(f"/api/styles/{sid}/valider").status_code == 409  # rien à garder

    r = client.post(f"/api/styles/{sid}/planche")
    assert r.status_code == 202 and r.json()["credits_estimes"] == 18
    tid = r.json()["tache_id"]
    assert taches.lire_tache(conn, tid)["file"] == "meshy"
    _worker_tourne(conn, cfg)
    t = client.get(f"/api/taches/{tid}").json()
    assert t["etat"] == "terminee", t
    d = client.get(f"/api/styles/{sid}").json()
    assert len(d["planche"]) == 6 and all(i["simule"] and not i["gardee"] and i["credits"] == 3 for i in d["planche"])
    assert [i["objet"] for i in d["planche"]] == ["caisse", "amphore", "lampe", "banc", "casque", "table"]
    assert d["credits_planche"] == 18
    assert get_meshy(cfg).solde()["restants"] == 1000 - 18  # même source que la jauge
    img = client.get(d["planche"][0]["url"])
    assert img.status_code == 200 and img.headers["content-type"] == "image/png"

    # Refaire la 2e image : 3 crédits, l'ancienne disparaît
    ancienne = d["planche"][1]
    r = client.post(f"/api/styles/{sid}/planche/{ancienne['id']}/refaire")
    assert r.status_code == 202 and r.json()["credits_estimes"] == 3
    _worker_tourne(conn, cfg)
    d = client.get(f"/api/styles/{sid}").json()
    assert len(d["planche"]) == 6 and ancienne["id"] not in [i["id"] for i in d["planche"]]
    assert d["credits_planche"] == 21 and not (atelier.styles / "planche-test-v0" / "board" / ancienne["fichier"]).exists()
    assert d["planche"][-1]["objet"] == "amphore"

    # Garder deux images puis valider
    for i in d["planche"][:2]:
        assert client.put(f"/api/styles/{sid}/planche/{i['id']}", json={"gardee": True}).status_code == 200
    d = client.post(f"/api/styles/{sid}/valider").json()
    assert d["etat"] == "valide" and d["valide_le"]
    brut = yaml.safe_load((atelier.styles / "planche-test-v0" / "style.yaml").read_text(encoding="utf-8"))
    assert len(brut["planche"]) == 2 and all((atelier.styles / "planche-test-v0" / "board" / f).exists() for f in brut["planche"])


def test_planche_credits_insuffisants_echec_sans_relance(client, conn, cfg, atelier):
    pilote = _pilote(client)
    sid = client.post("/api/styles", json={"nom": "Pauvre", "palette": PALETTE, "budgets_depuis": pilote["id"]}).json()["id"]
    get_meshy(cfg).image_vers_3d("x.png")  # 30 crédits
    cfg2 = copy.deepcopy(cfg)
    cfg2["services"]["meshy"]["credits_mensuels"] = 40  # il reste 10, la planche en veut 18
    cfgmod.enregistrer(cfg2)
    tid = client.post(f"/api/styles/{sid}/planche").json()["tache_id"]
    _worker_tourne(conn, cfgmod.charger())
    t = client.get(f"/api/taches/{tid}").json()
    assert t["etat"] == "echouee" and t["tentatives"] == 1 and "insuffisants" in t["erreur"]
    assert conn.execute("SELECT titre FROM evenements WHERE type = 'tache_echec_final'").fetchone()["titre"] == "Tâche planche_style impossible"


def test_fichiers_refusent_la_traversee(client):
    assert client.get("/api/fichiers/styles/rome-stylise-v0/board/..%2Fstyle.yaml").status_code == 404
    assert client.get("/api/fichiers/styles/rome-stylise-v0/autre/x.png").status_code == 404
    assert client.get("/api/fichiers/styles/rome-stylise-v0/board/absent.png").status_code == 404


def test_inspirations(client, atelier):
    pilote = _pilote(client)
    r = client.post(f"/api/styles/{pilote['id']}/inspirations", files=[("fichiers", ("ref 1.png", b"\x89PNG\r\n", "image/png")),
                                                                       ("fichiers", ("ref 1.png", b"\x89PNG\r\n", "image/png"))])
    assert r.status_code == 201 and r.json()["inspirations"] == ["ref-1-1.png", "ref-1.png"]
    assert client.get(f"/api/styles/{pilote['id']}").json()["inspirations"][0].endswith("/inspiration/ref-1-1.png")
    r = client.post(f"/api/styles/{pilote['id']}/inspirations", files=[("fichiers", ("x.txt", b"non", "text/plain"))])
    assert r.status_code == 422


def test_slug_et_codes():
    assert styles.slug("Médiéval stylisé !") == "medieval-stylise"
    assert styles.code_depuis_nom("Science-fiction propre") == "science-fiction-propre-v0"
    assert styles.base_du_code("rome-stylise-v12") == "rome-stylise"
    with pytest.raises(ValueError):
        styles.valider_code("Rome/../x")
