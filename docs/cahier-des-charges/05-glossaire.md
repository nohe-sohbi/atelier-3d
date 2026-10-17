# Glossaire

> Copie du document « Cahier des charges – Bibliothèque d'assets 3D », exportée le 17 oct. 2026. Ne la modifie pas ici : elle est régénérée depuis le document. Voir [README.md](README.md).

Les termes de la maquette et du cahier des charges, en une phrase chacun, avec l'endroit de l'app où tu les croises.

| Terme | Ce que c'est | Où tu le croises |
| --- | --- | --- |
| Adaptateur | Petit module Python qui traduit les ordres de l'app pour un générateur précis ; changer de générateur revient à changer d'adaptateur | Générateurs |
| API | Porte qu'un service ouvre aux programmes : l'app envoie une requête, le service répond | Partout |
| Bake (cuisson) | Copier les détails d'un modèle très fin dans des textures posées sur un modèle plus léger | Génération |
| Banc d'essai | Les mêmes objets passés dans deux générateurs, comparés sur les mêmes tests | Générateurs |
| .blend | Fichier de travail de Blender : la scène complète, modifiable | Fiche asset |
| Blender headless | Blender lancé sans fenêtre et piloté par un script (`blender -b -P script.py`) | Génération, tests, rendus |
| butler | Outil en ligne de commande d'itch.io qui envoie un dossier sur une page | Publier |
| CC0 | Licence domaine public : réutilisable sans condition ni crédit | Voie import, Brief |
| CC BY 4.0 | Réutilisable à condition de citer l'auteur ; licence des sorties de l'offre gratuite de Meshy | Licences |
| Claude Code | Claude qui écrit et lance du code dans ton terminal ; ici, il écrit les générateurs et le pipeline | Brief (« À créer »), Ajouter un générateur |
| Collision | Forme simplifiée et invisible que le moteur utilise pour les chocs | Spécifications d'un asset |
| ComfyUI | Logiciel local qui enchaîne des modèles d'IA en workflows ; l'app lui envoie des tâches par son API | Générateurs |
| Crédits | Monnaie de Meshy : 30 par objet 3D texturé, 3 par image | Menu, Brief, Accueil |
| Densité de texels | Pixels de texture par mètre de surface ; identique partout, elle donne la même netteté à des objets voisins | Tests, Styles |
| FBX | Format 3D d'Autodesk, encore attendu par Unity et beaucoup de boutiques | Fichiers |
| Finition | Étape automatique après la génération : échelle, nettoyage, réduction, pivot, export | Génération |
| Générateur procédural | Script Blender qui construit un type d'objet à partir de paramètres (largeur, nombre de lattes…) ; c'est la voie code | Générateurs, Brief |
| glTF, GLB | Format 3D ouvert et normalisé (ISO/IEC 12113) ; le GLB est sa version en un seul fichier. Format pivot de la bibliothèque | Fichiers, Tourner en 3D |
| glTF-Validator | Outil de Khronos qui vérifie qu'un fichier glTF respecte la norme et rend un rapport JSON | Tests |
| LOD | Versions de moins en moins détaillées d'un même objet, affichées de loin | Spécifications d'un asset |
| Maillage (mesh) | La surface de l'objet : des sommets reliés en triangles | Partout |
| Manifold | Surface fermée, sans trou ni arête partagée par plus de deux faces | Tests |
| Meshy | Service en ligne qui transforme une image en objet 3D texturé | Générateurs, crédits |
| model-viewer | Composant web qui affiche un GLB en 3D dans une page | Tourner en 3D, Comparer |
| Normal map | Texture qui simule des reliefs fins sans ajouter de triangles | Textures |
| ORM | Une texture qui en range trois : occlusion, rugosité, métal | Textures |
| PBR | Matériaux décrits par des propriétés physiques (couleur, rugosité, métal) : même rendu dans tous les moteurs | Spécifications, Styles |
| Pivot | Point autour duquel l'objet tourne et se pose ; ici, au sol et au centre | Tests |
| Pixal3D | Modèle open source qui transforme une image en 3D, lancé en local dans ComfyUI | Générateurs |
| Polling, SSE | Deux façons de suivre une tâche longue : redemander régulièrement (polling) ou recevoir un flux d'événements (SSE) | Génération |
| Remesh, retopologie | Reconstruire la surface avec moins de triangles, mieux rangés | Génération |
| Routage | Règles qui décident quel générateur traite quelle catégorie d'objet | Générateurs, Brief |
| SQLite | Base de données tenue dans un seul fichier, sans serveur | Toute l'app |
| Topologie | Façon dont les triangles sont organisés ; propre veut dire régulière, sans pointes ni trous | Revue |
| Trellis.2 | Modèle image vers 3D de Microsoft, autre option locale dans ComfyUI | Générateurs |
| Tris | Triangles : l'unité de poids d'un modèle 3D ; le budget fixe un maximum par catégorie | Revue, Styles |
| UV, dépliage | La découpe à plat du modèle, qui dit où chaque pixel de texture se colle | Tests |
| Voie | Chemin de fabrication d'un objet : code, IA, mixte (les deux) ou import CC0 | Brief, partout |
