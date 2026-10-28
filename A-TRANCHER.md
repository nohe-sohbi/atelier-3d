# À trancher avec Nohé

Ce fichier liste, étape par étape, les écarts entre la maquette (`docs/maquette/`), le cahier des
charges (`docs/cahier-des-charges/`) et le plan, rencontrés en construisant l'application, ainsi que
les choix **provisoires** faits dans le code pour que l'écran marche en attendant. Rien ici n'est
tranché : Nohé décide, puis le code ou les documents sont mis à jour. `docs/` n'est jamais modifié
par Claude Code (CLAUDE.md).

Ordre de foi (docs/cahier-des-charges/README.md) : plan > fonctionnalités > cahier des charges >
audit > maquette.

> **28 octobre 2026 : plus aucun « choix provisoire ».** Nohé exige zéro compromis. Les entrées marquées « choix
> provisoire » ci-dessous (S., C., V.) sont des dettes : elles sont reprises une par une dans `AUDIT-MAQUETTE.md`, où
> chaque écart devient du travail à faire, pas une décision. Rien n'est retiré de la maquette sans l'accord de Nohé.

## Décision du 28 octobre 2026 · Nouvelle maquette

**Tranché par Nohé** : la maquette v4 (`docs/maquette/`, validée le 28 octobre) remplace la maquette des 11 écrans
d'origine comme modèle des écrans. L'ancienne reste dans l'historique git (commit `89ac432` et précédents).

Conséquences, déjà appliquées :
- `docs/maquette/` contient la nouvelle maquette et un README aux règles mises à jour ;
- `tokens.css` reprend la palette de la nouvelle maquette (thème clair par défaut, sombre en option) ;
- la police est Inter, servie en local, à la place d'IBM Plex ;
- le test des couleurs vérifie la nouvelle maquette.

