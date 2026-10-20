# Passation · de la session cloud à la session sur la machine de Nohé

Écrit le 19 octobre 2026 par la session Claude Code du cloud, pour la session Claude Code qui reprend sur
la machine de Nohé. **Lis ce fichier en entier avant de toucher au code.** Ensuite : `CLAUDE.md`,
`ARCHITECTURE.md`, `A-TRANCHER.md`, puis `PLAN-CLOUD.md` pour la conception détaillée.

Ce fichier n'est pas dans `docs/` (lecture seule) : il se supprime quand la passation est faite.

## 1. Où on en est

**Mise à jour du 21 octobre 2026, session locale (Debian 13 ; Blender 5.2.2 LTS, glTF-Validator et Git LFS installés).**
- La PR #1 a été fusionnée le 19 octobre (§4.3 fait) : on travaille sur `main`.
- §4.0 fait : 3 correctifs propres à la machine (base créée à plusieurs, Vite en IPv4, port 8000 déjà pris).
- §4.1 fait : relecture de l'étape 2 corrigée, un test par constat.
- §4.2 fait : écrans de l'étape 3.
- Étape 4 faite (file de tâches, Génération, dépenses), sauf la notification du bureau : Nohé a dit « plus tard »,
  à reprendre à l'étape 8 (`A-TRANCHER.md` 4.6).
- Étape 5 faite : Blender sans fenêtre, finition, 12 contrôles, rendus, planche, et les 6 premiers générateurs
  (scutum, gladius, pilum, amphore, colonne, caisse), chacun testé dans Blender.
- Étape 6 faite : écran Références (4 images IA par objet, ta consigne, ton image, 4 versions Blender pour un objet
  code), puis « Lancer la génération 3D ». Le but de Nohé : avec des images de référence et des prompts, obtenir
  les assets qu'il veut ; la voie IA est le cœur.
- Prochaine étape : 7, Fabrication IA (Meshy, ComfyUI sur le PC Windows, mixte, import CC0).
- Toujours pas vérifiés : Windows, les services réels (Meshy, API Claude, ComfyUI, itch.io).

Ce qui suit est l'état laissé par la session cloud.

Branche `claude/atelier-3d-status-xp09v0`, PR #1 (brouillon) vers `main`, non fusionnée.
`main` ne contient encore que la documentation.

| Étape du plan | État |
|---|---|
| 0 · Préparation | faite (par Nohé) |
| 1 · Socle | **faite**, prouvée de bout en bout, relue par un relecteur indépendant, corrigée |
| 2 · Styles | **faite**, prouvée de bout en bout ; **relecture indépendante rendue, pas encore corrigée** (§4.1) |
| 3 · Lots et Brief | **API faite et testée** (commit `d69ad23`) ; **écrans pas commencés** (§4.2) |
| 4 à 13 | pas commencées |

Tests au dernier commit, dans le cloud (Linux, sans Blender) :

| Suite | Résultat |
|---|---|
| Python (`pytest`) | 153 passent, 1 sauté (marqué `blender`) |
| Interface (`vitest`) | 44 passent |
| Bout en bout (Playwright contre `python dev.py`) | 7 scénarios passent |
| `ruff`, `eslint`, `tsc` + build Vite | verts |

**Jamais vérifié** (impossible dans le cloud) :
- Windows : `dev.py`, l'arrêt par `taskkill`, les chemins ;
- Blender réel, glTF-Validator, butler ;
- les services réels : Meshy, API Claude, ComfyUI, itch.io ;
- l'interface construite servie par l'API (seul un test unitaire la couvre) ;
- une version de Node autre que 22.

## 2. Première fois sur la machine (Nohé)

```
git clone https://github.com/nohe-sohbi/atelier-3d
cd atelier-3d
git checkout claude/atelier-3d-status-xp09v0
python dev.py --installer
npx --prefix web playwright install chromium
python dev.py
```

Si le dépôt est déjà cloné : `git fetch origin` puis `git checkout claude/atelier-3d-status-xp09v0` puis `git pull`.

Ce que tu dois voir :
- **Au lancement.** Le terminal dit « Blender détecté : … ». `config.local.yaml` est créé avec ce chemin. Le navigateur s'ouvre sur http://127.0.0.1:5173.
- **Réglages.** La carte Blender passe à « Détecté » et donne la version 5.2.x. Les services restent en mode simulé, qui est le défaut.
- **Styles.** Le style pilote s'affiche, et « Nouveau style » produit une planche de 6 images simulées. Le détail est dans la description de la PR #1.
- **Lots.** L'écran affiche encore « Arrive à l'étape 3 du plan », ce qui est normal : ses écrans sont à faire.

