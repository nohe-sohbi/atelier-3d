from pathlib import Path

import pytest

from pipeline import _cli, blender_run


@pytest.fixture(scope="module")
def config_bpy():
    cfg = _cli.charger_config()
    b = (cfg.get("blender") or {})
    if not (b.get("chemin") or b.get("python_bpy")):
        pytest.skip("ni blender.chemin ni blender.python_bpy dans config.local.yaml")
    return cfg


def test_blender_introuvable():
    with pytest.raises(blender_run.BlenderIntrouvable):
        blender_run.run_script("x.py", [], {"blender": {"chemin": "", "python_bpy": ""}})
    with pytest.raises(blender_run.BlenderIntrouvable):
        blender_run.run_script("x.py", [], {"blender": {"python_bpy": "/nulle/part/python"}})


def test_commande_selon_config(tmp_path):
    exe = tmp_path / "blender"
    exe.write_text("")
    cmd = blender_run.commande("s.py", ["--a", "1"], {"blender": {"chemin": str(exe)}})
    assert cmd == [str(exe), "-b", "--factory-startup", "-P", "s.py", "--", "--a", "1"]
    cmd = blender_run.commande("s.py", ["--a"], {"blender": {"chemin": "", "python_bpy": str(exe)}})
    assert cmd == [str(exe), "s.py", "--", "--a"]


def test_run_script_trivial(tmp_path, config_bpy):
    script = tmp_path / "trivial.py"
    script.write_text(
        "import bpy, sys\n"
        "from pipeline._cli import args_apres_double_tiret\n"
        "print('ARGS', args_apres_double_tiret())\n"
        "print('VERSION', bpy.app.version_string)\n"
    )
    r = blender_run.run_script(script, ["--x", "42"], config_bpy, timeout=120)
    assert r.code == 0, r.stderr
    assert "VERSION 5." in r.stdout and "ARGS ['--x', '42']" in r.stdout
    assert r.duree_s > 0


def test_version_blender(config_bpy):
    assert blender_run.version_blender(config_bpy).startswith("5.")


def test_args_apres_double_tiret():
    assert _cli.args_apres_double_tiret(["blender", "-b", "-P", "s.py", "--", "--a", "1"]) == ["--a", "1"]
    assert _cli.args_apres_double_tiret(["s.py", "--a"]) == ["--a"]