Conséquences à traiter écran par écran (rien n'est encore changé dans les écrans) :
- le parcours passe de 4 à 6 étapes (Objets, Look, Fabrication, Validation, **Essai**, **Jeu**) ;
- le vocabulaire change : Lot devient Projet, Brief devient Créer puis Objets, Références devient Look,
  Génération devient Fabrication, Revue devient Validation ;
- l'ordre de foi des documents n'est pas modifié : le cahier des charges reste la référence pour les données et
  les règles d'asset. Seul le contenu des écrans suit la nouvelle maquette ;
- les écarts entre le cahier des charges et la nouvelle maquette seront notés ici au fur et à mesure.

### Validation (28 octobre) · choix provisoires

L'écran Validation lit de vrais fichiers : le .glb de l'objet (niveaux de détail et collision dans un seul fichier),
ses 5 vues, ses 12 contrôles (`rapport.json`) et des mesures prises sur le fichier (taille, pose au sol, point
d'ancrage). Quatre décisions réelles : garder, jeter, refaire, corriger.

| N° | Sujet | Maquette | Choix provisoire dans le code |
|---|---|---|---|
| V.1 | « Corriger » | cinq façons : repeindre, retoucher les zones pointées, alléger, changer la taille, séparer en pièces | aucune de ces opérations n'existe dans la chaîne de fabrication. « Corriger » redessine 4 nouveaux looks en tenant compte des remarques (pastilles et texte), puis l'objet revient au Look. Objets faits par IA seulement (12 crédits) ; un objet fait par script se règle avec « Refaire » |
| V.2 | « Refaire » | quatre façons (même look avec consigne, autre look, retoucher le look, ta carte graphique) | un seul geste : retour au Look de l'objet, gratuit |
| V.3 | Avis de l'IA | un avis écrit par Claude | pas d'avis tant qu'aucune IA n'en écrit un : l'onglet le dit |
| V.4 | Choisir la collection | liste de collections et étiquettes | l'objet gardé entre dans la collection du projet (créée au besoin) ; le choix arrive avec la Bibliothèque (étape 9) |
| V.5 | Coût d'un objet | crédits et minutes | crédits seulement : la durée n'est pas enregistrée |
| V.6 | Pastilles de défaut | gardées avec l'objet | servent à écrire les remarques envoyées avec « Corriger » ; leur position n'est pas enregistrée |
| V.7 | Essai et Jeu | écrans suivants | le bouton « Essayer les objets ensemble » mène à une page « arrive à l'étape 8 du plan » |
| V.8 | Étape Validation du projet | verrouillée tant que tout n'est pas fabriqué | s'ouvre dès qu'un objet est prêt, même si d'autres sont encore en fabrication |

### Créer, Objets, Look, Fabrication (28 octobre) · choix provisoires

Le projet compte désormais six étapes dans l'API (migration 060 : `essai_fait`, `jeu_fait`) et dans l'interface.
Les clés techniques (`brief`, `references`, `generation`, `revue`) et les adresses ne changent pas : seuls les
libellés changent (Objets, Look, Fabrication, Validation).

| N° | Sujet | Maquette | Choix provisoire dans le code |
|---|---|---|---|
| C.1 | Écran Créer | modes « Objets / Kit modulaire / Décor complet », images jointes, options, statistiques, activité | seulement la phrase, le style et « À toi de jouer » : le reste n'existe pas dans l'API et n'est pas inventé |
| C.2 | Essai et Jeu | deux écrans | l'API connaît les deux étapes ; les écrans arrivent plus tard. D'ici là, un projet dont tous les objets sont décidés reste à « Essai » et ne peut pas devenir « Terminé » |
| C.3 | Écran Objets | une carte par objet, case à cocher, « Régler… » (taille, finesse) | structure d'origine gardée (panneau « Ta demande » et liste avec voies), vocabulaire et aide nouveaux. Les cartes de la maquette sont à reprendre |
| C.4 | Écrans Look et Fabrication | idem | structure d'origine gardée, vocabulaire et aide nouveaux |
| C.5 | « Nouveau lot » | formulaire Créer | `/lots/nouveau` renvoie à Créer : un projet vide n'est plus créé tout seul |
| C.6 | Notifications | — | « Revue prête » devient « À valider », « Références prêtes » devient « Looks prêts » |
| C.7 | Page Générateurs | absente du menu | lien dans Réglages |

### Socle de la nouvelle interface (28 octobre) · choix provisoires

Menu, en-tête, barre d'onglets du téléphone, thème et composants communs sont faits. Écarts avec la maquette,
à confirmer avec Nohé :

| N° | Sujet | Maquette | Choix provisoire dans le code |
|---|---|---|---|
| S.1 | Recherche globale | absente | gardée, derrière une loupe dans l'en-tête (on ne perd pas la fonction) |
| S.2 | Collections épinglées | absentes du menu (elles sont des filtres de la Bibliothèque) | retirées du menu ; reviennent avec l'écran Bibliothèque (étape 9) |
| S.3 | Entrée « Générateurs » | absente du menu | retirée ; la page reste à `/generateurs` (étape 11). À replacer, par exemple dans Réglages |
| S.4 | « Créer » | l'écran d'accueil, avec le formulaire | ouvre `/lots/nouveau` en attendant l'écran Créer, qui prendra la racine `/` |
| S.5 | Badges du menu | aucun | gardés sur Projets et Bibliothèque : ils comptent ce qui attend une action |
| S.6 | Crédits | solde restant | solde restant affiché, détail (utilisés, renouvellement, « solde simulé ») au survol et pour les lecteurs d'écran |
| S.7 | Six étapes | 6 étapes dans l'en-tête de projet | composant `Etapes` prêt et testé ; non branché : le contrat de l'API décrit 4 étapes, la partie serveur suit avec l'écran Projet (étape 2 de la reconstruction) |
| S.8 | Liste des lots sur téléphone | cartes | le tableau défile dans son cadre en attendant la refonte de l'écran Projets |

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
| 2.13 | Crédits de la planche | 6 images à 3 crédits, « Refaire » à 3 crédits | Tarif lu dans l'adaptateur Meshy (`GET /api/styles/estimation-planche`), seul chiffre affiché ; crédits d'une image : ceux que Meshy rend (`consumed_credits`), sinon ce tarif ; comptés depuis l'adaptateur Meshy (simulé : solde du simulateur) ; les images remplacées comptent toujours dans « crédits dépensés sur cette planche » ; pas encore de ligne dans la table des coûts (suivi des coûts : étape 4) | — |
| 2.14 | Le worker tourne dès l'étape 2 | Le plan met la file de tâches à l'étape 4 | La planche est une tâche Meshy : la file et le worker du brouillon précédent sont repris maintenant (sans écran Génération), avec une erreur définitive sans relance pour les crédits insuffisants | — |
| 2.15 | Style pilote livré avec le dépôt | « Aucun nom de thème en dur dans l'app » | `style/rome-stylise-v0/style.yaml` est une donnée du dépôt (thème d'essai), importée au démarrage ; l'app n'en connaît aucun nom en dur | — |
| 2.16 | Bouton « Retour » de la planche | `NewStyle.dc.html` : « Retour » au pied de l'étape 2 | Absent : le style est créé en quittant l'étape 1 ; on le corrige ensuite par « Modifier » | Retour = rouvrir l'étape 1 sur le brouillon (et le modifier) ? |
| 2.17 | Images d'inspiration | Maquette : « Dépose des images ici ou choisis des fichiers » | Bouton de choix de fichiers seulement, pas de glisser-déposer | Le glisser-déposer est-il attendu ? |
| 2.18 | Budgets repris d'un style | Maquette : la ligne les donne (« Petit 2 000 · moyen 6 000 · grand 15 000 · module 8 000 tris · 512 px/m · 1 = 1 m ») | Une phrase d'aide sans les chiffres : la liste des styles ne renvoie pas leurs budgets | Les afficher (la liste des styles les donnerait alors) ? |
| 2.19 | Direction d'un nouveau style | Le yaml exige `direction` (stylisé ou semi-réaliste) ; la maquette ne la demande pas, elle la sous-entend par le nom du style de référence | Reprise du style de référence, « stylisé » pour une saisie à la main ; jamais demandée | La demander dans l'assistant ? |
| 2.20 | Style pilote « Actif » sans image | Maquette : Actif = images validées | Le pilote est livré validé (`planche: []` dans son yaml) mais sans image ; « Générer la planche » reste proposé | Le livrer en brouillon, ou avec une planche ? |
| 2.21 | Ce que reçoit Meshy pour la planche | Correction 10 : « images d'inspiration » ; API Meshy (doc d'octobre 2026) : `text-to-image`, ou `image-to-image` avec 1 à 5 images de référence, une image par tâche | Une tâche par objet ; les images d'inspiration (5 au plus) partent en références de chaque image ; sans inspiration, texte seul ; modèle `nano-banana` (3 crédits l'image, le tarif du cahier) ; la consigne vient de la description du nouveau style | Toutes les inspirations pour chaque image (actuel), ou une par image ? Un autre modèle (6 à 12 crédits) ? |
| 2.22 | Planche d'un style qui connaît moins de 6 types | « 6 objets génériques » | Une image par type connu (6 au plus) ; aucun « objet-3 » inventé ; boutons et estimation suivent ce nombre | — |
| 2.23 | Renommer une couleur dans « Modifier » | Non dessiné | Une couleur renommée à la même place : les matériaux qui la prennent pour base la suivent ; une couleur retirée et encore utilisée est refusée avec le nom du matériau | Ajouter ou retirer des couleurs dans « Modifier » ? |
| 2.24 | État d'un style relu depuis ses fichiers | Le yaml est la seule source ; la base est locale (`atelier.db` non versionnée) | Clé `planche` dans le yaml = validé, avec pour chaque image gardée `{fichier, objet, simule}` ; une base neuve retrouve état et images gardées ; les crédits dépensés, eux, ne sont qu'en base | — |
| 2.25 | Deux styles du même nom | La table refuse deux fois le même nom dans la même version | Refus clair (409) à la création, à la modification et à la copie ; au démarrage, un dossier en double est ignoré et journalisé | — |
| 2.26 | Palette d'un nouveau style | Correction 10 : « tu décris le style, choisis la palette, ajoutes des images d'inspiration » ; ta demande du 21 oct. : la palette tirée des images, modifiable | Les images d'inspiration viennent avant la palette ; les déposer la remplit : couleurs dominantes de tes images, fond uni écarté, nommées d'après une liste de noms courants, complétées à 8 au besoin (nuances). Calcul local (Pillow), gratuit et instantané ; tout se retouche avant de créer le style | — |

