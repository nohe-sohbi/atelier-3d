# Maquette de l'interface (v4, validée par Nohé le 28 octobre 2026)

Référence visuelle et fonctionnelle de l'app. Elle remplace la maquette des 11 écrans d'origine, qui reste
dans l'historique git. C'est une page unique, cliquable, responsive (téléphone, tablette, ordinateur).

- `index.html` : tous les écrans, un par ancre (`#accueil`, `#objets`, `#look`, `#fabrication`,
  `#validation`, `#essai`, `#jeu`, `#projets`, `#bibliotheque`, `#fiche`, `#styles`, `#style`,
  `#nouveau-style`, `#reglages`).
- `visionneuse.js` : l'afficheur 3D (tourner, modes d'affichage, lumière, repères, pointage, scène d'essai).
- `img/` et `modeles/` : images et fichiers 3D réels utilisés par la maquette.

Pour la voir : lancer `python dev.py`, puis ouvrir `/proposition/` (le dossier `web/public/proposition` est un
lien vers ce dossier). À retirer de `web/public` quand tous les vrais écrans sont construits, pour qu'elle ne
parte pas dans la version publiée.

## Le parcours

Six étapes par projet : **Objets, Look, Fabrication, Validation, Essai, Jeu.** À chaque étape, un encadré dit
en une phrase ce que l'utilisateur fait ici.

Vocabulaire de l'interface, qui remplace celui de l'ancienne maquette :
- « Lot » devient « Projet » ;
- « Brief » devient l'écran « Créer », puis l'étape « Objets » ;
- « Références » devient « Look » ;
- « Génération » devient « Fabrication » ;
- « Revue » devient « Validation » ;
- « Essai » et « Jeu » sont nouveaux.

## Règles pour Claude Code

1. **La maquette dit quoi afficher et où** : écrans, textes, ordre des sections, parcours entre écrans. Tu la
   reproduis en React + TypeScript avec de vrais composants ; tu ne recopies pas le HTML tel quel.
2. **Les données sont des exemples.** Noms d'objets, crédits, dates, compteurs : tout cela sert à montrer
   l'écran rempli. L'app n'affiche jamais une donnée inventée : elle lit l'API, sinon elle montre un état vide
   ou une erreur claire. Les fichiers 3D et les mesures affichées (taille, triangles, point d'ancrage) sont
   réels : l'app les calcule sur le vrai fichier.
3. **Le thème Rome antique est un exemple.** Aucun nom d'objet, de style ou de projet n'est écrit en dur dans
   l'app. Jamais de prénom inventé dans un écran ou une doc.
4. **L'app juge et guide à la place de l'utilisateur.** Il ne connaît pas la 3D. Chaque décision commence par
   un verdict en mots simples et par quelques questions Oui/Non qui disent quoi regarder. Les outils de pro
   (lumière, repères, fil de fer) existent mais restent rangés à part. Pas de jargon, jamais de format à
   choisir : l'app choisit (.glb pour tous).
5. **C'est une app web, peut-être publique un jour.** Jamais de chemin local ni d'écriture sur le disque de
   l'utilisateur : l'export est un téléchargement (.zip) ou un lien de partage. Rien de propre à Nohé dans les
   textes ou les défauts (moteur, carte graphique, chemins).
6. **Style.** Police Inter, servie en local. Couleurs à reprendre en variables depuis les blocs `:root`
   (thème clair, par défaut) et `[data-theme="sombre"]` de `index.html` ; `tokens.css` les porte, un test
   vérifie qu'elles existent dans la maquette.
7. **Responsive.** Chaque écran marche sur téléphone (390 px, au doigt) ET sur ordinateur. Sous 1000 px, la
   navigation passe en barre d'onglets en bas, et la barre d'actions de l'écran reste visible. Vérifier les
   deux tailles à chaque écran, sans défilement horizontal.
8. **Accessibilité.** Vrais `<button>`, `<a>` et `<label>`, cibles cliquables de 44 px minimum, focus visible ;
   une fenêtre se ferme avec Échap et rend le focus au bouton qui l'a ouverte.
9. **En cas de doute.** Pour l'interface (parcours, noms d'écrans, textes), cette maquette fait foi, par décision
   de Nohé (voir `A-TRANCHER.md`, « Décision du 28 octobre »). Pour les données, le traitement des objets et les
   règles d'asset, le cahier des charges (`docs/cahier-des-charges/`) fait foi. Signale chaque écart dans
   `A-TRANCHER.md`.
