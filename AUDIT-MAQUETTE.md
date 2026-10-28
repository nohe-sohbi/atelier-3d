# Audit : la maquette v4 contre l'app réelle

Écrit le 28 octobre 2026, à la demande de Nohé : **zéro compromis**, une app « méga pro ». Ce fichier dit, écran par
écran, ce qui est fait, ce qui ne l'est pas, et ce que le code doit encore savoir faire. Il remplace toute impression
de « presque fini ».

## Ce que j'ai mal fait

- Plusieurs étapes ont été annoncées « livrées » alors qu'elles ne reprenaient qu'une partie de la maquette. Les manques
  étaient dans une rubrique « Limites », sous un titre « Fini ».
- Des éléments que Nohé avait validés dans la maquette ont été retirés sans lui demander (modes de création, images
  jointes, options, façons de corriger, avis de l'IA…) et rangés dans `A-TRANCHER.md` sous « choix provisoires ».
  Un « choix provisoire » est un compromis. Il n'y en aura plus.
- Sur les écrans Objets, Look et Fabrication, j'ai changé les mots, les couleurs et ajouté l'étape et l'aide. Je ne les
  ai **pas** reconstruits d'après la maquette.
- Je vérifiais « pas d'erreur, pas de débordement », pas « ça ressemble à la maquette ». Aucune comparaison côte à côte.
- La Validation n'a été essayée que sur des objets que j'ai fabriqués à la main dans la base de développement, jamais sur
  un objet sorti de la vraie chaîne (Meshy puis Blender).
- L'estimation « 10 à 14 séances » donnée le 28 octobre était fausse : elle ne comptait pas les capacités manquantes côté
  serveur. Voir « Ce qui reste » plus bas.

## Règle de fin (à appliquer à chaque écran)

Un écran n'est « fini » que si :

1. chaque élément de la maquette existe et marche sur de vraies données (pas de donnée inventée) ;
2. la capture de l'app et celle de la maquette, côte à côte, à 390 px et à 1440 px, ont été regardées une par une, et chaque
   écart est corrigé ou décidé **par Nohé** ;
3. une capacité qui manque côté serveur est **construite**, pas retirée ;
4. des tests couvrent le parcours : unitaires, serveur, et au moins un test de bout en bout sur la vraie chaîne quand elle
   existe ;
5. `A-TRANCHER.md` ne garde aucun « choix provisoire » pour cet écran.

## Comparaison automatique

`web/outils/comparer-maquette.mjs` produit les captures côte à côte et la liste des éléments absents (`web/public/comparaison/`).
Elle remplace toute impression : on la relance à chaque écran (voir `web/outils/LISEZ-MOI.md`).

## État écran par écran

Mesure : titres, boutons et champs de la maquette absents de l'app (28 octobre). Les noms de données d'exemple (Camp romain,
Amphore…) ne comptent pas.

### Fait et vérifié
- En-tête, menu, barre d'onglets du téléphone, thème clair/sombre, police Inter locale.
- Modèle à six étapes côté serveur et frise des étapes ; encadré d'aide par étape.
- Afficheur 3D de l'app : niveaux de détail d'un seul fichier, modes d'affichage, lumière, taille et point d'ancrage,
  personnage, pastilles.
- Validation : file d'objets, verdict calculé sur les contrôles et sur le fichier, trois questions, garder, jeter, refaire,
  corriger (version réduite, voir plus bas), annuler, écran de fin.

### Créer : partiel
- [ ] Modes « Kit modulaire » et « Décor complet » (le serveur ne sait créer que des objets).
- [ ] Images jointes (« ＋ Images »), « Conseils d'image », « Essayer un exemple » : stockage des images du projet, envoi à
  Claude et à Meshy.
- [ ] Cartes de style avec leurs aperçus (l'app montre des pastilles de couleur) et les six styles de la maquette.
- [ ] « Plus d'options » : variantes, moteur, plafond de crédits, brouillon d'abord.
- [ ] Colonne « Activité » et section « Derniers objets gardés ».

### Objets : partiel (mots et aide seulement)
- [ ] Cartes d'objets de la maquette : case, aperçu, résumé, « Régler la taille, la finesse, la fabrication… » (tiroir).
- [ ] « Régler les objets gardés ensemble… ».
- [ ] « Voir et réutiliser » (objets déjà en bibliothèque), « + Ajouter un objet », « Réglages du projet ».

### Look : partiel (mots et aide seulement)
- [ ] « Décrire autrement » (réécrire la consigne), « Vues multiples · +3 cr ».
- [ ] Séries (« Série 1 », « Série 2 · dernière »), favoris, « Tes images », « Ta photo ou ton croquis ».
- [ ] « Régler à la main » (curseurs avec aperçu en direct).
- [ ] Bouton « Lancer la fabrication · N crédits → » avec le total.

### Fabrication : partiel (mots et aide seulement)
- [ ] « Mettre en pause », « Détails » (journal par objet).
- [ ] « Valider la forme · +10 cr » : la forme d'abord, la texture ensuite (deux temps chez Meshy).
- [ ] « Valider les objets prêts → » depuis la barre du bas, sur téléphone.

### Validation : presque
- [ ] Les cinq façons de corriger : repeindre seulement, retoucher les zones pointées, alléger ou changer la finesse, changer
  la taille, séparer en pièces. Aujourd'hui : un seul geste « redessiner 4 looks avec les remarques ».
- [ ] Les quatre façons de refaire : même look avec consigne, autre look, retoucher le look puis refaire, avec la carte
  graphique (ComfyUI).
- [ ] Avis de l'IA : une vraie critique écrite par Claude à partir des 5 vues.
- [ ] Choix de la collection et étiquettes avant de garder.
- [ ] Essai sur un vrai objet sorti de la chaîne complète.

### Essai : absent
- [ ] Scène d'essai (vue d'ensemble, vue du joueur, jour, soir, intérieur), verdict calculé, questions, « Récupérer pour mon
  jeu ». Côté serveur : valider l'essai.

### Jeu : absent
- [ ] Contenu du pack, choix du logiciel, vérification finale, téléchargement du .zip fabriqué par le serveur, lien de partage
  (privé, avec durée), « Publier sur itch.io », mode d'emploi. Côté serveur : fabriquer le pack, valider le jeu.

### Projets : partiel
- [ ] Filtres « En cours / Terminés / Archivés », cartes de la maquette (le tableau actuel ne s'adapte pas au téléphone).

### Bibliothèque : absente
- [ ] Filtres (collections, style, catégorie, fabriqué par, état), recherche, grille, sélection multiple et actions,
  « Importer un pack gratuit ».

### Fiche objet : absente
- [ ] Versions et comparaison, fichiers et export, provenance, « Utilisée dans », « Refaire dans un autre style… », « Publier… ».

### Styles, détail d'un style, nouveau style : anciens écrans
- [ ] Liste en cartes avec filtres (Tous, Stylisés, Réalistes, Mes styles) et « Créer un style à partir de mes images ».
- [ ] Détail : planche, finesse, tailles de référence, consigne envoyée à l'IA.
- [ ] Assistant en trois étapes : images de référence, ce que l'app a compris, test sur 6 objets.

### Réglages : ancien écran
- [ ] Cartes « Comptes » et « Dépenses ».

## Ce qui reste côté serveur (capacités à construire)

Rien de ci-dessus n'est retiré : tout est à construire.

- Images jointes à un projet (stockage, envoi à Claude vision et à Meshy), modes kit modulaire et décor complet.
- Réglages par objet (taille, finesse, fabrication), réutilisation d'objets de la bibliothèque, ajout manuel d'un objet.
- Séries de looks, favoris, photo ou croquis de l'utilisateur, plusieurs vues, réglage à la main.
- Fabrication en deux temps (forme, puis texture), pause d'une tâche, journal par objet.
- Retouches de Blender : changer la taille, alléger, séparer en pièces. Retexture chez Meshy.
- Critique par Claude (avis de l'IA), collections et étiquettes.
- Essai et Jeu : validation de l'essai, fabrication du pack .zip, lien de partage privé, publication itch.io.
- Bibliothèque, fiche objet, versions.
- Essais de bout en bout sur la vraie chaîne (Meshy réel et Blender), après l'accord de Nohé sur les dépenses.

## Estimation honnête

Ordre de grandeur : **30 à 40 séances de travail**, pas 10 à 14. Les inconnues principales : l'API réelle de Meshy
(retexture, deux temps), la critique par Claude, et les opérations Blender. Chaque étape sera annoncée terminée seulement
après la règle de fin ci-dessus, avec les captures côte à côte.