## Étape 3 · Lots et Brief

| # | Sujet | Ce que disent les sources | Choix provisoire dans le code | Question |
|---|---|---|---|---|
| 3.1 | Où vivent les règles de routage | Audit : réglage de configuration ; brouillon précédent : une table | Table `regles_routage`, 7 règles dans l'ordre de la maquette (Générateurs), lues dans l'ordre ; lecture seule par `GET /api/routage/regles`, éditeur à l'étape 11 | — |
| 3.2 | Ce que Claude classe | B3 : « une voie selon sa catégorie » ; maquette : le routage suit géométrique / ornemental / mixte / personnage | Claude donne deux champs : `categorie` (petit_prop…module_archi, pour le budget) et `nature` (pour le routage). Claude ne choisit jamais la voie | — |
| 3.3 | Règle « Équivalent CC0 » | Le catalogue CC0 arrive avec l'étape 7 | La règle est en place mais ne trouve jamais rien ; `operationnelle: false` dans la route des règles | — |
| 3.4 | Règle « Déjà dans ta bibliothèque » | Maquette : « réutilisée telle quelle » | Un asset au statut `garde` dont le type (de l'objet d'origine ou du nom) est le même, après normalisation ; pas de condition sur le style ni sa direction | Faut-il exiger le même style, ou la même direction ? |
| 3.5 | Objet mixte sans générateur pour sa pièce géométrique | Maquette : la colonne a son fût en code | La règle 4 s'applique, mais l'objet passe « À créer » tant que la pièce géométrique n'a pas de générateur | — |
| 3.6 | Personnage ou créature | Règle 7 « Hors périmètre pour l'instant » ; aucun exemple dans le Brief dessiné | L'objet est listé avec sa pastille « Hors périmètre », décoché d'office, sa case grisée (non cochable), et retiré à la validation du brief | Le montrer, ou le cacher ? |
| 3.7 | Dimensions d'un objet | Le style a des dimensions réelles par type ; Claude en propose aussi | Celles du style quand le type y figure (`source: style`), sinon celles de Claude (`source: claude`) | — |
| 3.8 | « Reproposer la liste » | Maquette : un bouton, rien sur ce qui est gardé | Remplace les objets encore au Brief ; garde, par type d'objet, les décochages et les voies choisies à la main ; ne touche pas aux objets déjà passés en Références | — |
| 3.9 | Nom du lot | Absent du Brief dans la maquette ; présent dans Lots et l'en-tête | Claude propose `nom_lot` ; il n'est écrit que si le nom est vide ; modifiable ensuite | Le nom se saisit-il dans le Brief ? |
| 3.10 | Choix du style | Maquette : deux boutons « Stylisé / Semi-réaliste » | Le lot pointe un style en base (`style_id`) ; par défaut le premier style validé ; le Brief propose la liste des styles en base (nom, code, « brouillon » s'il n'est pas validé) | Deux boutons (direction) ou liste des styles ? |
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
| 3.21 | Vignettes des objets du Brief | Maquette : un dessin par objet (56 px) | Aucune vignette : au Brief, aucune image n'existe encore, et un dessin inventé serait une fausse donnée | Une vignette à partir de l'étape Références ? |
| 3.22 | Nom du lot dans l'en-tête | Maquette : titre fixe | Bouton crayon « Renommer le lot » qui ouvre un champ (Entrée enregistre, Échap annule) ; un lot sans nom s'affiche « Lot sans nom » | — |
| 3.23 | Onglets des étapes | Maquette : les 4 onglets sont des liens | Une étape pas encore atteinte reste visible mais verrouillée (`aria-disabled`, ne s'ouvre pas) | — |
| 3.24 | « Appliquer la vN » | Dessiné nulle part (3.13) | Bouton dans les actions de l'en-tête, à côté de « Dupliquer le lot », seulement quand une version validée plus récente existe ; il ouvre une fenêtre d'estimation sans bouton de lancement | — |
| 3.25 | Bouton de proposition | Maquette : « Reproposer la liste » seulement | « Proposer la liste » tant qu'il n'y a pas de liste, « Reproposer la liste » ensuite ; le thème et le besoin s'enregistrent en quittant le champ, et avant la demande | — |
| 3.26 | Bandeau « simulé » du Brief | Règle : ce qui vient d'un adaptateur simulé est marqué | « simulé · Liste simulée : l'API Claude est en mode simulé (Réglages). Ces objets servent à essayer l'écran. » | Texte à valider |
| 3.27 | Place de l'en-tête de lot | Maquette : bandeau pleine largeur sous la barre du haut | Carte en haut de la page, dans la colonne de contenu, comme les autres écrans | — |
| 3.28 | Texte d'état de la demande pour Claude Code | Maquette : « …Il apparaît aussi dans Générateurs, section Générateurs à écrire » ; « dès que le script apparaît et passe ses tests » | Générateurs arrive à l'étape 11 : pas de renvoi ; le texte dit que les tests du script arrivent à l'étape 5 (3.16) | — |
| 3.29 | « Mis à jour » dans Lots | Maquette : « il y a 40 min », « hier », « 8 oct. » | Calculé depuis `maj_le` : minutes, heures, « hier », puis la date courte | — |

## Étape 4 · File de tâches et Génération

| # | Sujet | Ce que disent les sources | Choix provisoire dans le code | Question |
|---|---|---|---|---|
| 4.1 | Génération avant la fabrication | Plan : étape 4 = écran Génération ; aucun objet n'atteint la génération avant les étapes 5 à 7 (et 6 pour les références) | L'écran montre les vraies données : tuiles, objets « Attend sa référence », puces à faire, une phrase qui dit quand la fabrication arrive ; l'onglet reste verrouillé tant que le lot n'est pas à l'étape 3 ; l'écran s'ouvre aussi par son adresse et depuis Réglages | Ouvrir l'onglet Génération dès le brief validé ? |
| 4.2 | « Relances auto » | Maquette : « relance 2 sur 3 » (relances de qualité, après la finition) | La tuile compte les relances techniques des tâches du lot (tentatives au-delà de la première) ; les relances de qualité arrivent avec l'étape 5 | — |
| 4.3 | Tâches du lot | Maquette : seulement les objets | Section « Tâches du lot » sous la file : état, tentatives, erreur, journal (icône), Relancer pour une tâche échouée ou annulée, Annuler pour une tâche en attente ou en cours | Garder ? |
| 4.4 | Worker visible | Rien dans les sources | Le worker note un battement toutes les 5 s (table `workers`) ; Génération et Réglages disent « Worker actif » ou « Le worker ne tourne pas » avec son dernier signe de vie | — |
| 4.5 | File de tâches dans Réglages | Maquette : les limites des files seulement | Sous les limites : l'état du worker et les tâches actives ou récentes de tous les lots et styles, avec lien vers leur lot ou leur style, journal, Relancer, Annuler | Un écran à part ? |
| 4.6 | Notification de l'ordinateur | Correction 14 : « même onglet fermé », à activer dans Réglages | **Reportée (décision de Nohé, 20 oct.)** : la cloche de l'app suffit pour l'instant ; on en reparle quand la revue existera. Piste recommandée alors : ntfy sur le serveur, notification sur le téléphone et le PC même app fermée (l'app s'ouvre en http://192.168.1.21 : les navigateurs y refusent leurs propres notifications) | À rouvrir à l'étape 8 |
| 4.7 | Tarifs de l'API Claude | Audit : ≈ 0,03 $ par brief, ≈ 0,02 $ par avis | Tarifs officiels relevés le 6 octobre 2026 (Sonnet 5.5 : 2 $ / 10 $ par million de tokens ; Haiku 5.5 : 0,10 $ / 0,50 $), modifiables dans `config.local.yaml` ; un modèle sans tarif est compté mais pas chiffré | — |
| 4.8 | Plafond mensuel Claude | Maquette : « Règle le même plafond dans la Console » | L'app l'applique aussi : avant chaque appel réel, si la dépense notée du mois atteint le plafond, la tâche échoue tout de suite, sans relance, avec le motif | — |
| 4.9 | « Dépensé ce mois » | Réglages | Dépense réelle seulement ; les appels simulés sont comptés à part, gratuits | — |
| 4.10 | Crédits Meshy du lot | Maquette : « 156 utilisés · 126 prévus + 1 relance » | « N utilisés » (somme des coûts Meshy du lot, « · simulé » s'ils le sont) et « N prévus à la validation du brief » ; les crédits de la planche d'un style comptent pour le style, pas pour un lot | — |
| 4.11 | Rafraîchissement | Plan cloud : SSE ou interrogation | Interrogation : menu et cloche toutes les 15 s (onglet visible) ; Génération toutes les 2 s quand quelque chose tourne, 15 s sinon | — |
| 4.12 | « Revue prête » | A4, correction 14 | L'événement s'écrira quand un objet atteindra la revue : rien ne l'atteint avant l'étape 5 | — |
| 4.13 | Lancer la fabrication | Plan cloud : `POST /api/lots/{id}/lancer` | Pas de route ni de tâche tant que les étapes 5 et 7 ne sont pas construites : aucune tâche fantôme | — |
| 4.14 | Ports | — | `python dev.py` prend le premier port libre au-dessus de 5173 si un autre projet le tient, et l'annonce ; les tests bout en bout tournent sur 5199 (`ATELIER_E2E_PORT`) | — |
| 4.15 | Alerte crédits Meshy | Réglages : notification « crédits à 80 % » (ou 90 %) | Une notification dans la cloche quand la part utilisée du mois atteint le seuil, une seule par mois, marquée « (simulé) » en mode simulé | — |

## Étape 5 · Fabrication par code

| # | Sujet | Ce que disent les sources | Choix provisoire dans le code | Question |
|---|---|---|---|---|
| 5.1 | Lancer la fabrication | Correction 1 : pour un objet code, l'écran Références montre 4 variantes rendues par Blender et tu en choisis une (étape 6) | Remplacé à l'étape 6 (6.8) : on lance depuis les Références ; Génération garde « Refaire » pour un échec | — |
| 5.2 | Un contrôle bloquant en échec | Maquette : « relance 2 sur 3 » | Voie code : échec tout de suite, sans relance (un générateur rejouable redonne le même résultat), avec la liste des contrôles en échec ; les relances de qualité sont pour la voie IA (étape 7) | — |
| 5.3 | Matériaux d'un générateur | Générateur : « matériaux du style, jamais en dur » | Le générateur nomme les matériaux du style qu'il emploie (le scutum : pourpre, bois, bronze, ocre, cuir) ; un style qui ne les a pas fait échouer la génération avec le nom du matériau manquant | Des rôles (métal, bois, peinture) que chaque style relie à ses matériaux ? |
| 5.4 | Textures de la voie code | Spécification : textures PBR (couleur, normal, ORM), usure du style | Pas encore de cuisson : les couleurs viennent des matériaux du style, l'usure n'est pas appliquée, la densité de texels dit « aucune texture » (non bloquant) | Cuire les textures (et l'usure) pour la voie code ? |
| 5.5 | Licence d'un asset | Cahier : licence de publication proposée CC0, choisie à la publication ; `validate.py` refuse une source hors liste blanche | `meta.json` sans licence tant que l'asset n'est pas publié ; seules les sources sont contrôlées | — |
| 5.6 | glTF-Validator absent | Contrôle bloquant | Bloquant aussi quand l'outil manque, avec « renseigne son chemin dans Réglages » (l'archive le rendait facultatif) | — |
| 5.7 | Rendus | « 5 vues standard, une planche de contact par lot, une vue en contexte » | 5 vues de 512 px par asset, lumière et caméra fixes, EEVEE (Cycles en secours) ; une planche par asset ; la planche du lot et la vue en contexte viennent avec la Revue (étape 8) | — |
| 5.8 | Pièces déclarées | `CONTRAT.md` : toutes les pièces séparées | Le scutum de l'archive en déclarait 2 pour 3 (coque, umbo, poignée) : corrigé | — |
| 5.9 | Nom d'un asset | `ROM_PROP_Scutum_A` | Thème du style, PROP (ou ARCHI pour un module d'architecture), type d'objet en un mot, première variante libre ; un objet garde son nom d'un essai à l'autre | — |
| 5.10 | Fichiers d'un essai | Arborescence : `assets/<theme>/<id>/` pour les livrables | Chaque essai dans `lots/<lot>/<objet>/essai-<n>/` (glb, fbx, blend, meta.json, rapport.json, rendus) ; la copie vers `assets/` se fait quand l'asset est gardé (étapes 8 et 9) | — |
| 5.11 | Défauts du scutum repris de l'archive | Motifs de rejet : « motif peint flou », « dos incohérent » | Motif des ailes en gros pixels, dôme de l'umbo visible au dos : laissés tels quels, à juger en revue | Les corriger avant la revue ? |
| 5.12 | Les 6 premiers générateurs | Plan : « les 6 premiers générateurs » | Scutum, gladius, pilum, amphore, colonne repris de l'archive (pièces déclarées corrigées : 1 pour gladius, pilum et colonne, 3 pour l'amphore) ; la caisse est nouvelle (cadre en saillie, panneaux en planches, cadre bois ou fer) | — |
| 5.13 | Largeur de l'amphore | Style : amphore de 0,35 m de large ; l'archive : « diamètre de la panse = largeur hors tout » | Les anses de l'archive dépassaient la panse de 1 cm (calcul du point le plus large faux) : corrigé, l'anse reste ronde et son attache basse remonte sur l'épaule ; le pommeau du gladius était 0,2 mm trop fin : corrigé. Les dimensions de chaque générateur sont testées au millimètre | — |
| 5.14 | Pièces d'un objet selon ses paramètres | `CONTRAT.md` : un nombre de pièces fixe dans le MANIFESTE | Réglé à l'étape 6 (6.10) : un générateur dont le nombre de pièces dépend des réglages expose `pieces(params)` | — |


