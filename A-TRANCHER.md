# À trancher avec Nohé

Ce fichier liste, étape par étape, les écarts entre la maquette (`docs/maquette/`), le cahier des
charges (`docs/cahier-des-charges/`) et le plan, rencontrés en construisant l'application, ainsi que
les choix **provisoires** faits dans le code pour que l'écran marche en attendant. Rien ici n'est
tranché : Nohé décide, puis le code ou les documents sont mis à jour. `docs/` n'est jamais modifié
par Claude Code (CLAUDE.md).

Ordre de foi (docs/cahier-des-charges/README.md) : plan > fonctionnalités > cahier des charges >
audit > maquette.

## Étape 1 · Socle

| # | Sujet | Ce que disent les sources | Choix provisoire dans le code | Question |
|---|---|---|---|---|
| 1.1 | Interrupteur simulé / réel | Le plan (1d) l'exige par service ; la maquette `Settings.dc.html` n'en dessine aucun | Un groupe de boutons « Simulé / Réel » sur Meshy, API Claude, itch.io et ComfyUI (ComfyUI est dans « Outils sur ta machine », la maquette ne le classe pas comme service) | Le rendu convient-il ? ComfyUI reste-t-il dans « Outils » ? |
| 1.2 | États d'erreur des pastilles | La maquette ne montre que des états positifs (Connecté, Détecté, Joignable, Git LFS) | Ajout de « Non testé » (neutre), « Introuvable » (rouge, outil absent de la machine) et « Erreur » (rouge) ; aucun outil n'est vert sans test réel | Couleurs et libellés à valider |
| 1.3 | Pastille Git LFS | Verte et fixe dans la maquette | Un vrai test : `git lfs version`, LFS activé dans le dépôt, extensions suivies | — |
| 1.4 | Boutons « Tester » sur les outils | Le plan demande de vérifier que Blender, le validateur glTF et butler répondent ; la maquette n'a de bouton que sur les services | Un bouton « Tester » par outil ; la présence (sans lancer l'outil) est affichée dès l'ouverture | Test au clic (actuel), ou automatique à l'ouverture ? |
| 1.5 | Blender introuvable | Le plan attend « config.local.yaml qui contient le chemin de Blender » ; construit depuis le cloud, sans Blender | Détection automatique au premier `python dev.py` (PATH puis emplacements connus de Windows, macOS, Linux), bouton « Utiliser ce chemin » dans Réglages, sinon « Introuvable » honnête | — |
| 1.6 | Blender d'une autre version que 5.2 | CLAUDE.md fige la 5.2 LTS | « Détecté » avec le message « le projet attend Blender 5.2 LTS » (`version_ok: false`) | Faut-il refuser (rouge) une autre version ? |
| 1.7 | `blender.python_bpy` | Option du brouillon précédent, hors plan | Retirée (décision du 18 oct.) | — |
| 1.8 | Clés jamais renvoyées en clair | Le plan l'exige ; la maquette pré-remplit les champs mot de passe | Champ vide avec l'aperçu « ••••ab12 » en indication, bouton « Effacer la clé » ; une clé vide à l'enregistrement laisse l'actuelle, `null` l'efface | — |
| 1.9 | Champs hors maquette dans Réglages | — | Ajoutés : clé API itch.io, chemin de butler, crédits mensuels Meshy, délai de purge des rejets (correction 15), case « Dans l'app » pour les notifications | Garder ? |
| 1.10 | « Dépensé ce mois » (API Claude) | A6 (suivi des coûts) est à l'étape 4 | La ligne dit « Suivi des dépenses : arrive à l'étape 4 du plan » plutôt qu'un montant calculé avec des tarifs inventés | — |
| 1.11 | Jauge de crédits Meshy : sens et source | Menu « 426 / 1 000 » (consommé), Réglages « 574 / 1 000 restants », audit « 570 utilisés » ; le total 1 000 n'est pas donné par l'API Meshy | Une seule source : le solde lu par l'adaptateur (`GET /openapi/v1/balance` en réel, simulateur sinon) ; le menu affiche « utilisés / total », Réglages « restants » ; le total vient du réglage « crédits mensuels » ; « · simulé » affiché quand le solde vient du simulateur ; « Solde Meshy non lu » si l'API ne répond pas | Sens à confirmer ; suffixe « simulé » accepté ? |
| 1.12 | Notifications : défaut de la case « notification de l'ordinateur » | Correction 14 : « à activer » ; maquette : cochée | Décochée par défaut ; « Dans l'app » cochée | — |
| 1.13 | Textes figés « 3 relances » et « 80 % » | La maquette les écrit en dur alors que ce sont des réglages | Calculés depuis les réglages | — |
| 1.14 | Couleur d'alerte et de danger | README de la maquette `#FBF7EF`, écrans `#FBEEDC` ; rouge `#B42318` / `#FDECEA` absent du README | `#FBF7EF` (README) pour l'alerte, `#B42318` / `#FDECEA` (écran Fiche asset) pour l'erreur ; un test interdit toute couleur absente de `docs/maquette` | — |
| 1.15 | Polices | La maquette charge IBM Plex depuis Google Fonts ; la note de Réglages dit « rien ne part ailleurs que vers ces services » | IBM Plex servie en local (paquets @fontsource, licence OFL) ; un test interdit tout appel vers Google Fonts | — |
| 1.16 | « Nouveau lot » | Maquette : mène au Brief ; le lot se crée à l'étape 3 | Mène à `/lots/nouveau` : « Nouveau lot · Arrive à l'étape 3 du plan » | — |
| 1.17 | Route de santé | Plan : « une route /sante qui répond ok » ; convention : tout sous `/api` | Les deux existent : `/sante` et `/api/sante` | — |
| 1.18 | Modèle de données dès l'étape 1 | A1 (fonctionnalités) met toutes les tables à l'étape 1 ; les textes 1b-1d n'en créent aucune | Le schéma complet A1 est créé (vide) par la migration 000, avec en plus `couts`, `bancs`, `publications`, `regles_routage` | Garder ces tables en avance ? |
| 1.19 | Identifiants des modèles Claude | Maquette : « Sonnet 5.5 / Haiku 5.5 » ; le test de connexion liste les modèles via `GET /v1/models` | Liste figée `claude-sonnet-5-5` / `claude-haiku-5-5` dans la config et l'écran | Liste dynamique depuis l'API ? À vérifier à l'étape 12 |
| 1.20 | Test de connexion itch.io réel | Le plan dit « on vérifie que butler répond » ; la maquette n'a ni clé ni chemin pour butler | `butler version` + vérification de la clé par `GET https://itch.io/api/1/key/me` et concordance avec le compte réglé ; aucune page de jeu supposée (chaque pack aura la sienne) | OK ? |
| 1.21 | Test ComfyUI | La maquette dit « Pixal3D et Trellis.2 trouvés au dernier test », que `/system_stats` ne donne pas | Texte neutre : carte graphique et mémoire lues au test | — |
| 1.22 | glTF-Validator | 1a justifie Node « pour le validateur glTF » (paquet npm) ; la maquette attend un exécutable `gltf_validator` | Exécutable (binaire Khronos) ou commande du PATH | Lequel ? |
| 1.23 | Mode production | L'API sert `web/dist/` quand l'interface est construite | Non couvert par le test bout en bout (Vite seulement) ; testé unitairement | — |
| 1.24 | Ce qui reste dans l'archive | Le brouillon précédent contenait un worker, une file de tâches, des générateurs, un pipeline et un style v0 | Non repris à l'étape 1 ; réimportés à leur étape (2, 3, 4, 5) depuis `claude/sleepy-mendel-tc8e34`, qui reste intacte | Poser un tag d'archive sur cette branche ? |
| 1.25 | Cibles cliquables de 44 px | Le README de la maquette exige 44 px minimum ; `Settings.dc.html` lui-même emploie 40 px (champs, « Tester la connexion », « Dupliquer en v1 »), 36 px (Garder, Refaire) et 44 px seulement sur la recherche, la cloche, Annuler et Enregistrer | Comme la maquette : 44 px pour les boutons principaux, 40 px pour les champs et petits boutons, 36 px pour « Tout marquer lu » | Faut-il tout monter à 44 px (README) ou suivre les écrans (40) ? |
| 1.26 | butler dans Réglages | Le plan vérifie que butler répond ; la maquette n'a qu'un bouton « Tester butler » sur la carte itch.io | Pas de carte outil butler : le chemin et la présence sur la machine sont affichés sur la carte itch.io ; « Tester butler » teste l'adaptateur itch.io (simulé : Connecté sans appeler butler ; réel : butler + clé) | Une carte outil dédiée ? |
| 1.27 | Réponses d'API écrites à la main dans deux tests web | ARCHITECTURE : « les tests de l'interface ne simulent l'API qu'avec contrat.json » | Les réponses *dynamiques* (résultat de recherche selon la requête, message d'un test de connexion réussi en réel) sont écrites dans le test, avec la forme du contrat | Acceptable, ou générer aussi ces cas ? |

## Étape 2 · Styles

| # | Sujet | Ce que disent les sources | Choix provisoire dans le code | Question |
|---|---|---|---|---|
| 2.1 | Assistant « Nouveau style » : étape 2 ou 6 ? | D3 (étape 2) : « création et passage de version » ; correction 10 : l'assistant (décrire, palette, images d'inspiration, 6 premiers objets) ; la ligne de l'étape 6 du plan mentionne « assistant Nouveau style » | Livré à l'étape 2 en entier : il ne dépend pas de Blender (images Meshy, simulées par défaut) | À confirmer |
| 2.2 | Formulaire « Modifier » | Non dessiné dans la maquette | Fenêtre provisoire : nom, description, palette (couleur et nom), budgets de triangles, densité de texels ; refusée (409) si un lot utilise la version | Quels champs doivent être modifiables ? |
| 2.3 | Répercussion d'un matériau modifié | Note du canvas et audit : « se répercute sur les assets de la voie code » ; correction 11 (qui prime) : une nouvelle version ne touche aucun lot, on passe par « Appliquer la v1 » | Aucune répercussion automatique ; une version utilisée par un lot ne se modifie plus (on duplique) | À confirmer |
| 2.4 | Bouton « Appliquer la v1 » | Correction 11 ; dessiné nulle part (ni Lots, ni en-tête de lot, ni Brief) | Pas encore construit ; prévu dans l'en-tête de lot à l'étape 3, en estimation d'abord (le lancement attend les étapes 5 et 7) | Où le placer ? |
| 2.5 | Taille de la palette | `NewStyle.dc.html` : 6 couleurs ; cahier des charges : 8 à 12 couleurs nommées | 8 à 12 exigées (le validateur du yaml l'impose) ; la palette est reprise du style de référence choisi, puis retouchée | — |
| 2.6 | Les 6 objets génériques de la planche | Maquette : Tonneau, Caisse, Lanterne… (médiéval) ; planche Rome : scutum, amphore… | Liste `objets_planche` dans le style.yaml (6 types parmi `dimensions_m`), reprise du style de référence | Liste fixe par style, ou choisie par Claude selon le thème ? |
| 2.7 | Champs que l'assistant ne demande pas mais que le yaml exige | Code thème (`ROM`), direction, matériaux, dimensions par type, tolérances, gabarits de consignes | Copiés du style de référence choisi ; « Les saisir à la main » demande budgets, texels et dimensions ; le code thème d'un nouveau style = 3 premières lettres du nom (provisoire) ; un matériau par couleur de la palette (réglages repris de la référence quand la couleur de base existe) | Comment choisir le code thème d'un style ? |
| 2.8 | `materials.blend` | Cahier des charges : « shaders partagés dans un seul fichier .blend » ; le brouillon précédent reconstruit les matériaux depuis le yaml | Les matériaux vivent dans le yaml (base, rugosité, métal) ; aucun .blend promis | Qui fait foi ? |
| 2.9 | Disposition sur le disque | Cahier des charges : `style/style.yaml` et `style/board/` ; deux versions doivent coexister | `style/<code>/style.yaml`, `style/<code>/board/`, `style/<code>/inspiration/` ; une version = un dossier | — |
| 2.10 | Actif / Brouillon | Maquette : « Brouillon, jamais appliqué à un lot » | Actif = validé (au moins une image gardée) ; Brouillon = pas encore validé | Actif doit-il vouloir dire « utilisé par un lot » ? |
| 2.11 | Ouvrir un style précis | Le README de la maquette ne prévoit que `/styles` | `/styles?style=<code>` (la puce du style dans l'en-tête de lot y mènera) | — |
| 2.12 | Images de la planche à l'écran | « Images validées à la main » | Un style validé ne montre que ses images gardées ; un brouillon montre tout ce qui a été généré | — |
| 2.13 | Crédits de la planche | 6 images à 3 crédits, « Refaire » à 3 crédits | Comptés depuis l'adaptateur Meshy (simulé : solde du simulateur) ; les images remplacées comptent toujours dans « crédits dépensés sur cette planche » ; pas encore de ligne dans la table des coûts (suivi des coûts : étape 4) | — |
| 2.14 | Le worker tourne dès l'étape 2 | Le plan met la file de tâches à l'étape 4 | La planche est une tâche Meshy : la file et le worker du brouillon précédent sont repris maintenant (sans écran Génération), avec une erreur définitive sans relance pour les crédits insuffisants | — |
| 2.15 | Style pilote livré avec le dépôt | « Aucun nom de thème en dur dans l'app » | `style/rome-stylise-v0/style.yaml` est une donnée du dépôt (thème d'essai), importée au démarrage ; l'app n'en connaît aucun nom en dur | — |

## Étape 3 · Lots et Brief (API livrée ; écrans à faire)

| # | Sujet | Ce que disent les sources | Choix provisoire dans le code | Question |
|---|---|---|---|---|
| 3.1 | Où vivent les règles de routage | Audit : réglage de configuration ; brouillon précédent : une table | Table `regles_routage`, 7 règles dans l'ordre de la maquette (Générateurs), lues dans l'ordre ; lecture seule par `GET /api/routage/regles`, éditeur à l'étape 11 | — |
| 3.2 | Ce que Claude classe | B3 : « une voie selon sa catégorie » ; maquette : le routage suit géométrique / ornemental / mixte / personnage | Claude donne deux champs : `categorie` (petit_prop…module_archi, pour le budget) et `nature` (pour le routage). Claude ne choisit jamais la voie | — |
| 3.3 | Règle « Équivalent CC0 » | Le catalogue CC0 arrive avec l'étape 7 | La règle est en place mais ne trouve jamais rien ; `operationnelle: false` dans la route des règles | — |
| 3.4 | Règle « Déjà dans ta bibliothèque » | Maquette : « réutilisée telle quelle » | Un asset au statut `garde` dont le type (de l'objet d'origine ou du nom) est le même, après normalisation ; pas de condition sur le style ni sa direction | Faut-il exiger le même style, ou la même direction ? |
| 3.5 | Objet mixte sans générateur pour sa pièce géométrique | Maquette : la colonne a son fût en code | La règle 4 s'applique, mais l'objet passe « À créer » tant que la pièce géométrique n'a pas de générateur | — |
| 3.6 | Personnage ou créature | Règle 7 « Hors périmètre pour l'instant » ; aucun exemple dans le Brief dessiné | L'objet est listé avec sa pastille, décoché d'office, et retiré à la validation du brief | Le montrer, ou le cacher ? |
| 3.7 | Dimensions d'un objet | Le style a des dimensions réelles par type ; Claude en propose aussi | Celles du style quand le type y figure (`source: style`), sinon celles de Claude (`source: claude`) | — |
| 3.8 | « Reproposer la liste » | Maquette : un bouton, rien sur ce qui est gardé | Remplace les objets encore au Brief ; garde, par type d'objet, les décochages et les voies choisies à la main ; ne touche pas aux objets déjà passés en Références | — |
| 3.9 | Nom du lot | Absent du Brief dans la maquette ; présent dans Lots et l'en-tête | Claude propose `nom_lot` ; il n'est écrit que si le nom est vide ; modifiable ensuite | Le nom se saisit-il dans le Brief ? |
| 3.10 | Choix du style | Maquette : deux boutons « Stylisé / Semi-réaliste » | Le lot pointe un style en base (`style_id`) ; par défaut le premier style validé ; l'écran proposera la liste des styles | Deux boutons (direction) ou liste des styles ? |
| 3.11 | « Générer les références » à l'étape 3 | Audit : « crée une tâche d'images par objet » ; les images sont l'étape 6 | Les objets retenus passent à l'étape Références (les images arrivent à l'étape 6) ; refus s'il reste un objet « À créer » ; réutilisés : gardés d'office ; hors périmètre : retirés | Bloquer, ou laisser partir sans les « À créer » ? |
| 3.12 | Crédits du résumé | Audit : « 30 par objet IA ou mixte, plus 12 par objet pour ses 4 références » ; correction 1 : variantes code gratuites | 42 crédits par objet IA ou mixte ; 0 pour le code, le CC0, le réutilisé ; tarifs pris dans l'adaptateur Meshy, figés à la validation (`credits_prevus`) | Les objets code ont-ils aussi 4 références payantes ? |
| 3.13 | « Appliquer la vN » | Correction 11 ; dessiné nulle part | `GET /api/lots/{id}/appliquer-style` : estimation seulement (objets code gratuits, 30 crédits par objet IA) ; le lancement attend les étapes 5 et 7 ; bouton prévu dans l'en-tête de lot | Où le placer ? |
| 3.14 | Signature d'un générateur | CLAUDE.md : `build(params)` | `generators/CONTRAT.md` : `build(params, style, seed=0)` et un MANIFESTE complet (types, catégorie, famille, symétrie, pièces, paramètres, variantes) | Quelle signature fait foi ? |
| 3.15 | Nom du script et de la demande | Maquette : `ratelier.md`, type `ratelier_armes` | Tiré du type normalisé : « râtelier d'armes » donne `generators/demandes/ratelier_darmes.md` et `generators/ratelier_darmes.py` | Règle de nommage à fixer |
| 3.16 | Quand un script « rejoint le lot » | Maquette : « dès que le script apparaît et passe ses tests » | Le worker regarde `generators/` toutes les 30 s ; un MANIFESTE valide suffit pour re-router en voie code ; les tests du script (Blender) arrivent à l'étape 5 et l'état le dit | Attendre les tests avant de re-router ? |
| 3.17 | Quatrième file | Cahier : trois files (carte graphique, Meshy, Blender) | Une file `api` (4 en parallèle, non réglable) pour les appels à l'API Claude | — |
| 3.18 | Coût d'un brief simulé | Audit : ≈ 0,03 $ par brief | Ligne dans `couts` : tokens estimés, 0 $, `simule: true` ; les tarifs réels arrivent avec le suivi des coûts (étape 4) | — |
| 3.19 | Lot terminé : où mène « Voir les assets » | Maquette : vers la Bibliothèque | `/bibliotheque?lot=<id>` ; la Bibliothèque (étape 9) devra savoir filtrer par lot | — |
| 3.20 | Lots vides | Rien dans les sources | « Nouveau lot » crée un lot vide immédiatement ; un brouillon vide reste dans la liste | Les supprimer ? |
