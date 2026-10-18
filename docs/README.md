# Documentation d'Atelier 3D

Point d'entrée pour comprendre le projet, que tu sois Claude Code ou une nouvelle session Claude.

## Où est quoi

| Quoi | Source (là où on le modifie) | Copie dans ce dépôt |
|---|---|---|
| Cahier des charges : vision, fonctionnalités, plan, glossaire | [Document sur claude.ai](https://claude.ai/code/artifact/07ca744c-f2f7-4b87-82e7-d15446354a0f) | [cahier-des-charges/](cahier-des-charges/README.md) |
| Maquette cliquable : 11 écrans, 5 fenêtres, 2 composants | [Canvas sur claude.ai](https://claude.ai/artifact/6VaneF7fyVErVuSLVnWthu) | [maquette/](maquette/README.md) |
| Code de l'app | ce dépôt | — |

Les deux liens claude.ai sont privés : seul Nohé peut les ouvrir, avec ses sessions Claude.

## Où en est le projet

Le tableau des 13 étapes de [04-plan-de-developpement.md](cahier-des-charges/04-plan-de-developpement.md) dit quelle étape est faite et laquelle vient ensuite. Les décisions prises et celles qui restent ouvertes sont à la fin de [01-cahier-des-charges.md](cahier-des-charges/01-cahier-des-charges.md).

## Qui fait quoi

- **Nohé** décide, colle dans Claude Code les textes préparés pour chaque étape, et vérifie à l'écran ce que l'étape doit montrer.
- **Claude Code**, sur la machine de Nohé, écrit le code dans ce dépôt, puis commit et push à la fin de chaque étape.
- **Claude, sur claude.ai**, tient le cahier des charges et la maquette, détaille chaque étape au moment où Nohé l'attaque, et relit sur GitHub le code poussé avant de donner l'étape suivante.

## Pour une nouvelle session Claude sur claude.ai

- Ce projet est indépendant des autres projets de Nohé : ne t'y réfère pas et ne les mélange pas avec celui-ci.
- Rome antique n'est qu'un thème d'essai pour tester l'app, pas le sujet de la bibliothèque.
- Dis toujours où on va et qui fait quoi ; donne des étapes finement découpées, avec ce qu'il faut voir à l'écran à la fin de chacune.
- Avant de répondre sur l'état du projet, lis le plan ci-dessus et le dernier commit de ce dépôt.

## Mettre à jour docs/

Claude Code ne modifie jamais docs/. C'est Claude, sur claude.ai, qui le régénère après chaque changement de la source :

- **Cahier des charges :** modifier d'abord le document. Ensuite, exporter chaque onglet en Markdown avec l'outil d'export de Claude Docs. Pour récupérer le fichier, créer un blob depuis l'onglet, puis lire son asset sur l'artifact du document. Retranscrire les schémas (widgets) en Mermaid, écrire les dates en français, remplacer les mentions d'onglets par des liens relatifs, et garder la note d'en-tête de chaque fichier. Le README de cahier-des-charges/ s'écrit à la main.
- **Maquette :** modifier le canvas et le republier, puis recopier ici les fichiers `.dc.html` et `canvas.json`.
- Faire ensuite un commit et un push sur origin main.