Puis, dans le dossier du dépôt :

```
.venv\Scripts\python -m pytest
npm --prefix web test
npm --prefix web run test:e2e
```

Ensuite, lance Claude Code dans le dossier du dépôt et colle :

> Lis PASSATION.md, puis fais le travail dans l'ordre qu'il donne. Commence par me dire ce que les tests donnent sur ma machine.

## 3. Décisions déjà prises par Nohé, et ce qui change en local

| Sujet | Décision du 18 oct. (cloud) | En local |
|---|---|---|
| Base de départ | Reprise sélective de la branche `claude/sleepy-mendel-tc8e34` (jamais modifiée) | Inchangé ; elle reste une source à piocher (§5) |
| Où pousser | Sur cette branche, PR vers main ; Nohé fusionne | **Sur cette branche jusqu'à la fusion de la PR #1**, puis règle de `CLAUDE.md` : commit, puis push sur main |
| Périmètre et ordre | 1, 2, 3, 4 puis 8 à 11 (rien de ce qui exige Blender) | **Ordre du plan de `docs/`** : 3, 4, 5, 6, 7, 8… Blender est là |
| Blender | Option `python_bpy` supprimée ; Blender 5.2 LTS lancé en exécutable, détecté au 1er lancement ; tests marqués `blender` | Inchangé ; les tests `blender` tournent chez Nohé (`pytest -m blender`) |

Règles de travail tenues depuis le début, à garder :
- **`docs/` en lecture seule.** Toute contradiction entre maquette, cahier et plan va dans `A-TRANCHER.md`, avec le choix provisoire fait dans le code et la question à Nohé. Rien n'est tranché en silence.
- **Jamais de fausse donnée à l'écran.** Ce qui vient d'un adaptateur simulé est marqué « simulé ». En base, cela donne `simule = 1` ou `"simule": true`.
- **Couleurs** dans `web/src/styles/tokens.css` seulement. Un test vérifie que chacune existe dans `docs/maquette/`.
- **Budgets, matériaux et dimensions** viennent du `style.yaml`, jamais en dur.
- **Tâches.** Tout ce qui dure plus d'une seconde passe par la file. Une erreur sans espoir lève `TacheDefinitive` : échec immédiat, sans relance. On ne crée pas de tâche pour une étape pas encore construite.
- **Commits** en français, après des tests verts. On corrige le code, jamais le seuil.

## 4. Le travail, dans l'ordre

### 4.0 Vérifier sur la machine

Lance les commandes du §2. Chaque échec propre à Windows ou à la machine devient le premier correctif, avec un test qui le reproduit.

### 4.1 Corriger la relecture indépendante de l'étape 2

Un relecteur indépendant a relu l'étape 2 et reproduit la plupart des constats par un script jetable. **Revérifie chaque constat avant de le corriger.** Écris d'abord le test qui le montre.

**Bloquants**

- **B1 · Deux styles du même nom et de la même version.**
  - Symptôme : la création renvoie 500 et laisse un dossier orphelin. Ensuite, **l'API ne redémarre plus**, parce que `importer_dossier` lève la même erreur au démarrage.
  - Où : contrainte `UNIQUE (nom, version)` dans `api/migrations/000_socle.sql` ; dans `api/services/styles.py::creer`, le yaml est écrit avant la base.
  - Correctif : vérifier le couple et répondre 409, ou retirer la contrainte par une migration 011. Insérer en base avant d'écrire sur le disque, ou nettoyer le dossier en cas d'échec. Dans `importer_dossier`, attraper l'`IntegrityError` et la journaliser.
- **B2 · Arrêt du worker pendant une planche.**
  - Symptôme : les images et les crédits sont doublés à la reprise.
  - Où : `styles.executer_planche` ne regarde jamais `ctx.arret_demande()`, et `planche_images.tache_id` reste toujours vide.
  - Correctif : dans la boucle d'attente, lever `InterruptedError` quand l'arrêt est demandé. Rendre le rangement idempotent : renseigner `tache_id`, puis supprimer les lignes de cette tâche avant de les réinsérer, dans une seule transaction.

