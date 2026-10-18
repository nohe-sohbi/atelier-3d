"""Outils sur la machine : règle de chemin, détection de Blender, tests d'outils avec des fakes."""
from pathlib import Path
from subprocess import CompletedProcess

import pytest

from api.services import outils


def _fichier(p: Path) -> Path:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("")
    return p


def test_resoudre_chemin(tmp_path):
    exe = _fichier(tmp_path / "outil")
    assert outils.resoudre_chemin(str(exe)) == str(exe)
    assert outils.resoudre_chemin(str(tmp_path / "absent")) is None  # un chemin doit exister
    assert outils.resoudre_chemin("") is None and outils.resoudre_chemin(None) is None
    assert outils.resoudre_chemin("commande", which=lambda n: f"/bin/{n}") == "/bin/commande"
    assert outils.resoudre_chemin("commande", which=lambda n: None) is None


def test_detecter_blender_path_d_abord(tmp_path):
    assert outils.detecter_blender("linux", which=lambda n: "/usr/bin/blender", environ={}, home=tmp_path) == "/usr/bin/blender"


def test_detecter_blender_windows_version_attendue_d_abord(tmp_path):
    pf = tmp_path / "Program Files"
    _fichier(pf / "Blender Foundation" / "Blender 4.2" / "blender.exe")
    cinq = _fichier(pf / "Blender Foundation" / "Blender 5.2" / "blender.exe")
    environ = {"ProgramFiles": str(pf), "LOCALAPPDATA": str(tmp_path / "Local")}
    assert outils.detecter_blender("win32", which=lambda n: None, environ=environ, home=tmp_path) == str(cinq)
    cinq.unlink()
    # Sans 5.2 : la plus récente des autres installations, puis rien
    assert outils.detecter_blender("win32", which=lambda n: None, environ=environ, home=tmp_path).endswith("Blender 4.2/blender.exe")
    _fichier(tmp_path / "Local" / "Programs" / "Blender Foundation" / "Blender 5.1" / "blender.exe")
    (pf / "Blender Foundation" / "Blender 4.2" / "blender.exe").unlink()
    assert "Blender 5.1" in outils.detecter_blender("win32", which=lambda n: None, environ=environ, home=tmp_path)


def test_detecter_blender_macos_et_linux(tmp_path, monkeypatch):
    app = _fichier(tmp_path / "Applications" / "Blender.app" / "Contents" / "MacOS" / "Blender")
    assert outils.detecter_blender("darwin", which=lambda n: None, environ={}, home=tmp_path) == str(app)
    candidats = outils.candidats_blender("linux", {}, tmp_path)
    assert tmp_path / ".local" / "share" / "flatpak" / "exports" / "bin" / "org.blender.Blender" in candidats
    assert Path("/snap/bin/blender") in candidats and Path("/usr/bin/blender") in candidats
    # Détection isolée de la machine : seuls des candidats sous tmp_path
    flatpak = _fichier(tmp_path / ".local" / "share" / "flatpak" / "exports" / "bin" / "org.blender.Blender")
    monkeypatch.setattr(outils, "candidats_blender", lambda plateforme, environ, home: [home / "absent", flatpak])
    assert outils.detecter_blender("linux", which=lambda n: None, environ={}, home=tmp_path) == str(flatpak)
    flatpak.unlink()
    assert outils.detecter_blender("linux", which=lambda n: None, environ={}, home=tmp_path) is None


def _lancer_factice(stdout="", code=0):
    def lancer(args, timeout, cwd=None):
        return CompletedProcess(args, code, stdout=stdout, stderr="")
    return lancer


def test_tester_blender_introuvable():
    r = outils.tester_blender({"blender": {"chemin": ""}})
    assert r["ok"] is False and r["etat"] == "Introuvable" and "suggestion" in r["details"]
    r = outils.tester_blender({"blender": {"chemin": "/nulle/part/blender"}})
    assert r["etat"] == "Introuvable" and "/nulle/part/blender" in r["message"]


def test_tester_blender_versions(tmp_path):
    exe = _fichier(tmp_path / "blender")
    cfg = {"blender": {"chemin": str(exe)}}
    r = outils.tester_blender(cfg, lancer=_lancer_factice("Blender 5.2.2 LTS\n\tbuild date: 2026-09-01"))
    assert r["ok"] is True and r["etat"] == "Détecté" and r["details"]["version_ok"] is True
    assert r["message"] == "Blender 5.2.2 LTS"
    r = outils.tester_blender(cfg, lancer=_lancer_factice("Blender 4.2.1"))
    assert r["ok"] is True and r["details"]["version_ok"] is False and "attend Blender 5.2" in r["message"]
    r = outils.tester_blender(cfg, lancer=_lancer_factice("", code=1))
    assert r["ok"] is False and r["etat"] == "Erreur"


