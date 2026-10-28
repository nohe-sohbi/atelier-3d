"""Écran Références (étape 6) : propositions par objet, consigne, image donnée, choix, lancement de la génération."""
import io
import json
import shutil

import pytest
from PIL import Image

from api import chemins, db
from api.adapters import get_meshy
from api.services import evenements, generateurs_registre, references, taches
from worker.main import Worker

BESOIN = "Des armes de légionnaire et un peu de mobilier."


def _worker_tourne(cfg, timeout=60):
    """Des passages du worker jusqu'à vider la file (il prend au plus N tâches par file à chaque passage)."""
    w = Worker(verrou="test", tick_s=0.05, backoff_base_s=0, charger_config=lambda: cfg)
    try:
        for _ in range(20):
            w.tour()
            assert w.attendre_fin(timeout)
            conn = db.connexion()
            try:
                if not db.une(conn, "SELECT 1 FROM taches WHERE etat = 'en_attente'"):
                    break
            finally:
                conn.close()
    finally:
        w.arreter(delai_s=1)


def _png(cote: int = 64) -> bytes:
    tampon = io.BytesIO()
    Image.new("RGB", (cote, cote), (181, 88, 46)).save(tampon, "PNG")
    return tampon.getvalue()


@pytest.fixture
def avec_scutum(atelier):
    shutil.copy(chemins.racine() / "generators" / "scutum.py", atelier.generateurs / "scutum.py")


def _lot_valide(client, cfg, garder_le_code=True):
    """Liste simulée proposée par le worker, « À créer » passés en IA, brief validé : les références se préparent."""
    lot = client.post("/api/lots", json={"theme": "Thème", "besoin": BESOIN}).json()
    client.post(f"/api/lots/{lot['id']}/proposition")
    _worker_tourne(cfg)
    for o in client.get(f"/api/lots/{lot['id']}/objets").json()["objets"]:
        if o["voie"] == "a_creer" or (o["voie"] == "code" and not garder_le_code):
            client.patch(f"/api/lots/{lot['id']}/objets/{o['id']}", json={"voie": "ia"})
    assert client.post(f"/api/lots/{lot['id']}/valider-brief").status_code == 200
    return lot["id"]


def _objets(client, lid):
    return {o["id"]: o for o in client.get(f"/api/lots/{lid}/references").json()["objets"]}


def test_valider_le_brief_prepare_4_propositions_par_objet(client, conn, cfg, avec_scutum):
    lid = _lot_valide(client, cfg)
    r = client.get(f"/api/lots/{lid}/references").json()
    assert r["objets"] and all(o["preparation"] and not o["propositions"] for o in r["objets"])
    types = {o["genre"]: t for o in r["objets"] for t in [taches.lire_tache(conn, o["preparation"]["tache_id"])]}
    assert types["variantes"]["file"] == "blender" and types["images"]["file"] == "meshy"
    assert r["credits_serie"] == 12 and r["meshy_simule"] is True and r["peut_lancer"] is False
    assert r["style"]["code"] == "rome-stylise-v0" and r["style"]["palette"]

    # Config de test sans Blender : les images IA arrivent, les variantes du scutum échouent avec un motif clair.
    _worker_tourne(cfg)
    objets = client.get(f"/api/lots/{lid}/references").json()["objets"]
    ia = [o for o in objets if o["genre"] == "images"]
    assert ia and all(len(o["propositions"]) == 4 and o["preparation"] is None and o["series"] == 1 for o in ia)
    assert all(p["simule"] and p["genre"] == "image" for o in ia for p in o["propositions"])
    img = client.get(ia[0]["propositions"][0]["url"])
    assert img.status_code == 200 and img.headers["content-type"] == "image/png"
    assert client.get("/api/fichiers/references/999").status_code == 404
    code = next(o for o in objets if o["genre"] == "variantes")
    assert code["erreur"] and "Blender" in code["erreur"]["message"] and code["propositions"] == []
    # Les crédits : 3 par image, rattachés au lot, marqués simulés.
    lignes = db.toutes(conn, "SELECT * FROM couts WHERE type = 'reference'")
    assert len(lignes) == 4 * len(ia) and all(c["credits"] == 3 and c["simule"] and c["lot_id"] == lid for c in lignes)
    # Pas de « Looks prêts » tant qu'un objet n'a pas ses propositions.
    assert not db.une(conn, "SELECT 1 FROM evenements WHERE type = ?", (evenements.REFERENCES_PRETES,))


