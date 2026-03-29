ifeq ($(OS),Windows_NT)
    DETECTED_OS := windows
else
    DETECTED_OS := unix
endif


# Makefile (replace the Windows KILL_PORT define)
ifeq ($(DETECTED_OS),windows)
define KILL_PORT
@echo "🔍 Checking port $(1) on Windows..."
@powershell -NoProfile -Command "try { \
  $$conns = Get-NetTCPConnection -LocalPort $(1) -State Listen -ErrorAction SilentlyContinue; \
  if ($$null -ne $$conns) { \
    foreach ($$c in $$conns) { Stop-Process -Id $$c.OwningProcess -Force -ErrorAction SilentlyContinue } ; \
    Write-Output '✅ Port $(1) cleared (Windows)'; \
  } else { \
    Write-Output '✅ Port $(1) is free'; \
  } \
} catch { Write-Output '⚠️  Port check failed, continuing' }"
endef
else
define KILL_PORT
@echo "🔍 Checking port $(1) on macOS/Linux..."
@PID=$$(lsof -ti :$(1)); \
if [ ! -z "$$PID" ]; then \
  echo "⚠️  Port $(1) in use — killing PID $$PID"; \
  kill -9 $$PID || true; \
else \
  echo "✅ Port $(1) is free"; \
fi
endef
endif

# ===== Config =====
PROJECT_NAME  := Trojan Parse
VENV_DIR      := .venv
PIP          ?= pip3
PORT         ?= 8501
APP_ENTRY    ?= src/app/server_streamlit.py
STREAMLIT_APP?= src/app/server_streamlit.py

# ---- Python / Poetry / venv per OS ----
ifeq ($(DETECTED_OS),windows)
    PYTHON       := python
    PIP          := pip
    VENV_PYTHON  := $(VENV_DIR)\Scripts\python.exe
    POETRY_BIN   :=
    RUNPY        := $(VENV_PYTHON)
    RUN          := $(VENV_PYTHON) -m
    PIP_RUN      := $(VENV_PYTHON) -m pip
else
    PYTHON      ?= python3
    VENV_PYTHON := $(VENV_DIR)/bin/python
    POETRY_BIN  := $(shell command -v poetry 2>/dev/null)
    HAVE_VENV   := $(wildcard $(VENV_PYTHON))
    RUNPY       := $(if $(HAVE_VENV),$(VENV_PYTHON),$(if $(POETRY_BIN),poetry run $(PYTHON),$(VENV_PYTHON)))
    RUN         := $(if $(HAVE_VENV),$(VENV_PYTHON) -m,$(if $(POETRY_BIN),poetry run,$(VENV_PYTHON) -m))
    PIP_RUN     := $(if $(HAVE_VENV),$(VENV_PYTHON) -m pip,$(if $(POETRY_BIN),poetry run $(PIP),$(VENV_PYTHON) -m pip))
endif

# Ollama
OLLAMA_HOST   ?= http://localhost:11434
OLLAMA_GEN    := $(OLLAMA_HOST)/api/generate
OLLAMA_TAGS   := $(OLLAMA_HOST)/api/tags
LATIN_TAG     ?= latin_ollama_model:1.0.0
GREEK_TAG     ?= greek_ollama_model:1.0.0
BASE_MODEL    ?= llama3.1:8b

# ===== Frontend (React) =====
FRONTEND_DIR  ?= src/frontend
FRONTEND_PORT ?= 3000
FE_DIR        ?= src/frontend/src
NPM           ?= npm

# ===== Notebooks -> JupyterLite =====
NB_SRC_DIR        ?= notebooks
JLITE_DIR         ?= src/frontend/public/jlite
JLITE_FILES_DIR   ?= $(JLITE_DIR)/files
JLITE_NB_DIR      ?= $(JLITE_FILES_DIR)/notebooks
JLITE_INDEX_JSON  ?= $(JLITE_NB_DIR)/index.json

# ===== FastAPI (Uvicorn) =====
API_PORT ?= 5050
API_APP  ?= app.server_fast:app

# Detect frontend package manager
FE_PM := npm



