# Atelier 3D : `make dev` lance tout ; `make test` et `make lint` vérifient.
PY ?= .venv/bin/python
PYTEST ?= .venv/bin/pytest
RUFF ?= .venv/bin/ruff

.PHONY: dev api worker web test test-api lint install

dev:            ## API + worker + interface Vite, puis ouvre http://127.0.0.1:5173
	$(PY) dev.py

api:            ## API seule (http://127.0.0.1:8000)
	$(PY) -m api --reload

worker:         ## worker seul
	$(PY) -m worker

web:            ## interface Vite seule
	npm --prefix web run dev

test:           ## tests Python et interface
	$(PYTEST) -q
	npm --prefix web test --if-present

test-api:       ## tests de l'API et du worker seulement
	$(PYTEST) tests/api tests/worker -q

lint:           ## ruff sur api, worker, tests
	$(RUFF) check api worker tests

install:        ## dépendances Python (venv) et Node
	$(PY) -m pip install -e ".[dev]"
	npm --prefix web install
