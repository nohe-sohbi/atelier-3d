# Plan de développement

> Copie du document « Cahier des charges – Bibliothèque d'assets 3D », exportée le 17 oct. 2026. Ne la modifie pas ici : elle est régénérée depuis le document. Voir [README.md](README.md).

Ton choix du 17 octobre : on développe toute l'application, interface et fonctionnalités, puis on la teste à la fin en fabriquant de vrais objets. 13 étapes : la première est à moi, les 11 suivantes construisent l'app écran par écran, la dernière est le test.

## Comment on développe

- **Chaque écran arrive avec ses vraies fonctions.** Aucun écran rempli de fausses données : quand une étape est finie, ce que tu vois à l'écran marche. C'est ce que tu demandais lors de l'audit : du fonctionnel derrière chaque bouton.
- **Les services payants sont simulés jusqu'au test.** Meshy, l'API Claude, ComfyUI et itch.io ont chacun un double simulé qui répond comme le vrai, sans dépenser de crédits ni demander de carte graphique. Un réglage bascule vers les vrais services pour le test final.
- **Blender tourne pour de vrai.** Il est gratuit et sur ta machine, et les scripts de fabrication ne peuvent pas se développer sans lui.
- **Tests automatiques et test de l'application sont deux choses différentes.** Claude Code écrit des tests automatiques qui vérifient que chaque fonction marche : c'est ainsi qu'il sait que son code est fini. Le test de l'application, c'est fabriquer de vrais objets et les juger ; il arrive à la dernière étape.
- **Qui fait quoi.** Toi : tu colles les textes dans Claude Code, tu regardes le résultat à l'écran, tu coches. Claude Code : il écrit le code. Moi : je détaille chaque étape au moment où tu l'attaques, et je débloque si ça coince.

## Les 13 étapes

Chaque étape livre des écrans qui marchent. Les codes de la colonne Fonctionnalités renvoient à l'onglet du même nom.

| Étape | Ce que tu obtiens à l'écran | Fonctionnalités | Séances | Fin visée |
| --- | --- | --- | --- | --- |
| 0 · Maquette à jour | Fait : la maquette avec les 15 corrections et les 5 fenêtres, en fichiers pour Claude Code | — | moi | 17 oct. 2026 |
| 1 · Socle | L'app s'ouvre dans ton navigateur ; menu et barre du haut conformes à la maquette ; écran Réglages complet | A1, A2, A5 | 10 | 3 nov. 2026 |
| 2 · Styles | Écran Styles : créer, modifier et versionner un style ; palette, matériaux, budgets | D3 | 3 | 8 nov. 2026 |
| 3 · Lots et Brief | Écrans Lots et Brief : créer un lot, recevoir la liste proposée et la voie de chaque objet | B1, B2, B3 | 7 | 21 nov. 2026 |
| 4 · File de tâches | Écran Génération : les tâches avancent, se relancent, reprennent après une coupure ; notifications et jauge de crédits | A3, A4, A6 | 8 | 5 déc. 2026 |
| 5 · Fabrication par code | Un objet en voie code passe pour de vrai par génération, finition, tests et rendus ; les 6 premiers générateurs | B7, B10, B11, B12 | 21 | 10 janv. 2027 |
| 6 · Références | Écran Références : images pour les objets IA, variantes Blender pour les objets code ; assistant Nouveau style | B4 | 4 | 17 janv. 2027 |
| 7 · Fabrication IA | Meshy, ComfyUI, objets mixtes et import CC0 branchés jusqu'à la revue | B5, B6, B8, B9 | 12 | 7 févr. 2027 |
| 8 · Revue | Écran Revue : vues, 3D, avis IA, décisions, régénération avec consigne | B13, B14, C3 | 5 | 16 févr. 2027 |
| 9 · Bibliothèque | Bibliothèque et fiche asset : versions, comparaison A/B, collections, étiquettes, export | C1, C2, C4 | 7 | 28 févr. 2027 |
| 10 · Publication | Fenêtre Publier : choix du pack, contenu, envoi sur itch.io | C5 | 3 | 6 mars 2027 |
| 11 · Générateurs et Accueil | Écran Générateurs avec banc d'essai et règles ; Accueil avec À faire, activité et chiffres | D1, D2 | 6 | 16 mars 2027 |
| 12 · Test de l'application | Bascule vers les vrais services ; 5 objets fabriqués et jugés ; décision de continuer ou d'ajuster | — | 4 | 23 mars 2027 |

