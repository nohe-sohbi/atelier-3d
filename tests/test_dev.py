"""dev.py : la config du premier lancement est un YAML valide, même avec un chemin Windows ; ports déjà pris."""
import importlib
import socket
import threading

import yaml

from api import config as cfgmod
from api.services import outils

CHEMIN_WINDOWS = r"C:\Program Files\Blender Foundation\Blender 5.2\blender.exe"


def test_preparer_config_chemin_windows(atelier, monkeypatch):
    atelier.config.unlink()
    dev = importlib.import_module("dev")
    monkeypatch.setattr(outils, "detecter_blender", lambda *a, **k: CHEMIN_WINDOWS)
    chemin = dev.preparer_config()
    assert chemin == atelier.config
    assert yaml.safe_load(chemin.read_text(encoding="utf-8"))["blender"]["chemin"] == CHEMIN_WINDOWS
    assert cfgmod.charger()["blender"]["chemin"] == CHEMIN_WINDOWS
    assert "# Copie ce fichier" in chemin.read_text(encoding="utf-8")  # les commentaires de l'exemple sont gardés


def test_preparer_config_sans_blender(atelier, monkeypatch):
    atelier.config.unlink()
    dev = importlib.import_module("dev")
    monkeypatch.setattr(outils, "detecter_blender", lambda *a, **k: None)
    chemin = dev.preparer_config()
    assert yaml.safe_load(chemin.read_text(encoding="utf-8"))["blender"]["chemin"] == ""
    assert dev.preparer_config() == chemin  # déjà là : rien n'est réécrit


def _occuper_un_port() -> socket.socket:
    """Un port déjà écouté par « un autre programme », comme 8000 quand un autre service local le tient."""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("127.0.0.1", 0))
    s.listen()
    return s


def test_port_api_pris_par_un_autre_programme(monkeypatch):
    dev = importlib.import_module("dev")
    with _occuper_un_port() as occupe:
        port = occupe.getsockname()[1]
        monkeypatch.setattr(dev, "PORT_API", port)
        assert not dev.port_libre(port)
        choisi = dev.choisir_port_api(None)
        assert choisi != port and dev.port_libre(choisi)


def test_port_api_demande_deja_pris(atelier, capsys):
    dev = importlib.import_module("dev")
    with _occuper_un_port() as occupe:
        port = occupe.getsockname()[1]
        assert dev.choisir_port_api(port) is None
        assert dev.main(["--port", str(port), "--sans-navigateur"]) == 2
    assert f"le port {port} est déjà pris" in capsys.readouterr().out


def test_port_web_deja_pris(atelier, capsys):
    dev = importlib.import_module("dev")
    with _occuper_un_port() as occupe:
        port = occupe.getsockname()[1]
        assert dev.main(["--port-web", str(port), "--sans-navigateur"]) == 2
    assert f"le port {port} de l'interface est déjà pris" in capsys.readouterr().out


def test_le_worker_se_relance_quand_le_code_change(tmp_path):
    dev = importlib.import_module("dev")
    changement, arret = threading.Event(), threading.Event()
    t = threading.Thread(target=dev.surveiller_code, args=(changement, arret, (tmp_path,)), daemon=True)
    t.start()
    try:
        (tmp_path / "notes.txt").write_text("rien", encoding="utf-8")
        assert not changement.wait(2.5)  # un fichier qui n'est pas du Python : rien
        (tmp_path / "handler.py").write_text("TYPE = 'x'\n", encoding="utf-8")
        assert changement.wait(10)
    finally:
        arret.set()
        t.join(5)