def test_references_pretes_une_seule_notification(client, conn, cfg):
    lid = _lot_valide(client, cfg, garder_le_code=False)
    _worker_tourne(cfg)
    notifs = [n for n in client.get("/api/notifications").json()["notifications"] if n["type"] == evenements.REFERENCES_PRETES]
    assert len(notifs) == 1 and notifs[0]["lien"] == f"/lots/{lid}/references"
    oid = next(iter(_objets(client, lid)))
    client.post(f"/api/lots/{lid}/objets/{oid}/propositions", json={})
    _worker_tourne(cfg)
    assert db.une(conn, "SELECT COUNT(*) AS n FROM evenements WHERE type = ?", (evenements.REFERENCES_PRETES,))["n"] == 1
    e = client.get(f"/api/lots/{lid}").json()
    assert e["etape_courante"] == 2 and e["detail"].endswith("à choisir")


def test_quatre_autres_consigne_et_choix(client, conn, cfg):
    lid = _lot_valide(client, cfg, garder_le_code=False)
    _worker_tourne(cfg)
    o = next(iter(_objets(client, lid).values()))
    premiere = o["propositions"][1]["id"]
    assert client.put(f"/api/lots/{lid}/objets/{o['id']}/reference", json={"proposition_id": premiere}).json()["choix_id"] == premiere
    # Ta consigne : gardée, envoyée telle quelle à Meshy pour la série suivante.
    defaut = o["consigne"]
    assert "Rome antique stylisée" in defaut and o["consigne_modifiee"] is False
    r = client.put(f"/api/lots/{lid}/objets/{o['id']}/consigne", json={"consigne": "  Tonneau   cerclé de fer, bois sombre. "})
    assert r.json()["consigne"] == "Tonneau cerclé de fer, bois sombre." and r.json()["consigne_modifiee"] is True
    assert client.put(f"/api/lots/{lid}/objets/{o['id']}/consigne", json={"consigne": "x" * 1001}).status_code == 422
    r = client.post(f"/api/lots/{lid}/objets/{o['id']}/propositions", json={})
    assert r.status_code == 202 and r.json()["objet"]["preparation"]
    assert client.post(f"/api/lots/{lid}/objets/{o['id']}/propositions", json={}).status_code == 409  # déjà en préparation
    _worker_tourne(cfg)
    meshy = get_meshy(cfg).etat.charger()["taches"]
    apres = _objets(client, lid)[o["id"]]
    assert apres["series"] == 2 and [p["serie"] for p in apres["propositions"]] == [1, 2, 2, 2, 2]  # le choix reste visible
    assert apres["propositions"][0]["id"] == premiere and apres["propositions"][0]["choisie"] is True
    assert sum(1 for t in meshy.values() if t["entree"]["prompt"] == "Tonneau cerclé de fer, bois sombre.") == 4
    # Vide : la consigne de l'app revient.
    assert client.put(f"/api/lots/{lid}/objets/{o['id']}/consigne", json={"consigne": ""}).json()["consigne"] == defaut
    # Une proposition d'un autre objet : introuvable pour celui-ci.
    autre = next(x for x in _objets(client, lid).values() if x["id"] != o["id"])
    r = client.put(f"/api/lots/{lid}/objets/{o['id']}/reference", json={"proposition_id": autre["propositions"][0]["id"]})
    assert r.status_code == 404


def test_ton_image_choisie_puis_modele_de_4_images(client, conn, cfg, atelier):
    lid = _lot_valide(client, cfg, garder_le_code=False)
    _worker_tourne(cfg)
    o = next(iter(_objets(client, lid).values()))
    url = f"/api/lots/{lid}/objets/{o['id']}/image"
    assert client.post(url, files={"fichier": ("notes.txt", b"pas une image", "text/plain")}).status_code == 422
    assert client.post(url, files={"fichier": ("faux.png", b"pas une image", "image/png")}).status_code == 422
    r = client.post(url, files={"fichier": ("minuscule.png", _png(16), "image/png")})
    assert r.status_code == 422 and "32 × 32 px au moins" in r.json()["erreur"]  # Meshy la refuserait
    r = client.post(url, files={"fichier": ("Mon croquis.PNG", _png(), "image/png")})
    assert r.status_code == 201
    perso = next(p for p in r.json()["propositions"] if p["genre"] == "perso")
    assert r.json()["choix_id"] == perso["id"] and perso["choisie"] and perso["legende"] == "Ton image" and not perso["simule"]
    assert client.get(perso["url"]).status_code == 200
    r = client.post(f"/api/lots/{lid}/objets/{o['id']}/propositions", json={"modele_id": perso["id"]})
    assert r.status_code == 202
    _worker_tourne(cfg)
    meshy = get_meshy(cfg).etat.charger()["taches"]
    guidees = [t for t in meshy.values() if t["entree"]["images"] and t["entree"]["images"][0].endswith("perso-1.png")]
    assert len(guidees) == 4  # ton image guide chacune des 4 images
    apres = _objets(client, lid)[o["id"]]
    assert [p["genre"] for p in apres["propositions"]] == ["image"] * 4 + ["perso"] and apres["choix_id"] == perso["id"]
    # Un objet code ne prend pas d'image : il se règle par ses variantes.
    assert client.post(f"/api/lots/{lid}/objets/{o['id']}/propositions", json={"modele_id": 999}).status_code == 404