Hypothèse : 4 séances de 2 h par semaine (deux soirs, samedi, dimanche), sans vacances, soit environ 90 séances. Les durées viennent des tailles estimées dans l'onglet Fonctionnalités ; l'étape 5 est la plus incertaine. Le premier vrai objet jugé arrive donc vers fin mars 2027.

## Étape 0 · La maquette à jour (moi)

**Fait le 17 octobre.** Le canvas de la maquette est à jour, et ses fichiers sont déposés dans le dépôt GitHub, dossier `docs/maquette/` : les 18 fichiers `.dc.html` (11 écrans, 5 fenêtres, 2 composants), `canvas.json` et un `README.md` qui dit à Claude Code comment les lire et ce qu'il ne doit pas en reprendre (les données de démonstration). Le cahier des charges y est aussi, en Markdown, dans docs/cahier-des-charges/. Le dépôt contient aussi `CLAUDE.md`, `.gitattributes` et `.gitignore`.

**Objectif :** avant que Claude Code construise le moindre écran, la maquette doit contenir tout ce qu'on a décidé, parce qu'elle lui sert de modèle.

**Ce que je fais :**

- les 15 corrections de l'onglet Fonctionnalités ;
- les 5 fenêtres qui manquent : Publier, Lancer un banc d'essai, Nouveau style, Régénérer avec une consigne, Préparer un générateur pour Claude Code ;
- ta décision sur la publication : l'interrupteur Privé/Public remplacé par la liste des packs ;
- puis je t'envoie les fichiers de la maquette, à déposer dans le projet pour que Claude Code les lise.

**Ce que tu fais :** regarder la maquette mise à jour et me dire si un écran ne te convient pas.

## Étape 1 · Le socle

**Objectif :** l'app s'ouvre dans ton navigateur, avec le menu et la barre du haut de la maquette, et l'écran Réglages marche entièrement. Tout le reste se branchera dessus. L'étape se fait en quatre temps ; chacun a son texte à coller dans Claude Code.

### 1a · Installer les outils (toi)