**Importants**

| # | Constat | Correctif proposé |
|---|---|---|
| I1 | Le prompt de la planche d'un nouveau style reprend le texte thématique du style de référence (« Rome antique… »), et la description saisie ne sert à rien | Construire le gabarit depuis la description du nouveau style (`styles.creer`) |
| I2 | Un seul appel Meshy pour les 6 images avec « objets génériques », puis les étiquettes caisse, amphore… sont collées après coup : elles sont inventées | Un appel `n=1` par objet, avec `prompt_planche(s, objet)` |
| I3 | Les images d'inspiration sont stockées mais jamais envoyées à Meshy | Les passer à `image_vers_image`, ou retirer la promesse du libellé et la consigner |
| I4 | `modifier` écrit le yaml avant la base : en cas d'échec, le fichier et la table divergent | Base d'abord, ou restauration du yaml |
| I5 | Renommer une couleur dans « Modifier » donne 422 sans issue : les matériaux ne suivent pas | Slugifier les clés et remapper `materiaux[*].base`, ou verrouiller le nom |
| I6 | `dupliquer` n'est pas transactionnel ; un dossier résiduel bloque la version pour toujours (409) | Transaction, et `rmtree` du dossier copié en cas d'échec |
| I7 | Réimport au démarrage : un brouillon devient « Actif » et un style validé perd sa planche | `etat` selon `brut["planche"]`, et recréer les `planche_images` gardées |
| I8 | Le tarif de 3 crédits par image est écrit en dur dans `commun.ts`, `routes/styles.py` et le simulateur ; en réel, la réponse Meshy n'a pas de champ `credits` | Un tarif exposé par l'adaptateur et une route d'estimation ; l'interface n'affiche que ce chiffre |
| I9 | En réel, un refus Meshy (402 ou 403) part en relances au lieu d'un échec définitif | Le convertir en `TacheDefinitive` |

**Mineurs**, à faire au passage :
- M1 : `garder_image` ne met pas le yaml à jour après validation.
- M2 : `dupliquer` recopie les crédits de la planche.
- M3 : transactions manquantes dans `styles.py`.
- M4 : `importer_dossier` trie v10 avant v2.
- M5 : le polling de `web/src/api/taches.ts` ne s'annule jamais quand on quitte l'écran.
- M6 : sans worker, l'écran attend 10 minutes sans rien dire.
- M7 : la progression de la planche n'est pas marquée « simulé », et un ternaire mort traîne dans `NouveauStyle.tsx`.
- M8 : défauts en dur, `texel 512` et `#888888`.
- M9 : les champs de la palette font moins de 40 px.
- M10 : un `?style=` inconnu est ignoré sans message.
- M11 : écarts de maquette non consignés, à ajouter dans `A-TRANCHER.md` §2 :
  - pas de bouton Retour ;
  - pas de glisser-déposer ;
  - budgets repris non affichés ;
  - `direction` jamais proposée ;
  - style pilote Actif sans image.
- M12 : `usage_assets` vaut 0 en dur.
- M13 : un style saisi à la main avec moins de 6 types reçoit des étiquettes `objet-2`…
- M14 : le worker de `dev.py` ne se recharge pas quand le code change.
- M15 : `modifier` accepte des tolérances et des textures négatives.

Tests manquants signalés par le relecteur :
- B1, B2, I5, I6 et I7 ;
- un échec Meshy `FAILED` ou un délai dépassé ;
- les routes `/api/taches`, `/relancer` et `/annuler` appelées en HTTP ;
- côté interface : le polling réel avec l'état « échouée », `ModifierStyle`, « Refaire », `?style=` et la saisie à la main.

### 4.2 Finir l'étape 3 : les écrans

L'API est faite. Elle est décrite dans `api/routes/lots.py` et `api/routes/routage.py`, et ses choix provisoires sont dans `A-TRANCHER.md` §3. La conception d'origine est dans `PLAN-CLOUD.md` §8. Maquettes : `Lots.dc.html`, `LotHeader.dc.html`, `Brief.dc.html`, `ClaudeRequest.dc.html`.