def test_tester_gltf_validator(tmp_path):
    assert outils.tester_gltf_validator({"gltf_validator": {"chemin": "/nulle/part"}})["etat"] == "Introuvable"
    exe = _fichier(tmp_path / "gltf_validator")
    r = outils.tester_gltf_validator({"gltf_validator": {"chemin": str(exe)}}, lancer=_lancer_factice("2.0.0-dev.3.9"))
    assert r["ok"] is True and r["details"]["version"] == "2.0.0"


def test_extensions_lfs(tmp_path):
    ga = tmp_path / ".gitattributes"
    ga.write_text("*.blend filter=lfs diff=lfs merge=lfs -text\n*.glb filter=lfs diff=lfs merge=lfs -text\n*.txt text\n")
    assert outils.extensions_lfs(ga) == [".blend", ".glb"]
    assert outils.extensions_lfs(tmp_path / "absent") == []


def test_tester_git_lfs(tmp_path):
    git = lambda n: "/usr/bin/git" if n == "git" else None
    r = outils.tester_git_lfs(tmp_path, lancer=_lancer_factice(), which=lambda n: None)
    assert r["etat"] == "Introuvable" and "git introuvable" in r["message"]

    def lfs_absent(args, timeout, cwd=None):
        return CompletedProcess(args, 1 if args[1:3] == ["lfs", "version"] else 0, stdout="", stderr="git: 'lfs' is not a git command")
    assert outils.tester_git_lfs(tmp_path, lancer=lfs_absent, which=git)["etat"] == "Introuvable"

    def lfs_non_active(args, timeout, cwd=None):
        return CompletedProcess(args, 0, stdout="git-lfs/3.4.1 (GitHub; linux amd64)" if "version" in args else "", stderr="")
    r = outils.tester_git_lfs(tmp_path, lancer=lfs_non_active, which=git)
    assert r["ok"] is False and r["etat"] == "Erreur" and "git lfs install" in r["message"]

    def lfs_ok(args, timeout, cwd=None):
        return CompletedProcess(args, 0, stdout="git-lfs/3.4.1 (GitHub; linux amd64)" if "version" in args else "git-lfs clean -- %f", stderr="")
    r = outils.tester_git_lfs(tmp_path, lancer=lfs_ok, which=git)
    assert r["ok"] is False and ".blend" in r["message"]  # pas de .gitattributes
    (tmp_path / ".gitattributes").write_text("".join(f"*{e} filter=lfs diff=lfs merge=lfs -text\n" for e in outils.EXTENSIONS_LFS))
    r = outils.tester_git_lfs(tmp_path, lancer=lfs_ok, which=git)
    assert r["ok"] is True and r["etat"] == "Détecté" and r["details"]["version"] == "3.4.1"


def test_presence_outils(tmp_path):
    which = lambda n: "/usr/bin/" + n if n in ("git", "git-lfs", "butler") else None
    p = outils.presence_outils({"blender": {"chemin": ""}, "gltf_validator": {"chemin": "gltf_validator"}, "butler": {"chemin": "butler"}}, which=which)
    assert p["blender"]["present"] is False and "suggestion" in p["blender"]
    assert p["gltf_validator"] == {"present": False} and p["butler"] == {"present": True} and p["git_lfs"] == {"present": True}
    # Git LFS : git suffit à l'ouverture (git-lfs.exe hors PATH sous Git for Windows) ; le test au clic tranche
    sans_lfs = lambda n: "/usr/bin/git" if n == "git" else None
    assert outils.presence_outils({}, which=sans_lfs)["git_lfs"] == {"present": True}
    assert outils.presence_outils({}, which=lambda n: None)["git_lfs"] == {"present": False}


@pytest.mark.blender
def test_blender_reel_repond():
    """Ne tourne que sur une machine où Blender est dans le PATH."""
    if not outils.detecter_blender():
        pytest.skip("Blender non installé")
    assert outils.tester_blender({"blender": {"chemin": outils.detecter_blender()}})["ok"] is True
