# Cahier des charges

Ce que l'app doit faire, pourquoi, et dans quel ordre on la construit. Ces fichiers sont la copie, en Markdown, du document « Cahier des charges – Bibliothèque d'assets 3D » tenu avec Nohé. Ils sont régénérés depuis ce document à chaque changement : on ne les modifie pas ici.

## Les fichiers

| Fichier | Ce qu'il contient | Quand le lire |
|---|---|---|
| [01-cahier-des-charges.md](01-cahier-des-charges.md) | Vision, périmètre v1, principes, pipeline, style system, Definition of Done d'un asset, contrôles qualité, revue, licences, risques, décisions | Avant toute étape, pour les règles de fond |
| [02-audit-fonctionnel.md](02-audit-fonctionnel.md) | Écran par écran : ce que fait chaque bouton, avec quel outil (API, Blender, SQLite…), et l'architecture de l'app | Quand tu construis un écran |
| [03-fonctionnalites.md](03-fonctionnalites.md) | Les 28 fonctionnalités (codes A1 à D3), l'étape où chacune est construite, et les 15 corrections apportées à la maquette | Pour savoir ce qu'une étape doit livrer |
| [04-plan-de-developpement.md](04-plan-de-developpement.md) | Les 13 étapes, leurs dates, et le détail de l'étape en cours | Au début de chaque étape |
| [05-glossaire.md](05-glossaire.md) | Les termes du projet en une phrase | En cas de doute sur un mot |

La maquette des écrans est à côté, dans [../maquette/](../maquette/README.md).

## Quel fichier fait foi

Les documents ont été écrits dans cet ordre : cahier des charges, audit, fonctionnalités, plan. Quand deux d'entre eux se contredisent, le plus récent l'emporte :

1. **Plan de développement** : l'ordre des étapes et ce que chacune livre.
2. **Fonctionnalités** : ses 15 corrections et ses 2 décisions priment sur l'audit et la maquette.
3. **Cahier des charges** : les règles de fond, la Definition of Done, les seuils.
4. **Audit fonctionnel** : le détail écran par écran, sauf là où les fichiers ci-dessus le corrigent.

La maquette vient après tous ces fichiers. Si tu trouves une contradiction, signale-la à Nohé au lieu de trancher seul.

## À savoir en lisant

- **Voie A et voie B** dans le cahier des charges = **voie IA** et **voie code** dans la maquette et le reste des documents. Il existe aussi la voie mixte et la voie import CC0.
- **La roadmap en 4 phases** du cahier des charges a été remplacée le 17 octobre : toute l'application d'abord, puis le test avec de vrais objets à la fin. Les critères du go/no-go s'appliquent à ce test final.
- **Les décisions encore ouvertes** sont listées à la fin de 01-cahier-des-charges.md : licence de publication (à trancher avant la première publication) et moteur de jeu cible (test d'import en v2). Ne les tranche pas dans le code.
