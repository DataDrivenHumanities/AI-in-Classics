ifeq ($(OS),Windows_NT)
    DETECTED_OS := windows
else
    DETECTED_OS := unix
endif

# ===== Kill-port helper =====
ifeq ($(DETECTED_OS),windows)
define KILL_PORT
@echo "Checking port $(1) on Windows..."
@powershell -NoProfile -Command "try { \
  $$conns = Get-NetTCPConnection -LocalPort $(1) -State Listen -ErrorAction SilentlyContinue; \
  if ($$null -ne $$conns) { \
    foreach ($$c in $$conns) { Stop-Process -Id $$c.OwningProcess -Force -ErrorAction SilentlyContinue } ; \
    Write-Output 'Port $(1) cleared (Windows)'; \
  } else { \
    Write-Output 'Port $(1) is free'; \
  } \
} catch { Write-Output 'Port check failed, continuing' }"
endef
else
define KILL_PORT
@echo "Checking port $(1) on macOS/Linux..."
@PID=$$(lsof -ti :$(1)); \
if [ ! -z "$$PID" ]; then \
  echo "Port $(1) in use, killing PID $$PID"; \
  kill -9 $$PID || true; \
else \
  echo "Port $(1) is free"; \
fi
endef
endif

# ===== Config =====
PROJECT_NAME  := Trojan Parse
VENV_DIR      := .venv
PORT         ?= 8501
STREAMLIT_APP ?= src/app/server_streamlit.py
APP_ENTRY     ?= $(STREAMLIT_APP)

# ===== Python / uv per OS =====
ifeq ($(DETECTED_OS),windows)
    PYTHON      := python
    VENV_PYTHON := $(VENV_DIR)\Scripts\python.exe
else
    PYTHON      ?= python3
    VENV_PYTHON  := $(VENV_DIR)/bin/python
endif

# These are identical on both platforms so they live outside the ifeq
UV      := uv
RUNPY   := $(VENV_PYTHON)
RUN     := $(VENV_PYTHON) -m
PIP_RUN := uv pip install --python $(VENV_PYTHON)

# ===== Ollama =====
OLLAMA_HOST ?= http://localhost:11434
OLLAMA_GEN  := $(OLLAMA_HOST)/api/generate
OLLAMA_TAGS := $(OLLAMA_HOST)/api/tags
LATIN_TAG   ?= latin_ollama_model:1.0.0
GREEK_TAG   ?= greek_ollama_model:1.0.0
BASE_MODEL  ?= llama3.1:8b

# ===== Frontend =====
FRONTEND_DIR  ?= src/frontend
FRONTEND_PORT ?= 3000
FE_DIR        ?= src/frontend/src
FE_PM         ?= npm
FE_PM_DEV     := $(FE_PM) run dev -- -p $(FRONTEND_PORT)
FE_PM_BUILD   := $(FE_PM) run build
FE_PM_PREVIEW := $(FE_PM) run start -- -p $(FRONTEND_PORT)
FE_PM_INSTALL := $(FE_PM) install

# ===== Notebooks / JupyterLite =====
NB_SRC_DIR       ?= notebooks
JLITE_DIR        ?= src/frontend/public/jlite
JLITE_NB_DIR     ?= $(JLITE_DIR)/files/notebooks
JLITE_INDEX_JSON ?= $(JLITE_NB_DIR)/index.json

# ===== FastAPI =====
API_PORT ?= 5050
API_APP  ?= app.server_fast:app