- [ ] **Blender 5.2.2 LTS**, depuis [blender.org](https://www.blender.org/download/). On garde cette version pendant tout le projet.
- [ ] **Git**, depuis [git-scm.com](https://git-scm.com/), avec **Git LFS** pour les gros fichiers 3D ; sous Windows, il est inclus dans l'installateur de Git.
- [ ] **Python 3.12**, depuis [python.org](https://www.python.org/downloads/) ; sous Windows, coche « Add python.exe to PATH ».
- [ ] **Node.js LTS**, depuis [nodejs.org](https://nodejs.org/), pour l'interface et le validateur glTF.

**Ce que tu dois voir :** dans un terminal, `git lfs version`, `python --version` et `node --version` répondent chacun par un numéro de version. Sinon, ferme et rouvre le terminal.

### 1b · Créer le dépôt

- [x] Sur github.com, crée un dépôt `atelier-3d` : privé, et complètement vide (ne coche ni README, ni .gitignore, ni licence, sinon le premier envoi sera refusé).
- [ ] Clone le dépôt dans le dossier de ton choix : `git clone https://github.com/nohe-sohbi/atelier-3d`. Il contient déjà `CLAUDE.md`, le cahier des charges dans docs/cahier-des-charges/, la maquette dans `docs/maquette/`, `.gitattributes` et `.gitignore`.
- [ ] Lance `claude` dans le dossier et colle le texte « Pour Claude Code ».

**Contenu de CLAUDE.md, déjà dans le dépôt (pour mémoire)**

```markdown
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
- Cahier des charges : docs/cahier-des-charges/ ; son README.md dit quel fichier fait foi.

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
- docs/ est en lecture seule : une décision se change avec Nohé, jamais dans le code.

## Fini veut dire
Les tests automatiques passent et la fonctionnalité s'utilise depuis son écran.
```

**Pour Claude Code**

```
Lis CLAUDE.md. Le dépôt contient déjà CLAUDE.md, docs/ (cahier des charges et maquette), .gitattributes
(Git LFS pour .blend, .glb, .fbx et .png) et .gitignore. Prépare la suite :
1. Active Git LFS dans ce dépôt (git lfs install) et vérifie qu'il suit bien
   les extensions de .gitattributes.
2. Crée l'arborescence : api/, web/, worker/, generators/, pipeline/, style/,
   assets/, reports/, tests/ (docs/ existe déjà).
3. Crée config.local.yaml (déjà ignoré par Git) : chemin de Blender (trouve-le
   sur cette machine), et un mode "simule" ou "reel" pour Meshy, l'API Claude,
   ComfyUI et itch.io, réglé sur "simule".
4. Un README qui explique comment lancer l'app.
5. Commit, puis push sur origin main.
```

**Ce que tu dois voir :** les dossiers créés, et `config.local.yaml` qui contient le chemin de Blender. Sur GitHub, un deuxième commit apparaît avec les dossiers et le README, mais sans config.local.yaml.

### 1c · Le squelette de l'app

**Pour Claude Code**

```
Lis CLAUDE.md, puis docs/maquette/README.md : il explique comment lire la maquette
et ce qu'il ne faut pas en reprendre. Sidebar.dc.html est le menu.
Construis le squelette de l'application :
1. API FastAPI avec une base SQLite (atelier.db) et un système de migrations ;
   une route /sante qui répond ok.
2. Interface React qui reprend exactement la maquette pour le menu de gauche
   et la barre du haut : mêmes couleurs, polices (IBM Plex Sans et Mono),
   espacements.
3. Chaque entrée du menu mène à sa page ; une page pas encore construite
   affiche « Arrive à l'étape N du plan », jamais de fausses données.
4. Une seule commande lance l'API et l'interface ensemble.
5. Tests automatiques : l'API répond, chaque entrée du menu ouvre sa page.
Puis commit et push, et donne-moi l'adresse à ouvrir dans mon navigateur.
```

**Ce que tu dois voir :** à l'adresse indiquée, le menu et la barre du haut identiques à la maquette ; chaque entrée du menu ouvre sa page.

### 1d · L'écran Réglages

**Pour Claude Code**

```
Lis CLAUDE.md et docs/maquette/Settings.dc.html. Construis l'écran Réglages
avec ses vraies fonctions :
1. L'API lit et écrit les réglages dans config.local.yaml ; les clés ne sont
   jamais renvoyées en clair à l'interface.
2. Pour Meshy, l'API Claude, ComfyUI et itch.io : un adaptateur réel et un
   adaptateur simulé avec la même interface, et un interrupteur simulé / réel
   par service, sur simulé par défaut.
3. « Tester la connexion » : en simulé, répond comme le vrai service ; en réel,
   Meshy lit le solde (GET /openapi/v1/balance), l'API Claude liste les modèles
   (GET /v1/models), ComfyUI lit /system_stats, et on vérifie que butler,
   Blender et le validateur glTF répondent.
4. Enregistrer et Annuler marchent ; plafonds, relances et files de tâches
   sont relus par le reste de l'app.
5. Tests automatiques sur chaque réglage et chaque test de connexion simulé.
Puis commit et push.
```

**Ce que tu dois voir :** l'écran Réglages identique à la maquette. Tu changes une valeur, tu enregistres, tu recharges la page : la valeur est conservée. « Tester la connexion » affiche Connecté en mode simulé.

**Si ça coince, à n'importe quel moment :** si un problème bloque plus de 20 minutes, colle l'erreur ici. Si Claude Code ne trouve pas Blender, donne-lui son chemin ; sous Windows, c'est en général `C:\Program Files\Blender Foundation\Blender 5.2\blender.exe`.

## Les étapes suivantes

Je détaille chaque étape au moment où tu l'attaques, sous la même forme : ce que tu fais, le texte pour Claude Code, ce que tu dois voir à l'écran. Elles s'appuieront sur ce que Claude Code aura réellement construit, plutôt que sur des suppositions faites aujourd'hui. Quand une étape est finie, dis-le-moi ici avec son numéro, et je te donne la suivante.
