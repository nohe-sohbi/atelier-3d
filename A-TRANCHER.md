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
