#!/usr/bin/env python
"""Une seule commande : lance l'API (uvicorn, rechargement), le worker et l'interface Vite, puis ouvre le navigateur.

    python dev.py                 # API + worker + Vite, ouvre http://127.0.0.1:5173
    python dev.py --sans-web      # API + worker (sert web/dist/ si l'interface a été construite)
    python dev.py --installer     # crée .venv, installe le paquet et les dépendances web, puis quitte

Au premier lancement : copie config.local.example.yaml vers config.local.yaml et y écrit le chemin de
Blender s'il est trouvé sur la machine. Les logs de chaque processus sont relayés avec un préfixe ;
Ctrl+C arrête tout proprement. Marche sous Windows, macOS et Linux ; relance de lui-même dans .venv.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import shutil
import signal
import socket
import subprocess
import sys
import threading
import time
import urllib.request
import webbrowser
from pathlib import Path

RACINE = Path(__file__).resolve().parent
VENV = RACINE / ".venv"
PYTHON_VENV = VENV / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
PORT_API = 8000
COULEURS = {"api": "\033[36m", "worker": "\033[33m", "web": "\033[35m"}
FIN = "\033[0m"


def dire(texte: str) -> None:
    print(f"[dev   ] {texte}", flush=True)


# --- environnement -----------------------------------------------------------

def _dans_venv() -> bool:
    """Vrai quand l'interpréteur courant est celui de .venv (sys.prefix, pas le lien symbolique de l'exécutable)."""
    try:
        return Path(sys.prefix).resolve() == VENV.resolve()
    except OSError:
        return False


def _relancer_dans_venv() -> None:
    """Si .venv existe et qu'on n'y est pas, on relance dev.py avec son Python et on attend sa fin :
    `python dev.py` marche depuis n'importe quel Python, sur toutes les plateformes (pas d'execv, qui
    sous Windows rendrait la console avant la fin)."""
    if PYTHON_VENV.exists() and not _dans_venv() and not os.environ.get("ATELIER_DEV_SANS_VENV"):
        env = {**os.environ, "ATELIER_DEV_SANS_VENV": "1"}
        raise SystemExit(subprocess.call([str(PYTHON_VENV), str(RACINE / "dev.py"), *sys.argv[1:]], cwd=RACINE, env=env))


def _python_312() -> list[str]:
    """Commande d'un Python 3.12 pour créer le venv."""
    if sys.version_info[:2] == (3, 12):
        return [sys.executable]
    if os.name == "nt" and shutil.which("py"):
        return ["py", "-3.12"]
    for nom in ("python3.12", "python3", "python"):
        if shutil.which(nom):
            return [nom]
    return [sys.executable]


def _npm() -> str | None:
    return shutil.which("npm") or shutil.which("npm.cmd")


def commandes_installation() -> list[list[str]]:
    pip = [str(PYTHON_VENV), "-m", "pip"]
    npm = _npm() or "npm"
    return [[*_python_312(), "-m", "venv", str(VENV)],
            [*pip, "install", "-e", ".[dev]"],
            [npm, "--prefix", "web", "ci", "--no-audit", "--no-fund"]]


def installer() -> int:
    for cmd in commandes_installation():
        dire("$ " + " ".join(cmd))
        r = subprocess.run(cmd, cwd=RACINE, check=False)
        if r.returncode != 0:
            dire(f"échec (code {r.returncode})")
            return r.returncode
    dire("installation terminée : lance `python dev.py`")
    return 0


def _verifier_installation() -> bool:
    manquants = [m for m in ("fastapi", "uvicorn", "yaml", "httpx") if importlib.util.find_spec(m) is None]
    if manquants:
        dire(f"dépendances absentes dans cet environnement ({', '.join(manquants)}). Installe-les avec :")
        for cmd in commandes_installation():
            print("    " + " ".join(cmd))
        print("    ou, en une fois : python dev.py --installer")
        return False
    return True


# --- configuration locale ----------------------------------------------------

