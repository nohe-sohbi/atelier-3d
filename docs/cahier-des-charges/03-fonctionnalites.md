# Fonctionnalités à développer

> Copie du document « Cahier des charges – Bibliothèque d'assets 3D », exportée le 17 oct. 2026. Ne la modifie pas ici : elle est régénérée depuis le document. Voir [README.md](README.md).

28 fonctionnalités, rangées en 4 blocs. En les branchant sur la maquette, 17 failles sont apparues ; 16 demandent de modifier ou d'ajouter un écran. J'en corrige 15 moi-même. Deux dépendent de ce que tu veux : quand construire les écrans, et où publier ta bibliothèque.

## Les 28 fonctionnalités

Chaque ligne dit ce que la fonctionnalité fait et où elle se voit dans la maquette. L'étape est celle du plan de développement où elle est construite. Les tailles sont relatives : une grosse vaut environ deux moyennes, une moyenne environ trois petites. Avec ces tailles, l'interface pèse environ un quart du travail et le pipeline les trois quarts.

### A · Socle

| # | Fonctionnalité | Ce qu'elle fait | Où dans l'interface | Étape | Taille |
| --- | --- | --- | --- | --- | --- |
| A1 | Modèle de données | Tables SQLite : lots, objets, essais, versions, assets, collections, étiquettes, styles, générateurs, tâches, événements | Tous les écrans lisent ici | 1 · Socle | Moyenne |
| A2 | Interface et API locales | Serveur Python (FastAPI) et interface React ; menu et en-tête de lot partagés ; recherche globale en SQLite FTS5. Le squelette à l'étape 1, chaque écran à son étape | Les 14 écrans | 1 · Socle | Grosse |
| A3 | File de tâches | Tâches enregistrées en base, exécutées par un worker ; relances ; reprise après coupure | Génération, lots en cours de l'Accueil, badges | 4 · File de tâches | Grosse |
| A4 | Journal et notifications | Chaque étape de la file écrit un événement ; « À faire » et badges sont des requêtes | Accueil (À faire, Activité), cloche, badges du menu | 4 · File de tâches | Petite |
| A5 | Réglages et secrets | Fichier de configuration local, adaptateurs réels et simulés, tests de connexion | Réglages | 1 · Socle | Petite |
| A6 | Suivi des coûts | Crédits par tâche Meshy, tokens par appel Claude, solde Meshy | Jauge du menu, Accueil, estimation du Brief, Génération, Réglages | 4 · File de tâches | Petite |

### B · Fabriquer un lot

| # | Fonctionnalité | Ce qu'elle fait | Où dans l'interface | Étape | Taille |
| --- | --- | --- | --- | --- | --- |
| B1 | Lots et étapes | Créer, dupliquer ; état suivi objet par objet, étape du lot calculée | Lots, en-tête de lot, Nouveau lot | 3 · Lots et Brief | Moyenne |
| B2 | Proposition de liste | Appel Claude en JSON structuré : objets, description, dimensions, catégorie | Brief : Reproposer la liste | 3 · Lots et Brief | Petite |
| B3 | Routage | Règles ordonnées qui donnent une voie à chaque objet selon sa catégorie | Brief (pastilles de voie), Générateurs (règles) | 3 · Lots et Brief | Moyenne |
| B4 | Images de référence | Prompt tiré du style et de l'intention, Meshy image-to-image, 4 propositions, choix ; variantes Blender pour la voie code | Références | 6 · Références | Moyenne |
| B5 | Adaptateur Meshy | Image vers 3D avec remesh, suivi par sondage ou flux SSE, téléchargement du GLB | Génération, Générateurs | 7 · Fabrication IA | Moyenne |
| B6 | Adaptateur ComfyUI | Workflows Pixal3D et Trellis.2 au format API, suivi par websocket, récupération des fichiers | Génération, Générateurs, Ajouter un générateur | 7 · Fabrication IA | Moyenne |
| B7 | Générateurs code | Cadre commun (manifeste, paramètres, matériaux du style) puis un générateur par type, le scutum d'abord | Brief (voie Code, « À créer »), Génération | 5 · Fabrication par code | Grosse |
| B8 | Import CC0 | Catalogue local des packs téléchargés et API Poly Haven ; import avec sa licence | Brief (voie CC0), Fiche asset (provenance) | 7 · Fabrication IA | Moyenne |
| B9 | Assemblage mixte | Joint la pièce IA à la pièce code, mise à l'échelle sur les cotes du code | Génération (colonne) | 7 · Fabrication IA | Moyenne |
| B10 | Finition | Échelle, pivot, nettoyage, décimation, LOD, collision, export GLB et FBX | Génération (étape Finition) | 5 · Fabrication par code | Grosse |
| B11 | Tests automatiques | Les 12 contrôles du cahier des charges, seuils lus dans le style | Génération (Tests), Revue (12/12), Fiche asset | 5 · Fabrication par code | Grosse |
| B12 | Rendus | 5 vues, mise en contexte, vignettes | Revue, Fiche asset, Bibliothèque | 5 · Fabrication par code | Moyenne |
| B13 | Avis IA | Claude regarde les 5 rendus et écrit une remarque indicative | Revue | 8 · Revue | Petite |
| B14 | Revue et décisions | Garder, régénérer, changer de voie, jeter, avec motif ; validation | Revue | 8 · Revue | Moyenne |