def test_lancer_la_generation(client, conn, cfg, avec_scutum):
    lid = _lot_valide(client, cfg)
    assert client.post(f"/api/lots/{lid}/lancer").status_code == 409  # rien de choisi
    _worker_tourne(cfg)  # images IA ; les variantes Blender échouent ou réussissent selon la machine : peu importe ici
    objets = _objets(client, lid)
    ia = [o for o in objets.values() if o["genre"] == "images"]
    code = next(o for o in objets.values() if o["genre"] == "variantes")
    # La variante choisie du scutum, posée comme l'aurait rendue Blender.
    params = {"variante": "B", "motif": "foudre", "courbure": 0.35}
    pid = db.inserer(conn, "propositions", {"objet_id": code["id"], "serie": 1, "rang": 1, "genre": "variante", "fichier": "s1-2.png",
                                            "legende": "Motif foudre", "params_json": json.dumps(params), "credits": 0, "simule": 0,
                                            "cree_le": db.maintenant()})
    conn.commit()
    client.put(f"/api/lots/{lid}/objets/{code['id']}/reference", json={"proposition_id": pid})
    client.put(f"/api/lots/{lid}/objets/{ia[0]['id']}/reference", json={"proposition_id": ia[0]["propositions"][2]["id"]})
    en_file = client.post(f"/api/lots/{lid}/objets/{ia[0]['id']}/propositions", json={}).json()["tache_id"]
    r = client.post(f"/api/lots/{lid}/lancer")
    assert r.status_code == 202, r.text
    res = r.json()
    assert res["par_code"] == 1 and res["par_ia"] == 1 and len(res["taches"]) == 2  # Blender pour l'un, Meshy pour l'autre
    choisis = {code["id"], ia[0]["id"]}
    assert sorted(res["mis_de_cote"]) == sorted(o["nom"] for o in objets.values() if o["id"] not in choisis)
    essai = db.une(conn, "SELECT * FROM essais WHERE objet_id = ?", (code["id"],))
    assert json.loads(essai["params_json"]) == params  # la fabrication part de la variante choisie
    assert taches.lire_tache(conn, en_file)["etat"] == "annulee"  # des images qui ne serviraient plus
    lignes = {o["id"]: o for o in client.get(f"/api/lots/{lid}/objets").json()["objets"]}
    assert lignes[ia[0]["id"]]["etape"] == "generation"
    assert all(lignes[i]["retire"] for i in objets if i not in choisis)
    g = client.get(f"/api/lots/{lid}/generation").json()
    attente = next(x for x in g["objets"] if x["id"] == ia[0]["id"])
    assert attente["statut"] == "Génération en cours" and attente["etapes"][0]["etat"] == "en_cours"
    assert attente["vignette"] == f"/api/fichiers/references/{ia[0]['propositions'][2]['id']}"  # l'image choisie
    assert g["tuiles"]["en_cours"] == 2  # le scutum par Blender, l'objet IA par Meshy
    etapes = {e["cle"]: e["atteinte"] for e in client.get(f"/api/lots/{lid}").json()["etapes"]}
    assert etapes["generation"] is True
    # Lancé : le choix ne change plus, et une préparation relancée ne dépense rien.
    r = client.put(f"/api/lots/{lid}/objets/{ia[0]['id']}/reference", json={"proposition_id": ia[0]["propositions"][0]["id"]})
    assert r.status_code == 409 and "déjà lancé" in r.json()["erreur"]
    taches.relancer_tache(conn, en_file)
    _worker_tourne(cfg)
    t = taches.lire_tache(conn, en_file)
    assert t["etat"] == "echouee" and "ne serviraient plus" in t["erreur"]


