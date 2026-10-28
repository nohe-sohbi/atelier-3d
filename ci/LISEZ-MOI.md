# Intégration continue

`github-actions.yml` est la configuration prête à l'emploi : serveur (ruff, pytest), interface (types, lint, tests, build) et
bout en bout sans Blender. Elle doit vivre dans `.github/workflows/ci.yml` pour que GitHub la lance.

Elle n'y est pas encore : le jeton GitHub utilisé par Claude Code n'a pas l'autorisation « workflow », donc GitHub refuse le
dépôt qui la contient. Deux façons de l'activer :

- donner l'autorisation `workflow` au jeton, puis `mkdir -p .github/workflows && git mv ci/github-actions.yml .github/workflows/ci.yml` ;
- ou copier le fichier soi-même depuis l'interface GitHub (Add file > Create new file > `.github/workflows/ci.yml`).

Les tests marqués `blender` sont sautés en CI : ils chargent la machine et se lancent à la main (`pytest -m blender`) à la fin
de chaque jalon.
