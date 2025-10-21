.PHONY: dev run test fmt lint type prep

VENV ?= .venv
PYTHON ?= python3

DEV_REQUIREMENTS = -r requirements.txt

help:
@grep -E '^[a-zA-Z_-]+:.*?##' Makefile | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

dev: ## instala deps y prepara entorno
$(PYTHON) -m venv $(VENV)
. $(VENV)/bin/activate && pip install --upgrade pip && pip install $(DEV_REQUIREMENTS)
. $(VENV)/bin/activate && pre-commit install

run: ## ejecuta la API en modo desarrollo
uvicorn horizonte.api.main:app --reload

test: ## ejecuta la suite de pruebas
pytest -q

fmt: ## aplica formateo automático
black .

lint: ## ejecuta ruff
ruff check .

type: ## ejecuta mypy
mypy .

prep: ## instala pre-commit en el entorno actual
pre-commit install