## Étape 6 · Références

| # | Sujet | Ce que disent les sources | Choix provisoire dans le code | Question |
|---|---|---|---|---|
| 6.1 | Quand les propositions arrivent | Brief : le bouton s'appelle « Générer les références » ; l'estimation du brief compte 4 images par objet IA | À la validation du brief : une tâche par objet (images : file Meshy ; variantes : file Blender) ; l'écran se remplit seul. « 4 autres » demande une nouvelle série : l'ancienne quitte l'écran, sauf l'image choisie | — |
| 6.2 | Consigne d'une image | B4 : « prompt tiré du style et de l'intention » ; ton choix du 21 oct. : pouvoir réécrire la consigne | Gabarit du style (prop ou archi) rempli avec le nom et la description de l'objet ; réécrite à la main pour un objet (crayon), elle sert aux séries suivantes ; vide : celle de l'app revient | — |
| 6.3 | Ta propre image | Ton choix du 21 oct. : donner sa propre image | Elle devient le choix tout de suite (gratuit) ; « 4 images d'après ton image » l'envoie à Meshy comme modèle, avec une seule image de la planche du style pour les couleurs | La planche du style doit-elle accompagner ton image, ou ton image seule ? |
| 6.4 | Images qui guident Meshy par défaut | Maquette : « quatre images générées à partir de la planche du style » | Les images gardées de la planche du style (4 au plus), à défaut ses images d'inspiration, sinon la consigne seule | — |
| 6.5 | Les 4 versions d'un objet code | Correction 1 : « 4 versions du script avec des réglages différents » | 1re série : les variantes nommées du générateur, puis des tirages ; tirages rejouables, choix et cases libres, décimaux dans la moitié centrale de leur plage, entiers et dimensions du style gardés ; une version dont l'image est identique à une autre est écartée (réglage invisible) ; la légende nomme les 2 réglages qui s'écartent le plus | — |
| 6.6 | Objets sans référence au lancement | Maquette : « sera ignoré » | Mis de côté (retirés du lot), annoncé à côté du bouton avant le clic | — |
| 6.7 | Objets IA après le lancement | La voie IA arrive à l'étape 7 | Ils passent à Génération et y attendent avec leur image choisie (vignette) ; ils ne comptent pas « en cours » tant que rien ne tourne pour eux | — |
| 6.8 | Où se lance la fabrication | Maquette : « Lancer la génération 3D » sur Références ; Génération : « Toi : rien » | Le bouton « Fabriquer les objets code » de Génération est retiré ; l'onglet Génération s'ouvre au lancement. Sur Génération, un objet code en échec garde « Refaire » (si l'échec venait de la machine) et gagne « Choisir une autre version » (retour aux Références : le même réglage redonnerait le même échec) | — |
| 6.9 | Notification « Références prêtes » | Accueil : « références à choisir » ; ton choix : la cloche suffit pour l'instant (4.6) | Une fois par lot, quand chaque objet a ses propositions ; « 4 autres » ne re-prévient pas | — |
| 6.10 | Pièces d'un objet selon ses réglages | `CONTRAT.md` | Un générateur peut exposer `pieces(params)` (l'amphore : 3 avec anses, 1 sans) ; la fabrication et les contrôles l'utilisent | — |
| 6.11 | Crédits des images | Cahier : 3 crédits l'image | « 12 crédits » la série, tarif lu dans l'adaptateur Meshy ; chaque image note ce que Meshy a vraiment pris, dans le coût du lot | — |
| 6.12 | Assistant « Nouveau style » | La ligne de l'étape 6 du plan le cite | Déjà livré à l'étape 2 (2.1) | — |

