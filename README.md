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

(Complété à l'étape 1c : une seule commande lance l'API et l'interface.)

## Tester

- `.venv/bin/pytest`
- `npm --prefix web test`
