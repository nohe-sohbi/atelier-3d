# Architecture et conventions de code

Ce fichier complète CLAUDE.md. Il fixe où va chaque chose et comment les modules se parlent.
Le cahier des charges (docs/) reste la référence fonctionnelle ; docs/ ne se modifie pas ici.

## Arborescence

```
api/            API FastAPI. Point d'entrée : api/main.py (app = create_app()).
  config.py     Lecture/écriture de config.local.yaml (jamais de secret renvoyé en clair).
  chemins.py    Chemins de la base, de la config, des lots, des styles et de web/dist ; surchargeables par
                ATELIER_DB, ATELIER_CONFIG, ATELIER_LOTS, ATELIER_STYLES, ATELIER_WEB_DIST (tests, scripts).
  db.py         Connexion SQLite (atelier.db, WAL), migrations versionnées, découpage des scripts.
  migrations/   NNN_nom.sql, appliquées dans l'ordre, enregistrées dans la table `migrations`.
  routes/       Un module par écran ou domaine ; chaque module expose `router = APIRouter(...)`.
                api/main.py découvre et monte automatiquement tous les modules de api/routes/ sous /api.
  services/     Logique métier réutilisée par les routes et le worker : taches.py (file), evenements.py
                (journal et notifications), credits.py (solde Meshy, une seule source), outils.py (Blender,
                glTF-Validator, butler, Git LFS), style_yaml.py (chargeur de style.yaml), styles.py (écran Styles).
  adapters/     Services externes : meshy/, claude/, comfyui/, itchio/. Chaque dossier a
                base.py (interface), simule.py, reel.py et __init__.py avec `get_<service>(config)`.
                Le simulé est le défaut ; il répond comme le vrai sans dépenser de crédits.
worker/         Worker : worker/main.py boucle sur la table `taches` (files gpu, meshy, blender, api ; limites
                relues dans la config) ; worker/handlers/<type>.py expose TYPE et run(tache, ctx). Une
                TacheDefinitive (outil absent, crédits insuffisants, étape non construite) échoue sans relance.
pipeline/       Finition commune et scripts Blender (étape 5) : vide pour l'instant.
generators/     Générateurs code (étape 5) : vide pour l'instant.
style/          Un dossier par style et par version : style/<code>/style.yaml (seule source des couleurs,
                matériaux, budgets, tolérances), board/ (planche de référence), inspiration/. Le style du
                thème pilote est livré (rome-stylise-v0) ; les autres sont créés par l'écran Styles.
assets/         Livrables gardés, un dossier par asset (Git LFS pour .blend, .glb, .fbx, .png).
reports/        Rapports de tests et planches par lot.
lots/           Travail des lots (ignoré par Git).
web/            Vite + React + TypeScript. web/src/pages/<Ecran>/ par écran, web/src/components/
                pour le menu, la barre du haut, les fenêtres et les états ; web/src/api/ client typé ;
                web/e2e/ tests Playwright contre l'application réelle.
tests/          pytest : tests/api. Les tests qui exigent Blender sont marqués `@pytest.mark.blender`
                et sautés quand aucun Blender n'est configuré.
```

## Conventions

- Langue : identifiants et textes d'interface en français (comme la maquette et le cahier des charges) ;
  noms de tables et colonnes en français, snake_case.
- Dates en ISO 8601 UTC dans la base. Identifiants : entiers autoincrément, sauf les assets qui ont
  un `id` textuel `<THEME>_<CATEGORIE>_<Nom>_<Variante>`.
- L'API répond en JSON ; toute erreur, y compris une route inconnue, répond
  `{"erreur": "...", "detail": ...}` avec le bon code HTTP.
- Tout ce qui dure plus d'une seconde devient une tâche (`taches.creer_tache`) ; la route répond 202 avec
  l'id de la tâche, l'interface interroge /api/taches/{id}, et le worker signale la fin par un événement.
- Les seuils (budgets, tolérances) viennent du style du lot, jamais du code.
- Un écran ne lit que l'API ; pas de données inventées ; état vide ou erreur claire. Tout ce qui vient
  d'un adaptateur simulé est marqué « simulé » à l'écran.
- Contrat interface/API : `web/src/test/contrat.json` est généré depuis la vraie API par
  `python -m tests.api.contrat_web --ecrire` ; les tests de l'interface ne simulent l'API qu'avec ce
  fichier, et un test Python vérifie qu'il est à jour.
- Chemins de réglage (Blender, glTF-Validator, butler) : soit un chemin de fichier qui doit exister,
  soit un nom de commande résolu dans le PATH. Une seule règle pour tous les outils.
- Fichiers servis à l'interface (rendus, GLB, planches, archives) : uniquement sous `/api/fichiers/...`.
- Plages de numéros de migrations réservées par chantier :
  000-009 socle (modèle de données A1) · 010-019 styles · 020-029 lots/brief ·
  030-039 file de tâches/coûts · 040-049 fabrication code · 050-059 références · 060-069 fabrication IA ·
  070-079 revue · 080-089 bibliothèque · 090-099 publication · 100-109 générateurs/accueil.
  Chaque migration est indépendante des suivantes (CREATE TABLE IF NOT EXISTS, une colonne par
  ALTER TABLE, jamais la même colonne dans deux migrations).
- Chemins de fichiers : `lots/<lot_id>/` pour le travail d'un lot, `assets/<THEME>/<id>/` pour les
  livrables gardés, `reports/<lot_id>/` pour rapports et planches.

## Lancer et tester

Voir README.md : `python dev.py`, `pytest`, `npm --prefix web test`, `npm --prefix web run test:e2e`.
