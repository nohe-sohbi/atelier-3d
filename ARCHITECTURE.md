# Architecture et conventions de code

Ce fichier complète CLAUDE.md. Il fixe où va chaque chose et comment les modules se parlent,
pour que plusieurs chantiers avancent en parallèle sans se marcher dessus. Le cahier des charges
(docs/) reste la référence fonctionnelle.

## Arborescence

```
api/            API FastAPI. Point d'entrée : api/main.py (app = create_app()).
  config.py     Lecture/écriture de config.local.yaml (jamais de secret renvoyé en clair).
  db.py         Connexion SQLite (atelier.db), migrations versionnées, helpers.
  migrations/   NNN_nom.sql, appliquées dans l'ordre, enregistrées dans la table `migrations`.
  routes/       Un module par écran ou domaine ; chaque module expose `router = APIRouter(...)`.
                api/main.py découvre et monte automatiquement tous les modules de api/routes/.
  services/     Logique métier réutilisée par routes et worker (lots, assets, routage, coûts…).
  adapters/     Services externes : meshy/, claude/, comfyui/, itchio/. Chaque dossier a
                base.py (interface), simule.py, reel.py et __init__.py avec `get_<service>(config)`.
worker/         Worker Python : worker/main.py boucle sur la table `taches` (3 files : gpu, meshy,
                blender). worker/handlers/<type>.py expose `run(tache, ctx)`. Reprise après coupure.
pipeline/       Finition commune et scripts Blender (bpy). Chaque script lit ses arguments après `--`.
  blender_run.py Lance un script bpy : exécutable Blender (config blender.chemin) ou Python+bpy
                (config blender.python_bpy). Même script dans les deux cas.
  style.py      Charge et valide un style.yaml (budgets, palette, tolérances) : seule source des seuils.
generators/     Un générateur code = un fichier avec MANIFESTE (dict) et build(params) -> bpy objects.
  _base.py      Cadre commun : briques (révolution, extrusion, symétrie), matériaux du style, lecture
                des paramètres, déterminisme (seed).
style/          style.yaml (v0 du thème pilote), materials.blend, board/.
web/            Vite + React + TypeScript. web/src/pages/<Ecran>/ par écran, web/src/components/
                pour Sidebar, TopBar, LotHeader, fenêtres. web/src/api/ client typé.
tests/          pytest. tests/api, tests/worker, tests/pipeline, tests/generators. Les tests bpy sont
                marqués `@pytest.mark.bpy` et sautés si bpy est absent.
```

## Conventions

- Langue : identifiants et textes d'interface en français (comme la maquette et le cahier des charges) ;
  noms de tables et colonnes en français, snake_case.
- Dates en ISO 8601 UTC dans la base. Identifiants : entiers autoincrément, sauf les assets qui ont
  un `id` textuel `<THEME>_<CATEGORIE>_<Nom>_<Variante>`.
- L'API répond en JSON ; erreurs = `{"erreur": "...", "detail": ...}` avec le bon code HTTP.
- Tout ce qui dure plus d'une seconde devient une ligne dans `taches` (type, file, params JSON) ;
  la route répond immédiatement avec l'id de tâche. Le worker écrit l'avancement dans `evenements`.
- Les seuils (budgets, tolérances) sont lus dans le style du lot via pipeline/style.py. Jamais en dur.
- Un écran ne lit que l'API ; pas de données inventées ; état vide ou erreur claire.
- Plages de numéros de migrations réservées par chantier (pour éviter les collisions) :
  000-009 socle (modèle de données A1, tâches, événements) · 010-019 styles · 020-029 lots/brief ·
  030-039 file de tâches/coûts · 040-049 fabrication code · 050-059 références · 060-069 fabrication IA ·
  070-079 revue · 080-089 bibliothèque · 090-099 publication · 100-109 générateurs/accueil.
- Chemins de fichiers : `lots/<lot_id>/` pour le travail d'un lot, `assets/<THEME>/<id>/` pour les
  livrables gardés, `reports/<lot_id>/` pour rapports et planches.

## Lancer

- `make dev` (ou `python -m api` + `npm --prefix web run dev` + `python -m worker`) : voir README.md.
- Tests : `.venv/bin/pytest` et `npm --prefix web test`.
