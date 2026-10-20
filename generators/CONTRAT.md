# Contrat d'un générateur code

Un générateur code = **un fichier `generators/<nom>.py`** avec un `MANIFESTE` (dictionnaire) et une fonction
`build(params, style, seed=0)`. L'app lit le MANIFESTE sans Blender (routage du Brief, écran Générateurs) ;
seul `build` tourne dans Blender 5.2 LTS (`blender -b --factory-startup -P …`).

## Règles

- **N'importe pas `bpy` au niveau du module.** Fais-le dans `build` (ou dans des fonctions appelées par lui) :
  le module doit s'importer sur une machine sans Blender.
- **Rejouable** : mêmes `params` et même `seed` = même résultat. Pas de hasard hors `seed`.
- **1 unité = 1 mètre, haut = +Z, face avant = −Y.** Pivot au sol et centré, sauf armes et outils (à la poignée),
  selon `style.pivot`.
- **Couleurs, matériaux, budgets et dimensions viennent du style** (`style.materiau(nom)`, `style.budget(cat)`,
  `style.dimensions(type)`), jamais en dur.
- `pieces_declarees` = nombre de pièces séparées que l'objet contient (1 pour un objet d'un seul bloc) ;
  les tests comptent les morceaux et comparent. Si ce nombre dépend des réglages (une amphore sans anses), le
  générateur expose aussi `pieces(params) -> int`, lisible sans Blender : la fabrication l'utilise à la place.

## MANIFESTE

```python
MANIFESTE = {
    "nom": "scutum",                       # = nom du fichier
    "titre": "Scutum (bouclier rectangulaire courbe)",
    "version": 1,                           # entier ≥ 1, à augmenter quand la géométrie change
    "types": ["scutum", "bouclier", "bouclier rectangulaire"],  # minuscules sans accent : les types du brief qu'il sait faire
    "categorie": "prop_moyen",             # petit_prop | prop_moyen | grand_prop | module_archi (budget du style)
    "famille": "armes",                    # armes | outils | props | mobilier | contenants | archi (pivot du style)
    "dimensions_type": "scutum",           # clé de style.dimensions_m pour le test de dimensions
    "symetrique": "X",                     # "X", "Y" ou None
    "pieces_declarees": 1,
    "parametres": {
        "courbure": {"type": "float", "defaut": 0.5, "min": 0.0, "max": 1.0, "aide": "Courbure de la coque"},
        "motif": {"type": "choix", "defaut": "ailes", "choix": ["ailes", "foudre", "aucun"], "aide": "Décor peint"},
        "usure": {"type": "float", "defaut": 0.3, "min": 0.0, "max": 1.0, "aide": "Intensité de l'usure"},
    },
    "variantes": {"A": {"motif": "ailes"}, "B": {"motif": "foudre", "courbure": 0.6}},  # 2 à 4 jeux nommés
}
```

Types de paramètre : `float`, `int`, `bool`, `choix`. Chaque paramètre a un `defaut` (dans `[min, max]`, ou dans
`choix`).

## build

```python
def build(params: dict, style, seed: int = 0):
    import bpy  # ici seulement
    ...
    return objets_bpy  # les objets créés, prêts pour la finition commune (LOD, matériaux, export)
```

La finition, les tests et les rendus sont faits par le pipeline (étape 5 du plan), pas par le générateur.