# ===== Colors =====
ifeq ($(NO_COLOR),)
ESC    := \033
RESET  := $(ESC)[0m
GREEN  := $(ESC)[1;32m
YELLOW := $(ESC)[1;33m
BLUE   := $(ESC)[1;34m
PURPLE := $(ESC)[1;35m
GREY   := $(ESC)[90m
WHITE  := $(ESC)[1;37m
else
RESET  :=
GREEN  :=
YELLOW :=
BLUE   :=
PURPLE :=
GREY   :=
WHITE  :=
endif

# ===== Phony targets =====
.PHONY: help setup env run web check fix test \
        docker-build docker-run docker-dev docker-bash docker-clean \
        ollama-serve ollama-pull ollama-list build-latin build-greek \
        smoke-latin smoke-greek ensure-ollama ensure-models health \
        fe-install fe-dev fe-build fe-serve fe-clean fe-lint fe-lint-fix \
        fe-format fe-format-check \
        nb-bootstrap nb-sync nb-index \
        jlite-build jlite-serve jlite-clean \
        api-deps api-run api-health \
        start start-lite

# ===== Help =====
help:
	@echo "$(PROJECT_NAME) Makefile (OS = $(DETECTED_OS))"
	@printf "Usage: make <target>\n\n"
	@printf "$(GREEN)  start            Full install (venv, deps, npm, jlite) then launch all servers$(RESET)\n"
	@printf "$(GREEN)  start-lite       Launch all servers without reinstalling$(RESET)\n\n"
	@printf "$(YELLOW)  setup            Install all dependencies (venv, pip, npm, jlite)$(RESET)\n"
	@printf "$(YELLOW)  run              Run backend app ($(APP_ENTRY))$(RESET)\n"
	@printf "$(YELLOW)  web              Run Streamlit UI ($(STREAMLIT_APP))$(RESET)\n"
	@printf "$(YELLOW)  test             Run pytest tests$(RESET)\n"
	@printf "$(YELLOW)  check / fix      Lint or format Python and frontend code$(RESET)\n\n"
	@printf "$(BLUE)  fe-install       Install frontend dependencies$(RESET)\n"
	@printf "$(BLUE)  fe-dev           Start Next.js dev server (port $(FRONTEND_PORT))$(RESET)\n"
	@printf "$(BLUE)  fe-build         Build production bundle$(RESET)\n"
	@printf "$(BLUE)  fe-serve         Start production server$(RESET)\n"
	@printf "$(BLUE)  fe-clean         Remove node_modules and .next$(RESET)\n\n"
	@printf "$(WHITE)  nb-bootstrap     Initialize notebook and JupyterLite folders$(RESET)\n"
	@printf "$(WHITE)  nb-sync          Copy notebooks/ into the JupyterLite files area$(RESET)\n"
	@printf "$(WHITE)  nb-index         Regenerate notebooks index.json$(RESET)\n"
	@printf "$(WHITE)  jlite-build      Build JupyterLite bundle into frontend/public/jlite$(RESET)\n"
	@printf "$(WHITE)  jlite-serve      Serve the built JupyterLite locally for testing$(RESET)\n"
	@printf "$(WHITE)  jlite-clean      Remove the JupyterLite output directory$(RESET)\n\n"
	@printf "$(PURPLE)  api-deps         Install FastAPI and Uvicorn$(RESET)\n"
	@printf "$(PURPLE)  api-run          Run FastAPI backend$(RESET)\n"
	@printf "$(PURPLE)  api-health       Check FastAPI health endpoint$(RESET)\n\n"
	@printf "$(GREY)  docker-build, docker-run, docker-dev, docker-bash, docker-clean$(RESET)\n"
	@printf "$(GREY)  ollama-serve, ollama-pull, build-latin, build-greek, smoke-latin, smoke-greek$(RESET)\n"
	@printf "$(GREY)  PORT=$(PORT)  FRONTEND_PORT=$(FRONTEND_PORT)  API_PORT=$(API_PORT)$(RESET)\n\n"

# ===== Setup =====
# Creates the venv, installs Python deps, FastAPI, npm packages, and JupyterLite.
# start calls this so you never need to run setup and start separately.
setup:
ifeq ($(DETECTED_OS),windows)
	@echo "Creating venv with uv (Windows)..."
	$(UV) venv $(VENV_DIR)
	$(PIP_RUN) --upgrade pip
	@if exist requirements.txt ( $(PIP_RUN) -r requirements.txt )
else
	@echo "Creating venv with uv..."
	$(UV) venv $(VENV_DIR)
	$(PIP_RUN) --upgrade pip
	@if [ -f requirements.txt ]; then $(PIP_RUN) -r requirements.txt; fi
endif
	@$(MAKE) -s api-deps
	@$(MAKE) -s fe-install
	@$(MAKE) -s jlite-build

env:
	@echo "DETECTED_OS = $(DETECTED_OS)"
	@echo "VENV_PYTHON = $(VENV_PYTHON)"
	@echo "UV          = $(UV)"
	@echo "RUN         = $(RUN)"
	@echo "PIP_RUN     = $(PIP_RUN)"

# ===== Backend =====
run:
	$(RUNPY) $(APP_ENTRY)

web:
ifeq ($(DETECTED_OS),windows)
	$(VENV_PYTHON) -m streamlit run $(STREAMLIT_APP)
else
	PYTHONPATH="$(CURDIR)" $(VENV_DIR)/bin/streamlit run $(STREAMLIT_APP)
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

# ===== Frontend =====
fe-install:
	@echo "Installing frontend deps in $(FRONTEND_DIR)..."
	cd $(FRONTEND_DIR) && $(FE_PM_INSTALL)

fe-dev:
	@$(call KILL_PORT,$(FRONTEND_PORT))
	@echo "Starting frontend dev server on port $(FRONTEND_PORT)..."
	cd $(FRONTEND_DIR) && $(FE_PM_DEV)

fe-build:
	@echo "Building production frontend..."
	cd $(FRONTEND_DIR) && $(FE_PM_BUILD)

fe-serve:
	@$(call KILL_PORT,$(FRONTEND_PORT))
	@echo "Starting production server on port $(FRONTEND_PORT)..."
	cd $(FRONTEND_DIR) && $(FE_PM_PREVIEW)

fe-clean:
	@echo "Cleaning frontend node_modules and .next..."
	rm -rf $(FRONTEND_DIR)/node_modules $(FRONTEND_DIR)/.next

fe-lint:
	cd $(FE_DIR) && ($(FE_PM) run -s lint || echo "skip: no 'lint' script")

fe-lint-fix:
	cd $(FE_DIR) && ($(FE_PM) run -s lint:fix || echo "skip: no 'lint:fix' script")

fe-format:
	cd $(FE_DIR) && ($(FE_PM) run -s format || echo "skip: no 'format' script")

fe-format-check:
	cd $(FE_DIR) && ($(FE_PM) run -s format:check || echo "skip: no 'format:check' script")

# ===== Notebooks / JupyterLite =====
nb-bootstrap:
ifeq ($(DETECTED_OS),windows)
	@powershell -Command "New-Item -ItemType Directory -Force -Path '$(NB_SRC_DIR)' >$$null"
	@powershell -Command "New-Item -ItemType Directory -Force -Path '$(JLITE_NB_DIR)' >$$null"
	@powershell -Command "if (Test-Path '$(JLITE_DIR)/lab/index.html') { Write-Output 'JupyterLite present at $(JLITE_DIR)' } else { Write-Output 'JupyterLite not found at $(JLITE_DIR). Run make jlite-build first.' }"
else
	@mkdir -p "$(NB_SRC_DIR)" "$(JLITE_NB_DIR)"
	@if [ ! -f "$(JLITE_DIR)/lab/index.html" ]; then \
	  echo "JupyterLite not found at $(JLITE_DIR). Run make jlite-build first."; \
	else \
	  echo "JupyterLite present at $(JLITE_DIR)"; \
	fi
endif

# nb-bootstrap already creates JLITE_NB_DIR so no need to repeat it here
nb-sync: nb-bootstrap
ifeq ($(DETECTED_OS),windows)
	@powershell -Command "Get-ChildItem -Path '$(NB_SRC_DIR)' -Filter '*.ipynb' -File | ForEach-Object { Copy-Item -Path $$_.FullName -Destination '$(JLITE_NB_DIR)' -Force }"
else
	@find "$(NB_SRC_DIR)" -maxdepth 1 -type f -name "*.ipynb" -print0 | xargs -0 -I{} cp "{}" "$(JLITE_NB_DIR)"/
endif
	@$(MAKE) -s nb-index
	@echo "Synced notebooks to $(JLITE_NB_DIR)"

nb-index:
	@$(PYTHON) -c "import json, os; nb='$(JLITE_NB_DIR)'; idx='$(JLITE_INDEX_JSON)'; \
	files=[f for f in os.listdir(nb) if f.endswith('.ipynb')] if os.path.isdir(nb) else []; \
	data={'notebooks':[{'name':os.path.splitext(f)[0],'path':f} for f in sorted(files)]}; \
	os.makedirs(os.path.dirname(idx), exist_ok=True); \
	json.dump(data, open(idx,'w',encoding='utf8'), indent=2); \
	print('Wrote', idx, 'with', len(files), 'notebooks')" || echo "nb-index failed"

jlite-build:
	@echo "Installing JupyterLite..."
	$(PIP_RUN) -U "jupyterlite[all]"
	@echo "Building JupyterLite into $(JLITE_DIR)..."
	$(RUN) jupyter lite build --output-dir "$(JLITE_DIR)" --force
	@$(MAKE) -s nb-sync
	@echo "JupyterLite ready at $(JLITE_DIR)"

jlite-serve:
	@echo "Serving $(JLITE_DIR) at http://localhost:5174"
	cd "$(JLITE_DIR)" && $(PYTHON) -m http.server 5174

jlite-clean:
	@echo "Removing $(JLITE_DIR)"
	rm -rf "$(JLITE_DIR)"

# ===== FastAPI =====
api-deps:
	$(PIP_RUN) "fastapi>=0.110" "uvicorn[standard]>=0.23" "pydantic>=2"

api-run:
	PYTHONPATH=$(PWD)/src $(RUN) uvicorn $(API_APP) \
		--host 0.0.0.0 --port $(API_PORT) --reload --app-dir src

api-health:
	curl -s http://localhost:$(API_PORT)/api/health | jq .

# ===== Start targets =====
# start runs setup (which installs everything) then launches all three servers.
# start-lite skips setup and launches servers directly, assuming setup was already run.
start:
	@$(MAKE) -s setup
ifeq ($(DETECTED_OS),windows)
	@echo "Starting all servers (Windows)..."
	@$(call KILL_PORT,$(FRONTEND_PORT))
	@powershell -NoProfile -Command "cd '$(CURDIR)'; \
	  Start-Process -FilePath '$(VENV_PYTHON)' -ArgumentList '-m','uvicorn','$(API_APP)','--host','0.0.0.0','--port','$(API_PORT)','--reload','--app-dir','src' -WorkingDirectory '$(CURDIR)'; \
	  Start-Process -FilePath '$(VENV_PYTHON)' -ArgumentList '-m','streamlit','run','$(STREAMLIT_APP)' -WorkingDirectory '$(CURDIR)'; \
	  Start-Process -FilePath 'cmd.exe' -WorkingDirectory '$(CURDIR)\\$(FRONTEND_DIR)' -ArgumentList '/c','$(FE_PM_DEV)';"
else
	@echo "Starting all servers..."
	@$(call KILL_PORT,$(FRONTEND_PORT))
	( $(MAKE) -s api-run ) &
	( $(MAKE) -s web ) &
	( cd $(FRONTEND_DIR) && $(FE_PM_DEV) ) &
	wait
endif

start-lite:
ifeq ($(DETECTED_OS),windows)
	@echo "Quick start (Windows) -- FastAPI :$(API_PORT), Streamlit :$(PORT), React :$(FRONTEND_PORT)"
	@$(call KILL_PORT,$(FRONTEND_PORT))
	@powershell -NoProfile -Command "cd '$(CURDIR)'; \
	  Start-Process -FilePath '$(VENV_PYTHON)' -ArgumentList '-m','uvicorn','$(API_APP)','--host','0.0.0.0','--port','$(API_PORT)','--reload','--app-dir','src' -WorkingDirectory '$(CURDIR)'; \
	  Start-Process -FilePath '$(VENV_PYTHON)' -ArgumentList '-m','streamlit','run','$(STREAMLIT_APP)' -WorkingDirectory '$(CURDIR)'; \
	  Start-Process -FilePath 'cmd.exe' -WorkingDirectory '$(CURDIR)\\$(FRONTEND_DIR)' -ArgumentList '/c','$(FE_PM_DEV)'"
else
	@echo "Quick start -- FastAPI :$(API_PORT), Streamlit :$(PORT), React :$(FRONTEND_PORT)"
	@$(call KILL_PORT,$(FRONTEND_PORT))
	( $(MAKE) -s api-run ) &
	( $(MAKE) -s web ) &
	( cd $(FRONTEND_DIR) && $(FE_PM_DEV) ) &
	wait
endif
