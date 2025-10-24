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
RUNPY         := $(if $(POETRY_BIN),poetry run $(PYTHON),.venv/bin/$(PYTHON))
RUN           := $(if $(POETRY_BIN),poetry run, .venv/bin)
PIP_RUN       := $(if $(POETRY_BIN),poetry run $(PIP),.venv/bin/$(PIP))

# ===== Frontend (React) =====
FRONTEND_DIR ?= src/frontend
FRONTEND_PORT ?= 5173

FE_PM := $(shell \
  cd $(FRONTEND_DIR) 2>/dev/null && \
  if command -v pnpm >/dev/null 2>&1 && [ -f pnpm-lock.yaml ]; then echo pnpm; \
  elif command -v yarn >/dev/null 2>&1 && [ -f yarn.lock ]; then echo yarn; \
  else echo npm; fi \
)

ifeq ($(FE_PM),pnpm)
FE_PM_DEV     := pnpm dev
FE_PM_BUILD   := pnpm build
FE_PM_PREVIEW := pnpm preview
FE_PM_INSTALL := pnpm install --frozen-lockfile
else ifeq ($(FE_PM),yarn)
FE_PM_DEV     := yarn dev
FE_PM_BUILD   := yarn build
FE_PM_PREVIEW := yarn preview
FE_PM_INSTALL := yarn install --frozen-lockfile
else
FE_PM_DEV     := npm run dev
FE_PM_BUILD   := npm run build
FE_PM_PREVIEW := npm run preview
FE_PM_INSTALL := npm install
endif


.PHONY: help setup setup-poetry setup-venv env run web check fix test \
        docker-build docker-run docker-dev docker-bash docker-clean \
        ollama-serve ollama-pull ollama-list build-latin build-greek \
        smoke-latin smoke-greek ensure-ollama ensure-models health \
        fe-install fe-dev fe-build fe-serve fe-clean run-all



# ===== Help screen =====
help:
	@echo "Usage: make <target>"
	@echo
	@echo "Core:"
	@echo "  setup            Install backend dependencies (Poetry or venv)"
	@echo "  run              Run backend app ($(APP_ENTRY))"
	@echo "  web              Run Streamlit UI ($(STREAMLIT_APP))"
	@echo "  test             Run pytest tests"
	@echo "  check / fix      Format or lint Python code"
	@echo
	@echo "Frontend (React):"
	@echo "  fe-install       Install frontend dependencies ($(FE_PM))"
	@echo "  fe-dev           Start React dev server (port $(FRONTEND_PORT))"
	@echo "  fe-build         Build production bundle"
	@echo "  fe-serve         Preview production build"
	@echo "  fe-clean         Remove node_modules and dist"
	@echo "  run-all          Run Streamlit + React dev servers together"
	@echo
	@echo "Docker / Ollama:"
	@echo "  docker-build, docker-run, docker-dev, docker-bash, docker-clean"
	@echo "  ollama-serve, ollama-pull, build-latin, build-greek, smoke-latin, smoke-greek"
	@echo
	@echo "Config:"
	@echo "  PORT=$(PORT)  FRONTEND_PORT=$(FRONTEND_PORT)"
	@echo "  FRONTEND_DIR=$(FRONTEND_DIR)  FE_PM=$(FE_PM)"
	@echo

# ===== Setup =====
setup:
ifdef POETRY_BIN
	@echo "Using Poetry..."
	poetry install
else
	@echo "Using venv..."
	$(PYTHON) -m venv .venv
	. .venv/bin/activate; $(PIP) install --upgrade pip
	@if [ -f requirements.txt ]; then . .venv/bin/activate; $(PIP) install -r requirements.txt; fi
endif

env:
	@echo "PYTHON=$(PYTHON)"
	@echo "Detected Poetry: $(if $(POETRY_BIN),yes,no)"
	@echo "Runner: $(RUNPY)"

# ===== Backend Run & Tests =====
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

build-latin:
	ollama create $(LATIN_TAG) -f models/latin_model/Modelfile

build-greek:
	ollama create $(GREEK_TAG) -f models/greek_model/Modelfile

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

# ===== Frontend Commands =====
fe-install:
	@echo "Installing frontend deps in $(FRONTEND_DIR) using $(FE_PM)"
	@cd $(FRONTEND_DIR) && $(FE_PM_INSTALL)

fe-dev:
	@echo "Starting frontend dev server on port $(FRONTEND_PORT)..."
	@cd $(FRONTEND_DIR) && $(FE_PM_DEV)

fe-build:
	@echo "Building production frontend..."
	@cd $(FRONTEND_DIR) && $(FE_PM_BUILD)

fe-serve:
	@echo "Previewing production build..."
	@cd $(FRONTEND_DIR) && $(FE_PM_PREVIEW)

fe-clean:
	@echo "Cleaning frontend node_modules and dist..."
	@rm -rf $(FRONTEND_DIR)/node_modules $(FRONTEND_DIR)/dist

# ===== Combined Runner =====
run-all:
	@echo "Starting Streamlit (port $(PORT)) and React (port $(FRONTEND_PORT))..."
	( $(MAKE) -s web ) & \
	( cd $(FRONTEND_DIR) && $(FE_PM_DEV) ) & \
	wait