def preparer_config() -> Path:
    """Crée config.local.yaml au premier lancement, avec le chemin de Blender s'il est trouvé."""
    from api import chemins
    from api.services import outils

    chemin = chemins.chemin_config()
    if chemin.exists():
        return chemin
    chemin.parent.mkdir(parents=True, exist_ok=True)
    texte = chemins.chemin_config_exemple().read_text(encoding="utf-8")
    blender = outils.detecter_blender()
    if blender:
        # La première clé `chemin: ""` du fichier d'exemple est celle de Blender. Valeur écrite en chaîne JSON :
        # c'est une chaîne YAML valide même avec les antislashs d'un chemin Windows.
        texte = texte.replace('  chemin: ""', f"  chemin: {json.dumps(blender)}", 1)
    chemin.write_text(texte, encoding="utf-8")
    dire(f"{chemin.name} créé depuis l'exemple (tout en mode simulé)")
    if blender:
        dire(f"Blender détecté : {blender}")
    else:
        dire("Blender introuvable sur cette machine : l'écran Réglages le dira (pastille Introuvable) ; "
             "colle le chemin de blender.exe dans Réglages une fois Blender 5.2 LTS installé")
    return chemin


# --- rechargement du worker ----------------------------------------------------

def surveiller_code(changement: threading.Event, arret: threading.Event,
                    dossiers: tuple[Path, ...] = (RACINE / "api", RACINE / "worker")) -> None:
    """Pose `changement` quand un .py change : uvicorn recharge l'API (--reload), le worker n'a pas d'équivalent."""
    try:
        from watchfiles import PythonFilter, watch
    except ImportError:
        dire("watchfiles absent : le worker ne se relance pas quand le code change")
        return
    for _ in watch(*dossiers, watch_filter=PythonFilter(), stop_event=arret):
        changement.set()


# --- ports -------------------------------------------------------------------

def port_libre(port: int) -> bool:
    """Vrai si on peut écouter sur 127.0.0.1:port (comme uvicorn : SO_REUSEADDR hors Windows)."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        if os.name != "nt":
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            s.bind(("127.0.0.1", port))
        except OSError:
            return False
        return True


def choisir_port_api(demande: int | None) -> int | None:
    """Port de l'API. Avec --port : ce port, ou None s'il est pris. Sans : 8000, ou un port libre donné par
    le système si 8000 sert déjà à un autre programme (l'interface joint l'API par le proxy de Vite)."""
    if demande is not None:
        return demande if port_libre(demande) else None
    if port_libre(PORT_API):
        return PORT_API
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


# --- processus ---------------------------------------------------------------

def _relayer(nom: str, proc: subprocess.Popen, couleur: bool) -> None:
    prefixe = f"{COULEURS.get(nom, '')}[{nom:<6}]{FIN} " if couleur else f"[{nom:<6}] "
    assert proc.stdout is not None
    for ligne in proc.stdout:
        sys.stdout.write(prefixe + ligne.rstrip("\n") + "\n")
        sys.stdout.flush()


def _lancer(nom: str, cmd: list[str], couleur: bool, env: dict) -> subprocess.Popen:
    kwargs = {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP} if os.name == "nt" else {"start_new_session": True}
    proc = subprocess.Popen(cmd, cwd=RACINE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                            encoding="utf-8", errors="replace", bufsize=1, env=env, **kwargs)
    threading.Thread(target=_relayer, args=(nom, proc, couleur), daemon=True).start()
    return proc


def _tuer_arbre(p: subprocess.Popen) -> None:
    """Arrêt forcé du processus et de ses enfants : sous Windows, `npm.cmd` n'est que cmd.exe, Vite (node) est dessous."""
    if os.name == "nt":
        subprocess.run(["taskkill", "/PID", str(p.pid), "/T", "/F"], capture_output=True, check=False)
    else:
        try:
            os.killpg(p.pid, signal.SIGKILL)
        except (ProcessLookupError, OSError):
            p.kill()


def _arreter(procs: dict[str, subprocess.Popen]) -> None:
    for p in procs.values():
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
            dire(f"{nom} ne répond pas : arrêt forcé")
            _tuer_arbre(p)