### C · Ranger et publier

| # | Fonctionnalité | Ce qu'elle fait | Où dans l'interface | Étape | Taille |
| --- | --- | --- | --- | --- | --- |
| C1 | Versions et provenance | meta.json par version, version active, comparaison A/B | Fiche asset | 9 · Bibliothèque | Moyenne |
| C2 | Rangement | Vues, collections, étiquettes manuelles et automatiques, tri, sélection multiple, archives | Bibliothèque, Fiche asset, collections du menu | 9 · Bibliothèque | Moyenne |
| C3 | Visionneuse 3D | model-viewer sur le GLB de la version | Revue, Fiche asset | 8 · Revue | Petite |
| C4 | Export | Archive zip : GLB, FBX, .blend, textures, meta.json, licence | Bibliothèque, Fiche asset | 9 · Bibliothèque | Petite |
| C5 | Publication | Dossier du pack (README, licence, aperçus), butler push, version publiée suivie par asset | Bibliothèque (Publier), Fiche asset (packs de l'asset), Réglages | 10 · Publication | Moyenne |

### D · Générateurs et styles

| # | Fonctionnalité | Ce qu'elle fait | Où dans l'interface | Étape | Taille |
| --- | --- | --- | --- | --- | --- |
| D1 | Registre des générateurs | Liste, paramètres, activation, statistiques par générateur | Générateurs (cartes) | 11 · Générateurs et Accueil | Petite |
| D2 | Banc d'essai | Mêmes objets de référence, deux générateurs, mêmes tests, ton choix | Générateurs, Accueil, bandeau de la Bibliothèque | 11 · Générateurs et Accueil | Moyenne |
| D3 | Styles | style.yaml versionné : planche, palette, matériaux, budgets ; création et passage de version | Styles, panneau Style des Références, Brief | 2 · Styles | Moyenne |

## Ordre de développement

Ton choix du 17 octobre : toute l'application d'abord, interface comprise, puis le test à la fin. L'ordre des étapes, ce que chacune livre à l'écran et les dates visées sont dans l'onglet Plan de développement.

## Failles trouvées

Sur les 17 failles, 15 sont des corrections techniques : je les prends en charge et la maquette sera mise à jour avec. Deux seulement dépendent de ce que tu veux ; elles sont décrites en premier.

### Décision 1 · Quand construire les écrans

**Le contexte.** Le cahier des charges prévoit un pilote (phase 1) : fabriquer 5 objets pour vérifier que la méthode marche. Si moins de 3 sortent propres, ou s'il te faut plus de 15 minutes par objet, on revoit l'approche. Ces phases ont été écrites avant la maquette ; les 13 écrans représentent environ un quart du travail total.

**Option A, ma recommandation : le moteur d'abord.** Pendant les phases 0 et 1, tu lances la fabrication par une commande dans le terminal ; les résultats arrivent dans un dossier, et un seul écran existe : la Revue, pour garder ou jeter. Les 12 autres écrans arrivent en phase 2, une fois le pilote réussi. Si le pilote échoue, aucun écran n'a été construit pour rien.

**Option B : les écrans en même temps que le moteur.** Tu vois l'app grandir dès le début, ce qui motive. Mais si le pilote échoue ou change l'approche, une partie des écrans est à refaire.

Ta décision : Option B Révisée le 17 octobre : tout développer, interface comprise, puis tester l'application à la fin.

### Décision 2 · Où publier ta bibliothèque

**Le contexte.** Le cahier des charges prévoit deux façons de partager publiquement : une page itch.io (le site où les créateurs de jeux téléchargent des assets) et un dépôt public type GitHub. La maquette ne montre qu'itch.io, et chaque asset a un interrupteur Privé/Public dont le sens n'est défini nulle part.

**Option A, ma recommandation : itch.io seul en v1.** Un asset est public quand il est dans un pack publié ; l'interrupteur Privé/Public disparaît, remplacé par la liste des packs de l'asset. Le dépôt public viendra plus tard s'il te manque.

**Option B : les deux dès la v1.** « Public » veut dire « dans le dépôt », les packs restent sur itch.io. C'est une publication de plus à construire et deux endroits à tenir à jour.

Ta décision : Option A

### Ce que je corrige sans te demander

| # | Problème | Exemple dans la maquette | Correction | Écran touché |
| --- | --- | --- | --- | --- |
| 1 | Images de référence inutiles pour les objets faits par code | Le scutum, le gladius et le pilum reçoivent 4 images IA (12 crédits chacun), mais leur script Blender ne regarde aucune image | Pour ces objets, l'écran Références montre 4 versions du script avec des réglages différents, rendues par Blender, gratuites | Références, Brief |
| 2 | L'objet mixte n'a qu'une image | Pour la colonne, le fût est fait par code et le chapiteau par Meshy, mais Meshy reçoit l'image de la colonne entière | Le Brief découpe l'objet en deux pièces ; les Références ne montrent des images que pour le chapiteau | Brief, Références, Génération |
| 3 | On refabrique ce qu'on a déjà | La lance a été fabriquée puis archivée : c'était un doublon du pilum | Avant de fabriquer, l'app cherche dans ta bibliothèque ; si l'objet existe, il est réutilisé | Brief, Générateurs |
| 4 | « Régénérer » redonne presque la même chose | Meshy n'accepte pas de consigne comme « sépare les protège-joues » : avec la même image, il refait à peu près le même casque | Régénérer propose de partir d'une autre des 4 images, ou de retoucher l'image avec ta consigne avant de relancer la 3D | Revue, Fiche asset |
| 5 | Les assets CC0 entrent sans vérification | La caisse importée arrive directement en bibliothèque, sans tests ni revue, même si son style jure | Les imports passent par les mêmes étapes que le reste : finition, tests, revue | Revue, Générateurs |
| 6 | Le lot n'affiche qu'une étape | Si tu gardes 4 objets et en relances 2, le lot est à la fois « terminé » et « en génération » | L'app suit chaque objet séparément ; l'en-tête affiche l'étape la moins avancée | En-tête de lot, Lots, Revue |
| 7 | « À créer » reste sans suite | Le râtelier n'a pas de script : l'app le signale, puis plus rien | Un bouton prépare la demande à donner à Claude Code ; quand le script existe, l'app le détecte et reprend l'objet | Brief, Générateurs |
| 8 | Pas d'écran pour publier | Le bouton Publier existe, mais rien ne montre ce qui part, dans quel pack, en quelle version | Une fenêtre en trois temps : choisir le pack, vérifier le contenu, envoyer | Bibliothèque |
| 9 | Pas de bouton pour lancer un banc d'essai | La maquette montre un résultat, jamais le lancement, ni quels objets servent au test | Une liste de 5 objets de test modifiable et un bouton « Lancer un banc » avec le coût | Générateurs |
| 10 | Impossible de créer le premier style | La planche d'un style se remplit avec les images des lots, mais le premier lot a besoin d'une planche | Un assistant : tu décris le style, choisis la palette, ajoutes des images d'inspiration ; il propose 6 premiers objets à valider | Styles |
| 11 | Rien ne dit quoi faire après une nouvelle version de style | « Dupliquer en v1 » existe, mais les assets faits en v0 restent en v0 sans explication | Chaque lot garde sa version ; un bouton « Appliquer la v1 » refait les objets code gratuitement et chiffre les objets IA à refaire | Styles, Lots |
| 12 | Tout attend dans une seule file | Pendant que Meshy calcule sur ses serveurs, Blender et ta carte graphique restent à l'arrêt | Trois files en parallèle : carte graphique, Meshy, Blender | Réglages |
| 13 | Une coupure perd du travail | PC en veille pendant une génération : ce qui tournait dans ComfyUI est perdu | L'app note chaque tâche en cours et la reprend au redémarrage | Génération |
| 14 | Notifications invisibles quand l'onglet est fermé | L'app tourne dans ton navigateur : onglet fermé, tu ne sais pas que la revue est prête | Notification de ton ordinateur, comme à la réception d'un mail, à activer dans Réglages | Réglages |
| 15 | Le stockage se remplit | Chaque essai garde ses fichiers 3D, même rejeté | Seules les versions gardées sont sauvegardées ; les fichiers des rejets sont effacés après 30 jours, leur motif et leur image restent | Fiche asset, Réglages |

## Sources

- [Meshy : Image to 3D, paramètres de la requête](https://docs.meshy.ai/en/api/image-to-3d)
- [Meshy : tarifs de l'API](https://docs.meshy.ai/en/api/pricing)
- [ComfyUI : routes HTTP et WebSocket du serveur](https://docs.comfy.org/development/comfyui-server/comms_routes)
- [itch.io : publier avec butler](https://itch.io/docs/butler/pushing.html)