def test_rouvrir_un_objet_code_en_echec(client, conn, cfg, avec_scutum):
    lid = _lot_valide(client, cfg)
    code = next(o for o in _objets(client, lid).values() if o["genre"] == "variantes")
    assert client.post(f"/api/lots/{lid}/objets/{code['id']}/rouvrir").status_code == 409  # pas encore lancé
    conn.execute("UPDATE objets SET etape = 'tests' WHERE id = ?", (code["id"],))
    db.inserer(conn, "essais", {"objet_id": code["id"], "numero": 1, "generateur": "scutum", "etat": "echec",
                                "erreur": "contrôles en échec", "dossier": f"{lid}/{code['id']}/essai-1"})
    conn.commit()
    g = next(x for x in client.get(f"/api/lots/{lid}/generation").json()["objets"] if x["id"] == code["id"])
    assert g["peut_rechoisir"] is True
    r = client.post(f"/api/lots/{lid}/objets/{code['id']}/rouvrir")
    assert r.status_code == 200 and r.json()["peut_changer"] is True and r.json()["etape"] == "references"


def test_variantes_candidates_rejouables():
    manifestes, _ = generateurs_registre.manifestes(chemins.racine() / "generators")
    m = manifestes["scutum"]
    s1 = references.variantes_candidates(m, 1)
    assert s1 == references.variantes_candidates(m, 1)  # mêmes paramètres, même résultat
    assert [p.get("variante") for p, _ in s1[:3]] == ["A", "B", "C"]  # les variantes nommées d'abord
    s2 = references.variantes_candidates(m, 2)
    assert s2 != s1 and all("variante" not in p for p, _ in s2)
    for p, _ in s2:
        assert "hauteur_m" not in p and "finesse" not in p  # tirages : dimensions du style et entiers gardés
    for p, _ in s1 + s2:
        for nom, v in p.items():
            schema = m["parametres"].get(nom)
            if schema and schema["type"] == "float":
                assert schema["min"] <= v <= schema["max"]
    assert references.legende(m, {"motif": "foudre", "courbure": 0.35}) == "Motif foudre · Courbure 0,35"
    assert references.legende(m, {}) == "Réglages par défaut"
    assert references.legende(m, {"umbo_rayon_m": 0.11}) == "Umbo rayon 0,11 m"


@pytest.mark.blender
def test_variantes_rendues_par_blender(client, conn, cfg, atelier):
    from api import config as cfgmod
    from api.services import outils
    from tests.conftest import ecrire_config

    chemin = outils.detecter_blender()
    if chemin is None:
        pytest.skip("Blender 5.2 introuvable sur cette machine")
    ecrire_config(atelier.config, lambda c: c["blender"].update({"chemin": chemin}))
    shutil.copy(chemins.racine() / "generators" / "caisse.py", atelier.generateurs / "caisse.py")
    lot = client.post("/api/lots", json={"theme": "Thème", "besoin": "x"}).json()
    lid = lot["id"]
    oid = db.inserer(conn, "objets", {"lot_id": lid, "nom": "Caisse", "type_objet": "caisse", "categorie": "prop_moyen",
                                      "voie": "code", "generateur": "caisse", "etape": "references"})
    conn.commit()
    tid = references.preparer(conn, cfgmod.charger(), lid, oid)
    _worker_tourne(cfgmod.charger(), timeout=300)
    t = taches.lire_tache(conn, tid)
    assert t["etat"] == "terminee", t["erreur"]
    o = _objets(client, lid)[oid]
    assert [p["genre"] for p in o["propositions"]] == ["variante"] * 4
    assert o["propositions"][0]["legende"].startswith("Cadre") or o["propositions"][0]["legende"] == "Réglages par défaut"
    for p in o["propositions"]:
        img = client.get(p["url"])
        assert img.status_code == 200 and Image.open(io.BytesIO(img.content)).size == (references.TAILLE_APERCU_PX,) * 2


def test_deux_apercus_identiques_sont_reconnus(tmp_path):
    """Un réglage qui ne change rien à l'image (cannelures d'une colonne lisse) ne fait pas une variante de plus."""
    from PIL import ImageDraw

    def apercu(nom, rectangle=None):
        im = Image.new("RGB", (384, 384), (158, 158, 153))
        ImageDraw.Draw(im).rectangle((150, 40, 230, 360), fill=(232, 227, 216))  # une colonne
        if rectangle:
            ImageDraw.Draw(im).rectangle(rectangle, fill=(200, 190, 170))
        im.save(tmp_path / nom)
        return references._signature(tmp_path / nom)

    lisse, encore = apercu("a.png"), apercu("b.png")
    chapiteau = apercu("c.png", (130, 30, 250, 52))  # un chapiteau : à peine 2 % de l'image
    assert references._meme_image(lisse, encore) and not references._meme_image(lisse, chapiteau)
