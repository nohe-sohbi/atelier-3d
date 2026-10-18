#!/usr/bin/env python
"""Une seule commande : lance l'API (uvicorn, rechargement), le worker et l'interface Vite.

    python dev.py            # API + worker + Vite, puis ouvre http://127.0.0.1:5173
    python dev.py --sans-web # API + worker seulement (ou si l'interface est déjà construite)

Les logs de chaque processus sont relayés avec un préfixe ; Ctrl+C arrête tout proprement.
"""
from __future__ import annotations

import argparse
import os
import shutil
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path

RACINE = Path(__file__).resolve().parent
COULEURS = {"api": "\033[36m", "worker": "\033[33m", "web": "\033[35m"}
FIN = "\033[0m"


def _npm() -> str | None:
    return shutil.which("npm") or shutil.which("npm.cmd")


def _relayer(nom: str, proc: subprocess.Popen, couleur: bool) -> None:
    prefixe = f"{COULEURS.get(nom, '')}[{nom:<6}]{FIN} " if couleur else f"[{nom:<6}] "
    assert proc.stdout is not None
    for ligne in proc.stdout:
        sys.stdout.write(prefixe + ligne.rstrip("\n") + "\n")
        sys.stdout.flush()


def _lancer(nom: str, cmd: list[str], couleur: bool, env: dict | None = None) -> subprocess.Popen:
    kwargs = {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP} if os.name == "nt" else {"start_new_session": True}
    proc = subprocess.Popen(cmd, cwd=RACINE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                            encoding="utf-8", errors="replace", bufsize=1, env=env, **kwargs)
    threading.Thread(target=_relayer, args=(nom, proc, couleur), daemon=True).start()
    return proc


def _arreter(procs: dict[str, subprocess.Popen]) -> None:
    for nom, p in procs.items():
        if p.poll() is None:
            try:
                if os.name == "nt":
                    p.send_signal(signal.CTRL_BREAK_EVENT)
                else:
                    os.killpg(p.pid, signal.SIGINT)
            except (ProcessLookupError, OSError):
                pass
    limite = time.monotonic() + 20
    for nom, p in procs.items():
        try:
            p.wait(timeout=max(0.1, limite - time.monotonic()))
        except subprocess.TimeoutExpired:
            print(f"[dev   ] {nom} ne répond pas : arrêt forcé")
            p.kill()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Lance Atelier 3D en développement")
    parser.add_argument("--sans-web", action="store_true", help="ne lance pas Vite (npm run dev)")
    parser.add_argument("--port", type=int, default=8000, help="port de l'API")
    parser.add_argument("--sans-couleur", action="store_true")
    args = parser.parse_args(argv)
    couleur = not args.sans_couleur and sys.stdout.isatty()
    env = {**os.environ, "PYTHONUNBUFFERED": "1"}

    if not (RACINE / "config.local.yaml").exists():
        shutil.copy(RACINE / "config.local.example.yaml", RACINE / "config.local.yaml")
        print("[dev   ] config.local.yaml créé depuis l'exemple (tout en mode simulé)")

    procs: dict[str, subprocess.Popen] = {}
    procs["api"] = _lancer("api", [sys.executable, "-m", "api", "--port", str(args.port), "--reload"], couleur, env)
    procs["worker"] = _lancer("worker", [sys.executable, "-m", "worker"], couleur, env)
    adresse = f"http://127.0.0.1:{args.port}"
    if not args.sans_web:
        npm = _npm()
        if npm is None:
            print("[dev   ] npm introuvable : l'interface Vite n'est pas lancée (API seule)")
        elif not (RACINE / "web" / "node_modules").exists():
            print("[dev   ] web/node_modules absent : lance `npm --prefix web install` ; API seule")
        else:
            procs["web"] = _lancer("web", [npm, "--prefix", "web", "run", "dev"], couleur, env)
            adresse = "http://127.0.0.1:5173"
    time.sleep(1.5)
    print(f"\n[dev   ] Ouvre {adresse}   (API : http://127.0.0.1:{args.port}/api/sante ; Ctrl+C pour tout arrêter)\n")

    code = 0
    try:
        while True:
            for nom, p in procs.items():
                if p.poll() is not None:
                    print(f"[dev   ] {nom} s'est arrêté (code {p.returncode}) : arrêt de tout")
                    code = p.returncode or 1
                    raise KeyboardInterrupt
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\n[dev   ] arrêt…")
    finally:
        _arreter(procs)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
