# Atelier 3D

Application locale pour fabriquer une bibliothèque d'assets 3D de jeu : un brief devient
une liste d'objets ; chaque objet est fabriqué (script Blender, Meshy, ComfyUI ou import CC0),
fini, testé, rendu, jugé en revue, puis rangé en bibliothèque et publié.

## Pile
- API : Python 3.12, FastAPI, SQLite (atelier.db) avec migrations versionnées.
- Interface : React + TypeScript (Vite), servie en local.
- Travaux longs : file de tâches en base, exécutée par un worker Python.
- Blender 5.2 LTS sans fenêtre : blender -b --factory-startup -P <script> -- <arguments>.
- Modèle des écrans : la maquette dans docs/maquette/ ; lire d'abord son README.md.

## Règles
- Un écran est branché sur de vraies données dès qu'il est construit ; jamais de
  fausses données dans l'interface.
- Meshy, API Claude, ComfyUI, itch.io : un adaptateur réel et un adaptateur simulé
  avec la même interface ; le simulé est le défaut (config.local.yaml).
- 1 unité Blender = 1 mètre. Haut = +Z, face avant = -Y.
- Nommage des assets : <THEME>_<CATEGORIE>_<Nom>_<Variante>, ex. ROM_PROP_Scutum_A.
- Couleurs, matériaux, budgets et tolérances viennent du fichier de style, jamais en dur.
- Un générateur code = un fichier dans generators/ avec un MANIFESTE et build(params).
- Rejouable : mêmes paramètres = même résultat.
- Quand un test échoue, on corrige le code, jamais le seuil.
- Secrets et chemins dans config.local.yaml, non versionné.
- Chaque étape finie : commit, puis push sur origin main.

## Fini veut dire
Les tests automatiques passent et la fonctionnalité s'utilise depuis son écran.