1. **Contrat d'abord.**
   - Ajouter les réponses de lots dans `tests/api/contrat_web.py::generer` :
     - `GET /api/lots` vide puis rempli ;
     - `POST /api/lots` ;
     - `GET /api/lots/{id}` ;
     - `GET /api/lots/{id}/objets`, après une proposition simulée exécutée par `Worker(...).tour()` dans `generer()` ;
     - `GET …/objets/{oid}/demande` ;
     - `GET /api/routage/regles`.
   - Mettre `ATELIER_GENERATEURS` dans le dossier temporaire, pour que la machine reste figée.
   - Régénérer avec `python -m tests.api.contrat_web --ecrire`, puis lire les mocks via `depuis<T>()` dans `web/src/test/api-mock.ts`.
2. **`/lots`** : quatre filtres avec compteurs (`?groupe=`), tableau de 6 colonnes, segments d'étape, états vides par filtre. Un lot s'ouvre sur `lien`.
3. **`/lots/nouveau`** : `POST /api/lots`, puis redirection vers `/lots/{id}/brief` avec `replace`. Le bouton « Nouveau lot » du menu y mène déjà.
4. **`EnTeteLot`**, au-dessus des 4 écrans de lot :
   - fil d'Ariane, nom éditable (`PATCH`), thème ;
   - puce du style qui mène à `/styles?style=<code>` ;
   - `ligne_etat`, donnée par `GET /api/lots/{id}?etape=…` ;
   - « Dupliquer le lot » ;
   - onglets avec `aria-current="step"` ; une étape non atteinte a `aria-disabled` ;
   - « Appliquer la vN » si `style_plus_recent` est présent : il n'affiche que l'estimation.
5. **`/lots/:id/brief`** :
   - champs : thème, style (liste de `GET /api/styles`), besoin ;
   - « Proposer » ou « Reproposer la liste » : `POST …/proposition`, puis `attendreTache`, puis rechargement ;
   - bandeau « Liste simulée » quand `simule` est vrai ;
   - liste avec cases (`PATCH retenu`), pastilles de voie, dimensions « L × H m » ;
   - lien « Préparer la demande pour Claude Code » sur un objet « À créer » ;
   - résumé avec les bons pluriels ;
   - « Générer les références → » : `POST valider-brief`, puis `/lots/{id}/references`. Un 409 s'affiche tel quel.
   - Les couleurs des pastilles existent dans la maquette mais pas encore dans `tokens.css` : il faut les y ajouter.

     | Voie | Fond | Texte |
     |---|---|---|
     | Code | `#EAEDF3` | `#2F3A55` |
     | Mixte | `#F1ECFA` | `#5B3FA6` |
     | Réutilisé | `#E2EFEF` | `#1D5C5C` |
     | À créer | `#FBEEDC` | `#8A4B00` |
6. **Fenêtre « Demande pour Claude Code »**, sur la base de `components/Fenetre.tsx` :
   - chemin, Markdown, texte à coller ;
   - Copier (`navigator.clipboard`) ;
   - « Écrire dans le dépôt » : `POST …/demande` ;
   - « Passer en voie IA à la place » : `PATCH voie: "ia"` ;
   - états « Pas encore écrite », « Écrite dans le dépôt », « Script détecté ».
7. **Les autres écrans de lot.** `/lots/:id/references`, `/generation` et `/revue` gardent « Arrive à l'étape N » (6, 4 et 8) sous l'en-tête. La route `/lots/:id` redirige vers l'étape du lot : la recherche globale y mène déjà.
8. **Tests.**
   - Vitest : Lots, en-tête verrouillé, Brief (case, compteur, résumé, pastilles, bandeau simulé) et fenêtre (presse-papiers, écriture, Échap).
   - `web/e2e/lots.spec.ts` : Nouveau lot, Brief, proposition simulée, décocher, passer l'« À créer » en IA, valider. L'onglet Références montre alors « Arrive à l'étape 6 du plan », et Lots montre le lot à l'étape 2.
   - Mettre à jour `App.test.tsx` et `socle.spec.ts` : Lots n'y est plus une page à venir.
9. **Consigner.** Ajouter à `A-TRANCHER.md` §3 les écarts propres aux écrans. Puis commit et push sur la branche.

### 4.3 Fusionner la PR #1

Quand les tests du §2 passent chez Nohé et que 4.1 et 4.2 sont faits, Nohé passe la PR #1 de brouillon à prête et la fusionne. Ensuite :

```
git checkout main
git pull
```

La règle de `CLAUDE.md` reprend : chaque étape finie, commit, puis push sur main.

### 4.4 Étapes 4 à 13, dans l'ordre du plan