def _attendre_sante(url: str, delai_s: float, procs: dict[str, subprocess.Popen] | None = None) -> bool:
    """Attend que l'application réponde ; s'arrête tout de suite si l'API est morte entre-temps."""
    limite = time.monotonic() + delai_s
    while time.monotonic() < limite:
        if procs and any(p.poll() is not None for p in procs.values()):
            return False
        try:
            with urllib.request.urlopen(url, timeout=2) as r:
                if r.status == 200:
                    return True
        except OSError:
            pass
        time.sleep(0.5)
    return False


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Lance Atelier 3D en développement")
    parser.add_argument("--installer", action="store_true", help="crée .venv et installe tout, puis quitte")
    parser.add_argument("--sans-web", action="store_true", help="ne lance pas Vite (API seule)")
    parser.add_argument("--sans-navigateur", action="store_true", help="n'ouvre pas le navigateur")
    parser.add_argument("--port", type=int, default=None,
                        help=f"port de l'API (défaut {PORT_API}, ou un port libre si {PORT_API} est pris)")
    parser.add_argument("--port-web", type=int, default=5173, help="port de l'interface Vite (défaut 5173)")
    parser.add_argument("--sans-couleur", action="store_true")
    args = parser.parse_args(argv)

    if args.installer:
        return installer()
    _relancer_dans_venv()
    if not _verifier_installation():
        return 2
    if os.name == "nt":
        os.system("")  # active les séquences ANSI dans la console Windows
    couleur = not args.sans_couleur and sys.stdout.isatty()
    port_api = choisir_port_api(args.port)
    if port_api is None:
        dire(f"le port {args.port} est déjà pris : choisis-en un autre avec --port, ou retire --port")
        return 2
    if args.port is None and port_api != PORT_API:
        dire(f"le port {PORT_API} sert déjà à un autre programme : l'API prend le port {port_api}")
    if not args.sans_web and not port_libre(args.port_web):
        dire(f"le port {args.port_web} de l'interface est déjà pris (dev.py tourne déjà ?) : "
             "arrête l'autre programme, ou lance avec --port-web <port>")
        return 2
    env = {**os.environ, "PYTHONUNBUFFERED": "1", "ATELIER_API_PORT": str(port_api)}

    preparer_config()

    procs: dict[str, subprocess.Popen] = {}
    procs["api"] = _lancer("api", [sys.executable, "-m", "api", "--port", str(port_api), "--reload"], couleur, env)
    commande_worker = [sys.executable, "-m", "worker"]
    procs["worker"] = _lancer("worker", commande_worker, couleur, env)
    code_change, fin_surveillance = threading.Event(), threading.Event()
    threading.Thread(target=surveiller_code, args=(code_change, fin_surveillance), daemon=True).start()
    adresse = f"http://127.0.0.1:{port_api}"
    if not args.sans_web:
        npm = _npm()
        if npm is None:
            dire("npm introuvable : l'interface Vite n'est pas lancée (API seule)")
        elif not (RACINE / "web" / "node_modules").exists():
            dire("web/node_modules absent : lance `npm --prefix web ci` (ou `python dev.py --installer`) ; API seule")
        else:
            procs["web"] = _lancer("web", [npm, "--prefix", "web", "run", "dev", "--", "--port", str(args.port_web),
                                           "--strictPort"], couleur, env)
            adresse = f"http://127.0.0.1:{args.port_web}"

    # Arrêt propre aussi sur SIGTERM (même chemin que Ctrl+C).
    def _sigterm(*_: object) -> None:
        raise KeyboardInterrupt
    signal.signal(signal.SIGTERM, _sigterm)

    code = 0
    try:
        if _attendre_sante(f"{adresse}/api/sante", 60, procs):
            dire(f"Ouvre {adresse}   (API : http://127.0.0.1:{port_api}/api/sante ; Ctrl+C pour tout arrêter)")
            if not args.sans_navigateur:
                webbrowser.open(adresse)
        elif all(p.poll() is None for p in procs.values()):
            dire(f"l'application ne répond pas sur {adresse}/api/sante : regarde les lignes [api] ci-dessus")
        while True:
            if code_change.is_set():
                code_change.clear()
                dire("code modifié : redémarrage du worker")
                _arreter({"worker": procs["worker"]})
                procs["worker"] = _lancer("worker", commande_worker, couleur, env)
            for nom, p in procs.items():
                if p.poll() is not None:
                    dire(f"{nom} s'est arrêté (code {p.returncode}) : arrêt de tout")
                    code = p.returncode or 1
                    raise KeyboardInterrupt
            time.sleep(0.5)
    except KeyboardInterrupt:
        dire("arrêt…")
    finally:
        fin_surveillance.set()
        _arreter(procs)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