# ===== Colors =====
ifeq ($(NO_COLOR),)
ESC      := \033
RESET    := $(ESC)[0m
BOLD     := $(ESC)[1m

GREEN    := $(ESC)[1;32m
YELLOW   := $(ESC)[1;33m
BLUE     := $(ESC)[1;34m
PURPLE   := $(ESC)[1;35m
GREY     := $(ESC)[90m
WHITE    := $(ESC)[1;37m
else
RESET    :=
BOLD     :=
GREEN    :=
YELLOW   :=
BLUE     :=
PURPLE   :=
GREY     :=
WHITE    :=
endif


FE_PM_DEV     := npm run dev -- -p $(FRONTEND_PORT)
FE_PM_BUILD   := npm run build
FE_PM_PREVIEW := npm run start -- -p $(FRONTEND_PORT)
FE_PM_INSTALL := npm install
endif

.PHONY: help setup setup-venv env run web check fix test \
        docker-build docker-run docker-dev docker-bash docker-clean \
        ollama-serve ollama-pull ollama-list build-latin build-greek \
        smoke-latin smoke-greek ensure-ollama ensure-models health \
        fe-install fe-dev fe-build fe-serve fe-clean fe-lint fe-lint-fix \
        fe-format fe-format-check run-all \
        nb-bootstrap nb-sync nb-index \
        jlite-build jlite-serve jlite-clean \
        api-deps api-run api-health \
        start start-lite

# ===== Help screen =====
help:
	@echo "$(PROJECT_NAME) Makefile (OS = $(DETECTED_OS))"
	@printf "Usage: make <target>\n\n"
	@printf "$(GREEN)Start Here: First time Deployment:$(RESET)\n"
	@printf "$(GREEN)  start            Install backend dependencies, JupyterLite, and frontend dev$(RESET)\n\n"
	@printf "$(GREEN)Start Lite: (without JupyterLite)$(RESET)\n"
	@printf "$(GREEN)  start-lite       Install backend dependencies and start frontend + Streamlit$(RESET)\n\n"
	@printf "$(YELLOW)Core:$(RESET)\n"
	@printf "$(YELLOW)  setup            Install backend dependencies (Poetry or venv)$(RESET)\n"
	@printf "$(YELLOW)  run              Run backend app ($(APP_ENTRY))$(RESET)\n"
	@printf "$(YELLOW)  web              Run Streamlit UI ($(STREAMLIT_APP))$(RESET)\n"
	@printf "$(YELLOW)  test             Run pytest tests$(RESET)\n"
	@printf "$(YELLOW)  check / fix      Format or lint Python code$(RESET)\n\n"
	@printf "$(BLUE)Frontend (Next.js):$(RESET)\n"
	@printf "$(BLUE)  fe-install       Install frontend dependencies ($(FE_PM))$(RESET)\n"
	@printf "$(BLUE)  fe-dev           Start Next.js dev server (port $(FRONTEND_PORT))$(RESET)\n"
	@printf "$(BLUE)  fe-build         Build production bundle$(RESET)\n"
	@printf "$(BLUE)  fe-serve         Start production server$(RESET)\n"
	@printf "$(BLUE)  fe-clean         Remove node_modules and .next$(RESET)\n"
	@printf "$(BLUE)  run-all          Run Streamlit + FastAPI + Next.js dev servers together$(RESET)\n\n"
	@printf "$(GREY)Docker / Ollama:$(RESET)\n"
	@printf "$(GREY)  docker-build, docker-run, docker-dev, docker-bash, docker-clean$(RESET)\n"
	@printf "$(GREY)  ollama-serve, ollama-pull, build-latin, build-greek, smoke-latin, smoke-greek$(RESET)\n\n"
	@printf "$(GREY)Config:$(RESET)\n"
	@printf "$(GREY)  PORT=$(PORT)  FRONTEND_PORT=$(FRONTEND_PORT)$(RESET)\n"
	@printf "$(GREY)  FRONTEND_DIR=$(FRONTEND_DIR)  FE_PM=$(FE_PM)$(RESET)\n\n"
	@printf "$(WHITE)Notebooks:$(RESET)\n"
	@printf "$(WHITE)  nb-bootstrap      Initialize JupyterLite and notebook folders$(RESET)\n"
	@printf "$(WHITE)  nb-sync           Copy notebooks/ → frontend/public/jlite/files/notebooks/$(RESET)\n"
	@printf "$(WHITE)  nb-index          Regenerate notebooks index.json$(RESET)\n\n"
	@printf "$(WHITE)JupyterLite:$(RESET)\n"
	@printf "$(WHITE)  jlite-build       Build a local JupyterLite bundle into frontend/public/jlite$(RESET)\n"
	@printf "$(WHITE)  jlite-serve       Serve the built JupyterLite locally for quick testing$(RESET)\n"
	@printf "$(WHITE)  jlite-clean       Remove the JupyterLite output directory$(RESET)\n\n"
	@printf "$(PURPLE)FastAPI Backend:$(RESET)\n"
	@printf "$(PURPLE)  api-deps          Install FastAPI and Uvicorn dependencies$(RESET)\n"
	@printf "$(PURPLE)  api-run           Run FastAPI backend server$(RESET)\n"
	@printf "$(PURPLE)  api-health        Check FastAPI health endpoint$(RESET)\n\n"

# ===== Setup =====
setup:
ifeq ($(DETECTED_OS),unix)
ifneq ($(POETRY_BIN),)
	@if poetry run python -c "import sys" >/dev/null 2>&1; then \
	  echo "Using Poetry..." ; \
	  poetry install ; \
	else \
	  echo "Poetry detected but not usable (likely Python version mismatch). Using venv..." ; \
	  $(PYTHON) -m venv $(VENV_DIR) ; \
	  $(VENV_PYTHON) -m pip install --upgrade pip ; \
	  if [ -f requirements.txt ]; then $(VENV_PYTHON) -m pip install -r requirements.txt ; fi ; \
	fi
else
	@echo "Using venv..."
	$(PYTHON) -m venv $(VENV_DIR)
	$(VENV_PYTHON) -m pip install --upgrade pip
	@if [ -f requirements.txt ]; then $(VENV_PYTHON) -m pip install -r requirements.txt; fi
endif
else
	@echo "Using venv (Windows)..."
	$(PYTHON) -m venv $(VENV_DIR)
	$(VENV_PYTHON) -m pip install --upgrade pip
	@if exist requirements.txt ( "$(VENV_PYTHON)" -m pip install -r requirements.txt )
endif

	@$(MAKE) api-deps
	@$(MAKE) nb-bootstrap

setup-venv:
ifeq ($(DETECTED_OS),unix)
	@echo "Using venv..."
	$(PYTHON) -m venv $(VENV_DIR)
	$(VENV_PYTHON) -m pip install --upgrade pip
	@if [ -f requirements.txt ]; then $(VENV_PYTHON) -m pip install -r requirements.txt; fi
else
	@echo "Using venv (Windows)..."
	$(PYTHON) -m venv $(VENV_DIR)
	$(VENV_PYTHON) -m pip install --upgrade pip
	@if exist requirements.txt ( "$(VENV_PYTHON)" -m pip install -r requirements.txt )
endif

	@$(MAKE) api-deps
	@$(MAKE) nb-bootstrap

env:
	@echo "DETECTED_OS=$(DETECTED_OS)"
	@echo "PYTHON=$(PYTHON)"
	@echo "VENV_PYTHON=$(VENV_PYTHON)"
	@echo "Poetry detected: $(if $(POETRY_BIN),yes,no)"
	@echo "RUNPY=$(RUNPY)"
	@echo "RUN=$(RUN)"

# ===== Backend Run & Tests =====
run:
	$(RUNPY) $(APP_ENTRY)

web:
ifeq ($(DETECTED_OS),windows)
	$(VENV_PYTHON) -m streamlit run $(STREAMLIT_APP)
else
	@if [ -x "$(VENV_DIR)/bin/streamlit" ]; then \
	  PYTHONPATH="$(CURDIR)" $(VENV_DIR)/bin/streamlit run $(STREAMLIT_APP); \
	elif [ -n "$(POETRY_BIN)" ] && poetry run python -c "import sys" >/dev/null 2>&1; then \
	  PYTHONPATH="$(CURDIR)" poetry run streamlit run $(STREAMLIT_APP); \
	else \
	  PYTHONPATH="$(CURDIR)" $(VENV_DIR)/bin/streamlit run $(STREAMLIT_APP); \
	fi
endif

check:
	$(RUN) black --check .
	$(MAKE) -s fe-lint
	$(MAKE) -s fe-format-check

fix:
	$(RUN) black .
	$(MAKE) -s fe-lint-fix
	$(MAKE) -s fe-format

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
	@$(call KILL_PORT,$(FRONTEND_PORT))
	@echo "Starting frontend dev server on port $(FRONTEND_PORT)..."
	@cd $(FRONTEND_DIR) && $(FE_PM_DEV)

fe-build:
	@echo "Building production frontend..."
	@cd $(FRONTEND_DIR) && $(FE_PM_BUILD)

fe-serve:
	@$(call KILL_PORT,$(FRONTEND_PORT))
	@echo "Starting production server on port $(FRONTEND_PORT)..."
	@cd $(FRONTEND_DIR) && $(FE_PM_PREVIEW)

fe-clean:
	@echo "Cleaning frontend node_modules and .next..."
	@rm -rf $(FRONTEND_DIR)/node_modules $(FRONTEND_DIR)/.next

fe-lint:
	cd $(FE_DIR) && ($(NPM) run -s lint || echo "skip: no 'lint' script")

fe-lint-fix:
	cd $(FE_DIR) && ($(NPM) run -s lint:fix || echo "skip: no 'lint:fix' script")

fe-format:
	cd $(FE_DIR) && ($(NPM) run -s format || echo "skip: no 'format' script")

fe-format-check:
	cd $(FE_DIR) && ($(NPM) run -s format:check || echo "skip: no 'format:check' script")


# ===== Notebooks / JupyterLite =====
# makefile
nb-bootstrap:
ifeq ($(DETECTED_OS),windows)
	@powershell -Command "New-Item -ItemType Directory -Force -Path '$(NB_SRC_DIR)' >$null"
	@powershell -Command "New-Item -ItemType Directory -Force -Path '$(JLITE_NB_DIR)' >$null"
	@powershell -Command "if (Test-Path -Path '$(JLITE_DIR)/lab/index.html') { Write-Output '✅ JupyterLite present at $(JLITE_DIR)' } else { Write-Output '⚠️  JupyterLite not found at $(JLITE_DIR). Drop a Lite build there (lab/index.html).' }"
	@echo "✅ Notebook environment initialized. Place .ipynb files in $(NB_SRC_DIR)/ and run 'make nb-sync'"
else
	@mkdir -p "$(NB_SRC_DIR)"
	@mkdir -p "$(JLITE_NB_DIR)"
	@if [ ! -f "$(JLITE_DIR)/lab/index.html" ]; then \
		echo "⚠️  JupyterLite not found at $(JLITE_DIR). Drop a Lite build there (lab/index.html)."; \
	else \
		echo "✅ JupyterLite present at $(JLITE_DIR)"; \
 	fi
	@echo "✅ Notebook environment initialized. Place .ipynb files in $(NB_SRC_DIR)/ and run 'make nb-sync'"
endif

nb-sync: nb-bootstrap
ifeq ($(DETECTED_OS),windows)
	@powershell -Command "New-Item -ItemType Directory -Force -Path '$(JLITE_NB_DIR)' >$$null"
	@powershell -Command "Get-ChildItem -Path '$(NB_SRC_DIR)' -Filter '*.ipynb' -File | ForEach-Object { Copy-Item -Path $$_.FullName -Destination '$(JLITE_NB_DIR)' -Force }"
	@$(MAKE) nb-index
	@echo "✅ Synced notebooks to $(JLITE_NB_DIR)"
else
	@mkdir -p "$(JLITE_NB_DIR)"
	@find "$(NB_SRC_DIR)" -maxdepth 1 -type f -name "*.ipynb" -print0 | xargs -0 -I{} cp "{}" "$(JLITE_NB_DIR)"/
	@$(MAKE) nb-index
	@echo "✅ Synced notebooks to $(JLITE_NB_DIR)"
endif


nb-index:
	@$(PYTHON) -c "import json, os; nb='$(JLITE_NB_DIR)'; idx='$(JLITE_INDEX_JSON)'; \
	files=[f for f in os.listdir(nb) if f.endswith('.ipynb')] if os.path.isdir(nb) else []; \
	data={'notebooks':[{'name':os.path.splitext(f)[0],'path':f} for f in sorted(files)]}; \
	os.makedirs(os.path.dirname(idx), exist_ok=True); \
	json.dump(data, open(idx,'w',encoding='utf8'), indent=2); \
	print('Wrote', idx, 'with', len(files), 'notebooks')" || echo "nb-index failed"

# JupyterLite build/serve
jlite-build:
	@echo "🧱 Installing JupyterLite..."
	$(PIP_RUN) install -U "jupyterlite[all]"
	@echo "🏗️  Building JupyterLite into $(JLITE_DIR)..."
	$(RUN) jupyter lite build --output-dir "$(JLITE_DIR)" --force
	@echo "✅ JupyterLite built at $(JLITE_DIR)"
	@echo "📁 Syncing notebooks into JupyterLite files area..."
	@$(MAKE) nb-sync
	@echo "✨ Done. You can now open notebooks via your app modal."

jlite-serve:
	@echo "🌐 Serving $(JLITE_DIR) at http://localhost:5174"
	@cd "$(JLITE_DIR)" && $(PYTHON) -m http.server 5174

jlite-clean:
	@echo "🧹 Removing $(JLITE_DIR)"
	@rm -rf "$(JLITE_DIR)"

# ===== FastAPI backend =====
api-deps:
	$(PIP_RUN) install "fastapi>=0.110" "uvicorn[standard]>=0.23" "pydantic>=2"

api-run:
	PYTHONPATH=$(PWD)/src $(RUN) uvicorn $(API_APP) \
		--host 0.0.0.0 --port $(API_PORT) --reload --app-dir src

api-health:
	curl -s http://localhost:$(API_PORT)/api/health | jq .

# language: makefile
# Replace the Windows branches of start and start-lite in `Makefile`.
start:
ifeq ($(DETECTED_OS),windows)
	@echo "🚀 Setting up Trojan Parse full stack (Windows)..."
	@$(MAKE) setup
	@$(MAKE) jlite-build
	@echo "🌐 Starting FastAPI server on :$(API_PORT)..."
	@echo "📘 Starting Streamlit on :$(PORT)..."
	@$(call KILL_PORT,$(FRONTEND_PORT))
	@powershell -NoProfile -Command "cd '$(CURDIR)'; \
	  Start-Process -FilePath '$(VENV_PYTHON)' -ArgumentList '-m','uvicorn','$(API_APP)','--host','0.0.0.0','--port','$(API_PORT)','--reload','--app-dir','src' -WorkingDirectory '$(CURDIR)'; \
	  Start-Process -FilePath '$(VENV_PYTHON)' -ArgumentList '-m','streamlit','run','$(STREAMLIT_APP)' -WorkingDirectory '$(CURDIR)'; \
	  Start-Process -FilePath 'cmd.exe' -WorkingDirectory '$(CURDIR)\\$(FRONTEND_DIR)' -ArgumentList '/c','$(FE_PM_DEV)';"
else
	@echo "🚀 Setting up Trojan Parse full stack..."
	@$(MAKE) setup
	@$(MAKE) jlite-build
	@echo "🌐 Starting FastAPI server on :$(API_PORT)..."
	( $(MAKE) -s api-run ) &
	@echo "📘 Starting Streamlit on :$(PORT)..."
	( $(MAKE) -s web ) &
	@echo "⚛️  Starting React dev server on :$(FRONTEND_PORT)"
	@$(call KILL_PORT,$(FRONTEND_PORT))
	( cd $(FRONTEND_DIR) && $(FE_PM_DEV) ) &
	wait
endif

start-lite:
ifeq ($(DETECTED_OS),windows)
	@echo "⚡ Quick start (no setup, no JupyterLite build)… (Windows)"
	@echo "🌐 FastAPI → :$(API_PORT), 🏺 Streamlit → :$(PORT), ⚛️ React → :$(FRONTEND_PORT)"
	@$(call KILL_PORT,$(FRONTEND_PORT))
	@powershell -NoProfile -Command "cd '$(CURDIR)'; \
	  Start-Process -FilePath '$(VENV_PYTHON)' -ArgumentList '-m','uvicorn','$(API_APP)','--host','0.0.0.0','--port','$(API_PORT)','--reload','--app-dir','src' -WorkingDirectory '$(CURDIR)'; \
	  Start-Process -FilePath '$(VENV_PYTHON)' -ArgumentList '-m','streamlit','run','$(STREAMLIT_APP)' -WorkingDirectory '$(CURDIR)'; \
	  Start-Process -FilePath 'cmd.exe' -WorkingDirectory '$(CURDIR)\\$(FRONTEND_DIR)' -ArgumentList '/c','$(FE_PM_DEV)'"
else
	@echo "⚡ Quick start (no setup, no JupyterLite build)…"
	@echo "🌐 FastAPI → :$(API_PORT), 🏺 Streamlit → :$(PORT), ⚛️ React → :$(FRONTEND_PORT)"
	@$(call KILL_PORT,$(FRONTEND_PORT))
	( $(MAKE) -s api-run ) &
	( $(MAKE) -s web ) &
	( cd $(FRONTEND_DIR) && $(FE_PM_DEV) ) &
	wait
endif