Pour chaque étape, lis d'abord la ligne du plan dans `docs/cahier-des-charges/04-plan-de-developpement.md`, puis `03-fonctionnalites.md`. Ensuite, si elle existe, lis la conception cloud :

| Étape | Conception cloud |
|---|---|
| 4 · File de tâches et Génération | `PLAN-CLOUD.md` §9 |
| 5, 6, 7 · Fabrication code, références, IA | aucune : à concevoir depuis `docs/` |
| 8 · Revue | `PLAN-CLOUD.md` §10 |
| 9 · Bibliothèque et Fiche asset | `PLAN-CLOUD.md` §11 |
| 10 · Publication | `PLAN-CLOUD.md` §12 |
| 11 · Générateurs et Accueil | `PLAN-CLOUD.md` §13 |
| 12, 13 | aucune |

Pour les étapes 8 à 11, la conception cloud prévoyait des données insérées par les tests faute de fabrication. Avec 5 à 7 faites avant, branche-les sur les vrais essais.

## 5. Mécanismes à connaître

- **Contrat interface/API.**
  - `web/src/test/contrat.json` est généré depuis la vraie API par `python -m tests.api.contrat_web --ecrire`.
  - Le test gardien `tests/api/test_contrat_web.py` échoue s'il n'est pas à jour.
  - `api-mock.ts` n'a aucune constante écrite à la main. C'est ce qui empêche une page blanche comme celle de la cloche du premier brouillon.
- **Isolation des tests.**
  - Les variables `ATELIER_DB`, `ATELIER_CONFIG`, `ATELIER_LOTS`, `ATELIER_STYLES`, `ATELIER_GENERATEURS` et `ATELIER_WEB_DIST` déplacent tous les chemins.
  - La fixture `atelier` de `tests/conftest.py` les met dans un dossier temporaire.
  - Le serveur e2e, `web/e2e/serveur.ts`, fait de même. Il garde `web/test-results/dev.log` après chaque passage.
- **Worker dans un test.** `Worker(verrou="test", tick_s=0.05, backoff_base_s=0, charger_config=lambda: cfg)`, puis `tour()`, puis `attendre_fin()`, puis `arreter()`. Exemple : `tests/api/test_brief.py`.
- **Travaux périodiques.** `worker/periodiques.py` lance le scanner des générateurs toutes les 30 s. La purge des rejets de l'étape 9 y trouvera sa place.
- **Générateur factice** pour les tests : `tests/fabrique_generateur.py`. Le contrat d'un générateur est dans `generators/CONTRAT.md`.
- **Migrations** `api/migrations/NNN_nom.sql`, par plages :

  | Plage | Usage |
  |---|---|
  | 000 | socle |
  | 010 | styles |
  | 020 | lots et brief |
  | 030 | file et coûts (étape 4) |
  | 040 à 069 | réservées aux étapes 5 à 7 |
  | 070 | revue |
  | 080 | bibliothèque |
  | 090 | publication |
  | 100 | générateurs et accueil |

  Chaque migration est indépendante. Une colonne s'ajoute par `ALTER`, une seule fois. Pour changer un `CHECK`, on recrée la table, comme dans `020_lots_brief.sql`.
- **Claude simulé.** `api/adapters/claude/simule.py::proposition_brief_simulee` répond une liste déterministe, liée à l'empreinte du besoin, qui couvre toutes les natures. Les noms disent « Objet simulé ».
- **Branche d'archive.** `origin/claude/sleepy-mendel-tc8e34` est intacte. Elle contient encore des pièces utiles aux étapes 5 et 8, à reprendre avec relecture et le trailer `Repris-de: origin/claude/sleepy-mendel-tc8e34 @ 18d6c5f` :
  - `pipeline/` ;
  - `pipeline/meta.py`, dont il faut retirer la licence par défaut ;
  - `tests/pipeline/conftest.py::dossier_asset()`, un dossier d'asset complet sans Blender ;
  - les générateurs.

  Pour lire un fichier : `git show origin/claude/sleepy-mendel-tc8e34:pipeline/meta.py`. Après la fusion, Nohé peut la garder en tag (`archive/etape-1-brouillon-2026-10-18`) ou la supprimer.
- **Trailers de commit** utilisés jusqu'ici : `Co-Authored-By` et `Claude-Session`. La session locale suit ses propres réglages.
