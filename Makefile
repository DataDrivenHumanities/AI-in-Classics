# -------------------------------
# Project Makefile (dev-friendly)
# Supports: Poetry, plain venv/pip, Docker, Ollama models
# -------------------------------

# ===== Config =====
PYTHON        ?= python3
PIP           ?= pip3
PORT          ?= 8501
APP_ENTRY     ?= src/app/app.py
STREAMLIT_APP ?= src/app/app.py

# Ollama
OLLAMA_HOST   ?= http://localhost:11434
OLLAMA_GEN    := $(OLLAMA_HOST)/api/generate
OLLAMA_TAGS   := $(OLLAMA_HOST)/api/tags
LATIN_TAG     ?= latin_model:1.0.0
GREEK_TAG     ?= greek_model:1.0.0
BASE_MODEL    ?= llama3.1:8b

# Detect Poetry
POETRY_BIN    := $(shell command -v poetry 2>/dev/null)

# Runner helpers: prefer Poetry if present; else use .venv
RUNPY         := $(if $(POETRY_BIN),poetry run $(PYTHON),.venv/bin/$(PYTHON))
RUN           := $(if $(POETRY_BIN),poetry run, .venv/bin)
PIP_RUN       := $(if $(POETRY_BIN),poetry run $(PIP),.venv/bin/$(PIP))

# ===== Phony =====
.PHONY: help setup setup-poetry setup-venv setup-docker env \
        run web \
        check fix test \
        docker-build docker-run docker-dev docker-bash docker-clean \
        ollama-serve ollama-pull ollama-list build-latin build-greek \
        smoke-latin smoke-greek ensure-ollama ensure-models health

# ===== Help (default) =====
help:
	@echo "Usage: make <target>"
	@echo
	@echo "Core:"
	@echo "  setup            Auto-setup (Poetry if available, else venv+pip)"
	@echo "  run              Run app (python $(APP_ENTRY))"
	@echo "  web              Run Streamlit (streamlit run $(STREAMLIT_APP))"
	@echo "  test             Run tests (pytest)"
	@echo "  check            Format check (black)"
	@echo "  fix              Auto-format (black)"
	@echo
	@echo "Docker:"
	@echo "  docker-build     Build image classics-app"
	@echo "  docker-run       Run container (simple)"
	@echo "  docker-dev       Run with live reload (mount repo, expose $(PORT))"
	@echo "  docker-bash      Shell into a dev container"
	@echo "  docker-clean     Remove dangling images/containers"
	@echo
	@echo "Ollama:"
	@echo "  ollama-serve     Start Ollama server (foreground)"
	@echo "  ollama-pull      Pull base model ($(BASE_MODEL))"
	@echo "  build-latin      Create $(LATIN_TAG) from models/latin/Modelfile"
	@echo "  build-greek      Create $(GREEK_TAG) from models/greek/Modelfile"
	@echo "  smoke-latin      One-shot classify via API for Latin"
	@echo "  smoke-greek      One-shot classify via API for Greek"
	@echo "  ensure-models    Verify tags exist on server"
	@echo "  health           Check Ollama API availability"
	@echo
	@echo "Config via env vars:"
	@echo "  OLLAMA_HOST=$(OLLAMA_HOST)  BASE_MODEL=$(BASE_MODEL)"
	@echo "  LATIN_TAG=$(LATIN_TAG)  GREEK_TAG=$(GREEK_TAG)"
	@echo "  PORT=$(PORT)  APP_ENTRY=$(APP_ENTRY)  STREAMLIT_APP=$(STREAMLIT_APP)"

# ===== Meta setup =====
setup: ## prefer Poetry, else venv
ifdef POETRY_BIN
	@$(MAKE) setup-poetry
else
	@$(MAKE) setup-venv
endif

setup-poetry:
	poetry install

setup-venv:
	$(PYTHON) -m venv .venv
	. .venv/bin/activate; $(PIP) install --upgrade pip
	@if [ -f requirements.txt ]; then . .venv/bin/activate; $(PIP) install -r requirements.txt; \
	else echo "No requirements.txt found; if you use Poetry-only, run 'make setup-poetry' instead."; fi

env:
	@echo "PYTHON=$(PYTHON)"
	@echo "Detected Poetry: $(if $(POETRY_BIN),yes,no)"
	@echo "Runner: $(RUNPY)"

# ===== Run & Dev =====
run:
	$(RUNPY) $(APP_ENTRY)

web:
	$(if $(POETRY_BIN),poetry run streamlit run $(STREAMLIT_APP), .venv/bin/streamlit run $(STREAMLIT_APP))

check:
	$(RUN) black --check .

fix:
	$(RUN) black .

test:
	$(RUN) pytest -q

# ===== Docker =====
docker-build:
	docker build -t classics-app .

docker-run:
	docker run --rm -p $(PORT):$(PORT) classics-app

docker-dev:
	# Mount current dir for live reload; assumes container runs Streamlit on $(PORT)
	docker run --rm -it -v $(PWD):/app -w /app -p $(PORT):$(PORT) classics-app

docker-bash:
	docker run --rm -it -v $(PWD):/app -w /app classics-app bash

docker-clean:
	- docker rm $$(docker ps -aq) 2>/dev/null || true
	- docker rmi $$(docker images -f "dangling=true" -q) 2>/dev/null || true

# ===== Ollama =====
ollama-serve:
	ollama serve

ollama-pull:
	ollama pull $(BASE_MODEL)

ollama-list:
	ollama list

build-latin: ## requires models/latin/Modelfile
	ollama create $(LATIN_TAG) -f models/latin/Modelfile

build-greek: ## requires models/greek/Modelfile
	ollama create $(GREEK_TAG) -f models/greek/Modelfile

health:
	@echo "Checking $(OLLAMA_TAGS)"
	@curl -s -o /dev/null -w "%{http_code}\n" $(OLLAMA_TAGS)

smoke-latin:
	@curl -s $(OLLAMA_GEN) \
	  -d '{"model":"$(LATIN_TAG)","prompt":"Classify: Caelum pulchrum est.","stream":false}' | jq .

smoke-greek:
	@curl -s $(OLLAMA_GEN) \
	  -d '{"model":"$(GREEK_TAG)","prompt":"Classify: ἀγαθὸς ἀνήρ.","stream":false}' | jq .

ensure-ollama:
	@code=$$(curl -s -o /dev/null -w "%{http_code}" $(OLLAMA_TAGS)); \
	if [ "$$code" != "200" ]; then \
	  echo "Ollama not reachable at $(OLLAMA_HOST) (status $$code)"; exit 1; fi

ensure-models: ensure-ollama
	@names=$$(curl -s $(OLLAMA_TAGS) | jq -r '.models[].name'); \
	echo "$$names" | grep -qx '$(LATIN_TAG)' || (echo "Missing model tag: $(LATIN_TAG)"; exit 1); \
	echo "$$names" | grep -qx '$(GREEK_TAG)' || (echo "Missing model tag: $(GREEK_TAG)"; exit 1); \
	echo "All required models present."

