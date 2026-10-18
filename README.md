# Atelier 3D

Application locale pour fabriquer une bibliothèque d'assets 3D de jeu. Le cahier des charges est dans
`docs/cahier-des-charges/`, la maquette des écrans dans `docs/maquette/`, les conventions de code dans
`ARCHITECTURE.md`. Les écarts entre maquette, cahier des charges et code, et les choix provisoires faits
en attendant une décision, sont listés dans `A-TRANCHER.md`.

## Installer

Prérequis : Python 3.12, Node.js LTS, Git avec Git LFS, Blender 5.2 LTS.

Windows (PowerShell ou cmd) :

```
py -3.12 -m venv .venv
.venv\Scripts\python -m pip install -e ".[dev]"
npm --prefix web ci
```

macOS ou Linux :

```
python3.12 -m venv .venv
.venv/bin/pip install -e ".[dev]"
npm --prefix web ci
```

Ou, en une fois : `python dev.py --installer`.

## Lancer

```
python dev.py
```

Une seule commande lance l'API, le worker (file de tâches) et l'interface, crée `config.local.yaml` au premier lancement (avec le
chemin de Blender s'il est trouvé sur la machine), crée et migre la base `atelier.db`, puis ouvre le
navigateur sur **http://127.0.0.1:5173**. Ctrl+C arrête tout. Tous les services (Meshy, API Claude,
ComfyUI, itch.io) sont en mode simulé par défaut : on bascule service par service dans Réglages.

Options : `--sans-web` (API et worker seuls ; l'API sert alors `web/dist/` si l'interface a été construite
avec `npm --prefix web run build`), `--sans-navigateur`, `--port 8000` (port de l'API), `--port-web 5173`
(port de l'interface).

Séparément : `python -m api` (API sur http://127.0.0.1:8000, santé sur `/sante` et `/api/sante`,
documentation sur `/api/docs`) et `npm --prefix web run dev` (interface).

Variables d'environnement utiles (tests, scripts) : `ATELIER_DB`, `ATELIER_CONFIG`, `ATELIER_LOTS`,
`ATELIER_STYLES`, `ATELIER_WEB_DIST` remplacent les chemins par défaut.

## Tester

- Python : `.venv/bin/python -m pytest` (Windows : `.venv\Scripts\python -m pytest`).
- Interface : `npm --prefix web test`.
- Bout en bout, dans un vrai navigateur, contre `python dev.py` : `npm --prefix web run test:e2e`
  (Chromium Playwright requis : `npx --prefix web playwright install chromium` une fois).
- Les tests qui exigent Blender sont marqués `blender` et sautés quand il n'est pas configuré.