## Étape 7 · Fabrication IA

| # | Sujet | Ce que disent les sources | Choix provisoire dans le code | Question |
|---|---|---|---|---|
| 7.1 | Deux files pour un objet IA | Cahier : files Meshy, Blender, carte graphique en parallèle | Deux tâches par essai : `generer_ia` (file Meshy : l'image part, le GLB revient) puis `finir_ia` (file Blender : la même chaîne que la voie code). Attendre Meshy n'occupe pas Blender | — |
| 7.2 | Ce qu'on demande à Meshy | Doc Meshy du 21 oct. 2026 (image vers 3D) ; tarifs : 30 crédits l'objet texturé 2K | Modèle `latest`, texture PBR 2K (le moins cher qui soit texturé), remaillage en triangles au budget de triangles du style pour la catégorie. L'image part en data URI (jamais d'URL publique) | — |
| 7.3 | Ce que la finition corrige seule | Audit : « échelle, petits morceaux, triangles en trop » ne relancent rien | Débris (morceau sous 2 % de la surface) retirés, fissures (trous jusqu'à 16 côtés) bouchées, taille, triangles (LOD), textures ramenées à la taille du style (2K de Meshy → 1024 pour un prop) | — |
| 7.4 | Dimensions et symétrie d'un objet IA | Cahier : dimensions ± 5 %, symétrie 5 mm, bloquants ; audit : relance « pour des proportions fausses » | La plus grande dimension est amenée à celle prévue et contrôlée (bloquant) ; les proportions et la symétrie sont mesurées et affichées pour la revue, sans bloquer : les dimensions d'un objet hors du style sont une estimation de Claude, et chaque relance coûte 30 crédits | Garder ce choix après l'essai réel ? |
| 7.5 | Relance automatique | Audit : « relance automatique, 3 au plus » | Un contrôle bloquant en échec (maillage ouvert, UV qui se chevauchent…) relance un nouvel essai Meshy, autant que « Relances automatiques » dans Réglages (3) ; la tâche se termine sans alerte, l'alerte vient à la fin si tout a échoué. Un essai que Meshy rate lui-même est remboursé par Meshy et redemandé par la file | — |
| 7.6 | Provenance d'un objet IA | Cahier : « chaque asset sait d'où il vient » ; liste blanche des licences | Source : Meshy image vers 3D, licence Meshy-Pro ; l'image de référence est notée dans les paramètres (image Meshy, ou ton image : ses droits se vérifient à la publication, étape 10) | — |
| 7.7 | Un objet IA en échec | — | Génération propose « Refaire » (même image, nouvel essai) et « Choisir une autre image » (retour aux Références) | — |
| 7.8 | Meshy simulé | Règle : le simulé répond comme le vrai | Le simulateur rend un objet comme Meshy : Y en haut, quelques milliers de triangles, texture 2K, un petit débris à retirer | — |
| 7.9 | Planches de contact | — | Le titre et les vues sont écrits avec une police qui a les accents (la police intégrée à Pillow ne les a pas) | — |
