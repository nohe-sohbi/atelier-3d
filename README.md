# Atelier 3D

Application locale pour fabriquer une bibliothèque d'assets 3D de jeu. Le cahier des charges est dans
`docs/cahier-des-charges/`, la maquette des écrans dans `docs/maquette/`, les conventions de code dans
`ARCHITECTURE.md`.

## Installer

1. Python 3.12, Node.js LTS, Git LFS, Blender 5.2 LTS.
2. `python -m venv .venv && .venv/bin/pip install -e ".[dev]"` (Windows : `.venv\Scripts\pip`).
3. `npm --prefix web install`.
4. `cp config.local.example.yaml config.local.yaml` et renseigne le chemin de Blender.
   Tous les services (Meshy, API Claude, ComfyUI, itch.io) sont en mode simulé par défaut.

## Lancer

- `make dev` (ou `.venv/bin/python dev.py`) lance l'API, le worker et l'interface Vite ensemble, puis
  affiche l'adresse à ouvrir : **http://127.0.0.1:5173**. Ctrl+C arrête tout. `python dev.py --sans-web`
  saute Vite (l'API sert alors `web/dist/` si l'interface a été construite avec `npm --prefix web run build`).
- Séparément : `python -m api` (API sur http://127.0.0.1:8000, santé sur `/api/sante`, documentation
  sur `/api/docs`), `python -m worker` (file de tâches), `npm --prefix web run dev` (interface).
- Au premier lancement, `config.local.yaml` est copié depuis l'exemple : tout est en mode simulé.
  La base `atelier.db` est créée et migrée au démarrage de l'API et du worker.
- Variables d'environnement utiles (tests, scripts) : `ATELIER_DB`, `ATELIER_CONFIG`, `ATELIER_LOTS`
  remplacent les chemins par défaut.

## Tester

- `.venv/bin/pytest`
- `npm --prefix web test`
