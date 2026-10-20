"""Lancer Blender depuis l'app : rapport JSON, journal, erreurs, délai, arrêt."""
import pytest

from pipeline import blender


def test_sans_blender_erreur_claire(cfg, monkeypatch, tmp_path):
    cfg["blender"]["chemin"] = ""
    with pytest.raises(blender.BlenderIntrouvable, match="Réglages"):
        blender.lancer("version", {}, cfg, tmp_path)


@pytest.mark.blender
def test_version_reelle_et_journal(cfg_blender, tmp_path):
    r = blender.lancer("version", {}, cfg_blender, tmp_path)
    assert r["ok"] is True and r["version"].startswith("5.2") and r["duree_s"] > 0
    assert (tmp_path / "version.journal.txt").is_file() and (tmp_path / "version.entree.json").is_file()


@pytest.mark.blender
def test_une_erreur_du_script_remonte_avec_son_message(cfg_blender, tmp_path):
    with pytest.raises(blender.EchecBlender, match="commande inconnue") as e:
        blender.lancer("nexistepas", {}, cfg_blender, tmp_path)
    assert e.value.journal is not None and "Traceback" in e.value.journal.read_text(encoding="utf-8")


@pytest.mark.blender
def test_delai_depasse_et_arret(cfg_blender, tmp_path):
    with pytest.raises(blender.EchecBlender, match="délai dépassé"):
        blender.lancer("version", {}, cfg_blender, tmp_path, timeout=0.01)
    with pytest.raises(InterruptedError):
        blender.lancer("version", {}, cfg_blender, tmp_path, arret=lambda: True)
