# Outils de conception

## Comparer la maquette et l'app

    node web/outils/comparer-maquette.mjs                    # tous les écrans (une dizaine de minutes, peu de charge)
    node web/outils/comparer-maquette.mjs --ecran validation # un seul écran
    node web/outils/comparer-maquette.mjs --sans-captures    # seulement la différence de structure

Il faut l'app lancée (`python dev.py --reseau`) et un projet de démonstration (`python -m tests.outils.projet_demo`).
Sortie, dans `web/public/comparaison/` (ignoré par git, retiré de la version publiée) :

- `index.html` : maquette et app côte à côte à 390, 768 et 1440 px, en clair et en sombre. Ouvrable depuis le téléphone :
  `http://<adresse de l'app>/comparaison/index.html`.
- `rapport.md` et `rapport.json` : les titres, boutons et champs de la maquette absents de l'app (cases à cocher), et ce que
  l'app a en plus. Les noms de données d'exemple et les nombres sont ignorés : on compare la structure, pas les valeurs.

Les polices et three.js, que la maquette charge depuis internet, sont servis depuis `node_modules` (l'outil marche hors ligne).
Les onglets et les `<details>` sont parcourus ; les menus et tiroirs ne le sont pas encore (à ajouter écran par écran).

**Un écran n'est « fini » que si cette comparaison a été regardée une par une** (voir la règle de fin dans `AUDIT-MAQUETTE.md`).

## Jeu de démonstration

    python -m tests.outils.projet_demo                       # dans la base de développement
    python -m tests.outils.projet_demo --db X --lots Y       # dans une base précise (tests e2e)

Un projet avec une amphore nette, une caisse « à regarder » et une lanterne en fabrication, avec de vrais fichiers 3D à niveaux
de détail. Les tests de bout en bout l'appellent par `web/e2e/semer.ts`.
