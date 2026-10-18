
import pytest

from api import config as cfgmod
from api.adapters import get_claude, get_comfyui, get_itchio, get_meshy
from api.adapters.claude.simule import _exemple


def test_meshy_simule_solde_et_3d(atelier, cfg, tmp_path):
    m = get_meshy(cfg)
    assert m.mode == "simule" and m.solde() == {"restants": 1000, "total": 1000}
    tid = m.image_vers_3d("ref.png", {"topology": "quad"})
    assert tid.startswith("sim-3d-") and m.solde()["restants"] == 970
    etats = [m.etat_tache(tid) for _ in range(3)]
    assert [e["status"] for e in etats] == ["IN_PROGRESS", "IN_PROGRESS", "SUCCEEDED"]
    assert etats[0]["progress"] < etats[1]["progress"] < etats[2]["progress"] == 100
    assert etats[2]["model_urls"]["glb"]
    glb = m.telecharger(tid, tmp_path / "sortie")
    assert glb.exists() and glb.suffix == ".glb" and glb.read_bytes()[:4] == b"glTF"
    import trimesh
    scene = trimesh.load(glb)
    assert len(scene.geometry) == 1
    # Solde conservé sur disque : un nouvel adaptateur relit le même état.
    assert get_meshy(cfg).solde()["restants"] == 970
    assert (atelier.lots / ".simule" / "meshy.json").exists()


def test_meshy_simule_deterministe_et_images(atelier, cfg, tmp_path):
    a = get_meshy(cfg, tmp_path / "a")
    b = get_meshy(cfg, tmp_path / "b")
    assert a.image_vers_3d("x.png") == b.image_vers_3d("x.png")
    assert a.image_vers_image("un scutum", "x.png", 4) == b.image_vers_image("un scutum", "x.png", 4)
    assert a.solde()["restants"] == 1000 - 30 - 12
    tid = a.image_vers_image("un casque", None, 2)
    with pytest.raises(RuntimeError):
        a.telecharger(tid, tmp_path / "img")
    while a.etat_tache(tid)["status"] != "SUCCEEDED":
        pass
    dossier = a.telecharger(tid, tmp_path / "img")
    assert sorted(p.name for p in dossier.iterdir()) == [f"{tid}_1.png", f"{tid}_2.png"]
    with pytest.raises(LookupError):
        a.etat_tache("inconnue")


def test_claude_simule_json_et_usage(cfg):
    c = get_claude(cfg)
    schema = {"type": "object", "properties": {
        "objets": {"type": "array", "minItems": 3, "items": {"type": "object", "properties": {
            "nom": {"type": "string"}, "voie": {"enum": ["code", "ia"]}, "tris": {"type": "integer"},
            "ok": {"type": "boolean"}}}},
        "resume": {"type": "string"}}}
    rep, usage = c.completer_json("Tu listes des objets.", "Un forum romain", schema)
    assert len(rep["objets"]) == 3 and rep["objets"][0]["voie"] == "code" and rep["objets"][0]["ok"] is True
    assert isinstance(rep["resume"], str)
    assert usage["tokens_entree"] > 0 and usage["tokens_sortie"] > 0 and usage["modele"] == "claude-sonnet-5-5"
    assert c.completer_json("a", "b", schema)[0] == rep  # déterministe
    avis, usage2 = c.avis_rendus(["face.png", "trois-quarts.png"], "Scutum, style ROM")
    assert "2 rendus" in avis and usage2["tokens_entree"] > usage["tokens_entree"]
    assert c.tester_connexion()["etat"] == "Connecté"
    assert _exemple({"type": "number", "minimum": 2}) == 2.0


def test_comfyui_simule(cfg, tmp_path):
    c = get_comfyui(cfg)
    t = c.tester_connexion()
    assert t["ok"] and t["etat"] == "Joignable" and "Pixal3D" in t["details"]["modeles"]
    pid = c.lancer_workflow({"3": {"class_type": "LoadImage"}})
    assert c.etat(pid)["status"] == "en_cours"
    with pytest.raises(RuntimeError):
        c.recuperer_fichiers(pid, tmp_path)
    assert c.etat(pid)["status"] == "termine"
    fichiers = c.recuperer_fichiers(pid, tmp_path)
    assert [f.suffix for f in fichiers] == [".glb", ".png"] and all(f.exists() for f in fichiers)


def test_itchio_simule(cfg, tmp_path, atelier):
    i = get_itchio(cfg)
    assert i.tester_butler()["etat"] == "Connecté"
    (tmp_path / "pack").mkdir()
    (tmp_path / "pack" / "a.glb").write_bytes(b"glTF")
    r = i.pousser(tmp_path / "pack", "nohe/rome-antique", "html")
    assert r["ok"] and r["fichiers"] == 1 and r["build_id"].startswith("sim-build-")
    with pytest.raises(FileNotFoundError):
        i.pousser(tmp_path / "absent", "x/y", "html")


def test_mode_reel_choisit_les_adaptateurs_reels(cfg):
    for s in ("meshy", "claude", "comfyui", "itchio"):
        cfg["services"][s]["mode"] = "reel"
    assert get_meshy(cfg).mode == get_claude(cfg).mode == get_comfyui(cfg).mode == get_itchio(cfg).mode == "reel"
    assert get_meshy(cfg).tester_connexion()["ok"] is False  # pas de clé → refus propre, sans réseau
    assert get_claude(cfg).tester_connexion()["ok"] is False
    assert get_itchio(cfg).tester_butler()["etat"] == "Erreur" or cfgmod.service(cfg, "itchio")  # butler absent ici


def test_apercu_cle():
    assert cfgmod.apercu_cle("") == "" and cfgmod.apercu_cle("ab") == "••••" and cfgmod.apercu_cle("sk-ant-1234") == "••••1234"
