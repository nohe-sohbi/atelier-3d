# Maquette de l'interface

Référence visuelle et fonctionnelle de l'app : 11 écrans, 5 fenêtres et 2 composants partagés.
La version cliquable et à jour est le canvas publié sur claude.ai ; ce dossier en est la copie pour le dépôt.

## Règles pour Claude Code

1. **La maquette dit quoi afficher et où** : écrans, textes, ordre des sections, parcours entre écrans. Tu la reproduis en React + TypeScript avec de vrais composants ; tu ne recopies pas le HTML tel quel.
2. **Les données de la maquette sont fausses.** Tout ce que renvoie `renderVals()` (noms d'objets, crédits, dates, compteurs, pourcentages) sert seulement à montrer l'écran rempli. L'app n'affiche jamais une donnée inventée : elle lit l'API, sinon elle montre un état vide ou une erreur claire.
3. **Le thème Rome antique est un exemple.** Aucun nom d'objet, de style ou de lot n'est écrit en dur dans l'app.
4. **Style.** Polices IBM Plex Sans et IBM Plex Mono. Couleurs à reprendre en variables : accent `#2B50C8`, texte `#1D1C1A`, texte secondaire `#5E5B55`, bordures `#E3E1DC` et `#CFCCC5`, fond `#F5F4F1`, succès `#1F6B45` sur `#E3F2EA`, alerte `#8A4B00` sur `#FBF7EF`.
5. **Accessibilité.** Vrais `<button>`, `<a>` et `<label>`, cibles cliquables de 44 px minimum, focus visible ; une fenêtre se ferme avec Échap et rend le focus au bouton qui l'a ouverte.
6. **En cas de doute** entre la maquette et le cahier des charges, le cahier des charges gagne ; signale l'écart au lieu de choisir seul.

## Lire un fichier `.dc.html`

- Le HTML de l'écran est dans `<x-dc>`. Chaque trou `{{ chemin.vers.valeur }}` est rempli par l'objet que renvoie `renderVals()`, dans la balise `<script type="text/x-dc">` en bas du fichier.
- `<sc-for list="{{ items }}" as="item">` répète un bloc ; `<sc-if value="{{ x }}">` l'affiche ou non. Les attributs `hint-*` ne servent qu'à l'éditeur : ignore-les.
- `<dc-import name="Sidebar">` insère un composant (`Sidebar.dc.html`, `LotHeader.dc.html`).
- `class Component extends DCLogic` : `this.state` et `this.setState` portent l'état local de la maquette (onglet ouvert, case cochée, étape d'une fenêtre). C'est le comportement attendu de l'interface, pas la logique métier.
- `<a href="X.dc.html">` est un lien vers un autre écran : c'est un parcours à reproduire.
- `canvas.json` place les écrans sur le canvas et contient les notes reprises plus bas.
- Ces fichiers ne tournent pas seuls : le moteur qui les affiche vit sur claude.ai. Ici, ils se lisent comme une spécification.

## Écrans et routes proposées

| Fichier | Écran | Route ou usage |
|---|---|---|
| `Main.dc.html` | Accueil | / |
| `Lots.dc.html` | Lots | /lots |
| `Library.dc.html` | Bibliothèque | /bibliotheque |
| `Asset.dc.html` | Fiche asset | /assets/:id |
| `Generators.dc.html` | Générateurs | /generateurs |
| `Styles.dc.html` | Styles | /styles |
| `Settings.dc.html` | Réglages | /reglages |
| `Brief.dc.html` | Lot · 1 Brief | /lots/:id/brief |
| `Refs.dc.html` | Lot · 2 Références | /lots/:id/references |
| `Generation.dc.html` | Lot · 3 Génération | /lots/:id/generation |
| `Review.dc.html` | Lot · 4 Revue | /lots/:id/revue |
| `Publish.dc.html` | Fenêtre Publier | fenêtre, depuis Bibliothèque et Fiche asset |
| `BenchLaunch.dc.html` | Fenêtre Lancer un banc | fenêtre, depuis Générateurs |
| `NewStyle.dc.html` | Fenêtre Nouveau style | fenêtre, depuis Styles |
| `Regenerate.dc.html` | Fenêtre Régénérer | fenêtre, depuis Revue et Fiche asset |
| `ClaudeRequest.dc.html` | Fenêtre Demande Claude Code | fenêtre, depuis Brief et Générateurs |
| `Sidebar.dc.html` | Composant Menu | à gauche de tous les écrans |
| `LotHeader.dc.html` | Composant En-tête de lot | en haut des 4 écrans de lot |

## Ce que dit chaque écran (notes du canvas)

- **Accueil** : Accueil : ce qui t'attend. Revue prête, références à choisir, résultat d'un banc d'essai : un clic t'amène au bon écran. La cloche s'ouvre sur les notifications.
- **Lots** : Lots : tous tes lots et leur étape. Un lot s'ouvre directement sur l'étape où il en est.
- **Bibliothèque** : Bibliothèque : ranger et retrouver. Vues, collections et étiquettes ; sélection multiple pour étiqueter, publier ou archiver d'un coup. Les étiquettes techniques viennent seules des métadonnées.
- **Fiche asset** : Fiche asset : l'historique d'un asset. Toutes ses générations, rejets compris avec leur motif. Compare deux versions, choisis l'active : les fichiers suivent. Dessinée pour le casque : dans la maquette, chaque carte ouvre cette fiche.
- **Générateurs** : Générateurs : ajouter, comparer, adopter. Le banc d'essai compare deux générateurs sur tes objets de référence ; les règles de routage décident qui fabrique quoi.
- **Styles** : Styles : tes moodboards exécutables, versionnés. Un lot en applique un ; un matériau partagé modifié se répercute sur les assets de la voie code, les assets IA se régénèrent.
- **Réglages** : Réglages : les clés de Meshy, de l'API Claude et d'itch.io, les outils de ta machine, les plafonds et la file de tâches. Rien ne part ailleurs que vers ces services.
- **Lot · 1 Brief** : Toi : un thème, un style, une phrase. Claude propose et classe la liste d'objets, les règles de routage choisissent la voie de chacun ; tu coches. Cible : 2 min par lot.
- **Lot · 2 Références** : Toi : choisir 1 image sur 4 par objet. C'est ici que se joue le style : l'image choisie guide la voie IA et sert de cible à la voie code. Cible : 30 s par objet.
- **Lot · 3 Génération** : Toi : rien. Code ou IA selon l'objet, finition, tests et relances tournent seuls. Une notification arrive quand la revue est prête.
- **Lot · 4 Revue** : Toi : garder, régénérer, changer de voie ou jeter. La technique est déjà vérifiée ; tu ne juges que le beau et le cohérent. Cible : 1 min par objet.
- **Fenêtre Publier** : Depuis Bibliothèque (sélection) ou Fiche asset. Un asset devient public quand il entre dans un pack publié. La licence se choisit ici, avant la première publication.
- **Fenêtre Lancer un banc** : Depuis Générateurs. Mêmes objets de référence pour chaque banc ; côté Meshy, reprendre le dernier essai ne coûte rien.
- **Fenêtre Nouveau style** : Depuis Styles. Tu définis, l'IA dessine une planche de 6 objets génériques, tu gardes ce qui te ressemble.
- **Fenêtre Régénérer** : Depuis Revue ou Fiche asset. La consigne part de l'avis de l'IA ; le coût s'affiche avant de relancer.
- **Fenêtre Demande Claude Code** : Depuis Brief ou Générateurs, quand aucun générateur code ne connaît le type. L'app écrit la demande, Claude Code écrit le script.
