# Development Guide

Pick **one** setup path: **Poetry**, **plain Python (venv)**, or **Docker**.  
Then (optionally) build the **Ollama** models for sentiment tests.

> We recommend **Poetry** or **Docker** for the smoothest experience.

---

## Prerequisites

- **Python 3.10+**
  - If you want to use **Poetry**, this repo’s `pyproject.toml` currently requires **Python <3.12**.
- **Make** (macOS/Linux preinstalled; Windows: download [here](https://sourceforge.net/projects/gnuwin32/files/make/3.81/make-3.81.exe/download?use_mirror=cytranet-dal&download) or `choco install make` or use WSL)
- **Ollama** (for local LLM): <https://ollama.com/download>
- **Docker** (optional): <https://docs.docker.com/get-docker/>

---
## 1. Quick Start
### 1a. Quick Start (Poetry)

```bash
# from repo root
make setup          # uses Poetry if compatible; otherwise falls back to venv + requirements.txt
make web            # runs Streamlit app (default: src/app/server_streamlit.py)
```

### Tests, formatting

```bash
make test           # pytest
make check          # black --check
make fix            # black (format)
```

---

### 1b. Quick Start (Python venv)

If you don't use Poetry:

```bash
make setup-venv     # creates .venv and installs requirements.txt (if present)
make web            # runs Streamlit
# or
make run
```

> If you don't have a `requirements.txt`, either generate one from Poetry (`poetry export -f requirements.txt --output requirements.txt`) or switch to the Poetry path.

---

### 1c. Quick Start (Docker)

```bash
make docker-build
make docker-dev     # mounts repo for live reload, exposes port (default 8501)
# or
make docker-run     # simple run of the built image
```

Common maintenance:

```bash
make docker-clean   # remove dangling containers/images
```

---

## 2. Ollama Models (Latin & Greek Sentiment)

These steps build light wrappers on top of a base model (default **llama3.1:8b**).

### 2.1 Start the Ollama server

```bash
ollama serve
```

Keep this terminal open (or run it as a service).

### 2.2 Pull the base model

```bash
make ollama-pull
# equivalent to: ollama pull llama3.1:8b
```

### Build our project models

Your repo should have:

```bash
models/
  latin/
    Modelfile
  greek/
    Modelfile
```

> If your repo instead uses `models/latin_model/Modelfile` and `models/greek_model/Modelfile`, either rename to `latin/` and `greek/`, **or** update the Makefile paths accordingly.

Build:
(linux only req apt install jq -y)
```bash
make build-latin
make build-greek
```

Verify:

```bash
make ollama-list
# should list:
# latin_model:1.0.0
# greek_model:1.0.0
# llama3.1:8b
```

### Health check & smoke tests

```bash
make health         # checks /api/tags
make smoke-latin    # one-shot classify request
make smoke-greek
```

If the smoke test returns an `error` or 404, your model tag probably doesn’t exist (see Troubleshooting).

---

## Running the Sentiment Test Suites

Latin:

```bash
make ensure-models  # verifies both tags exist
make test-latin     # or: poetry run python tests/Latin_Sentiment_Sentences_Test_Cases.py
```

Greek (if you have the parallel harness):

```bash
make test-greek
```

---

## Make Targets (Cheat Sheet)

Core:
- `make setup` — Prefer Poetry; otherwise uses `.venv`
- `make setup-venv` — Create and populate a Python virtualenv (legacy)
- `make run` — Runs `APP_ENTRY` (default `src/app/server_streamlit.py`)
- `make web` — Runs Streamlit app (`STREAMLIT_APP`, default `src/app/server_streamlit.py`)
- `make start` — Start local dev server with hot-reload (convenience task; may run `make web` or a watcher)
- `make start-lite` — Lightweight start (no model build, minimal services) for quick dev/testing
- `make test` — Run `pytest`
- `make check` — `black --check` (style checks)
- `make fix` — Run `black` to format code

Docker:
- `make docker-build` — Build the development image
- `make docker-run` — Run the built image
- `make docker-dev` — Run container with repo mounted for live reload (exposes port, default 8501)
- `make docker-bash` — Get a shell in the dev container
- `make docker-clean` — Remove dangling containers/images

Ollama / Models:
- `make ollama-serve` — Run Ollama server (foreground)
- `make ollama-pull` — Pull base model (e.g., `llama3.1:8b`)
- `make ollama-list` — List tags from Ollama server
- `make build-latin` — Build `latin` model tag from `models/latin/Modelfile`
- `make build-greek` — Build `greek` model tag from `models/greek/Modelfile`
- `make ensure-models` — Verify required model tags exist on Ollama
- `make smoke-latin` / `make smoke-greek` — Quick one-shot classify requests to validate models
- `make health` — Check Ollama `/api/tags` (200 OK expected)

Misc / Tests:
- `make test-latin` — Run Latin sentiment test suite
- `make test-greek` — Run Greek sentiment test suite (if present)
- `make lint` — Run linters (if defined)
- `make deps` — Show or install dependency info (if defined)

Notes:
- `make start` / `make start-lite` behavior may be project-specific; inspect the `Makefile` for exact commands and adjust environment variables (`PORT`, `OLLAMA_HOST`, `LATIN_TAG`, `GREEK_TAG`, etc.) as needed.
- For Streamlit entry override use the `STREAMLIT_APP` env var (default `src/app/app.py`).

Config via env vars:

```bash
# defaults shown
OLLAMA_HOST=http://localhost:11434
LATIN_TAG=latin_model:1.0.0
GREEK_TAG=greek_model:1.0.0
BASE_MODEL=llama3.1:8b
PORT=8501
APP_ENTRY=src/app/server_streamlit.py
STREAMLIT_APP=src/app/server_streamlit.py
```

---

## (Optional) Legacy build script

If you still want a local build script:

```bash
sh .build.sh
cd src/app
python3 app.py
```

> Note: the old docs had a typo (`.buld.sh`). Make sure your script is actually named `.build.sh`.

---

## Model Folder Layout (Suggested)

```bash
models/
  latin/
    Modelfile
    prompts/ (optional)
    weights/ (optional)
  greek/
    Modelfile
    prompts/ (optional)
    weights/ (optional)
```

If you prefer `latin_model/` and `greek_model/`, update the Makefile targets:

```make
build-latin:
 ollama create $(LATIN_TAG) -f models/latin_model/Modelfile

build-greek:
 ollama create $(GREEK_TAG) -f models/greek_model/Modelfile
```

---

## Common Issues & Fixes

### Ollama 404 on `/api/generate`

- Usually means **model tag not found**. Run `ollama list` and ensure your code/Makefile use the exact tag (e.g., `latin_model:1.0.0`).

#### `{"error":"model 'X' not found"}`

- You didn’t build the model: run `make build-latin` / `make build-greek`.
- Wrong folder path in Makefile: adjust `-f models/.../Modelfile`.

### Server not reachable

- `ollama serve` must be running. Check with `make health` or:

  ```bash
  curl -s http://localhost:11434/api/tags
  ```

### Inconsistent outputs (extra text)

- Keep temperature at 0 in Model files and enforce a one-word response in prompts.
- Normalize in the test harness (`clean_sentiment()`).

### Missing Python deps

- Poetry: `make setup` (or `poetry install`)
- venv: ensure `requirements.txt` exists, then `make setup-venv`

### Graphviz / Altair errors (Streamlit visuals)

- macOS: `brew install graphviz`
- Ubuntu/Debian: `sudo apt-get update && sudo apt-get install -y graphviz`
- Altair v4: `poetry add "altair<5,>=4.2"`

---

## Releasing a new model version

1. Edit `models/<latin|greek>/Modelfile`
2. Build a new tag:

   ```bash
   ollama create latin_model:1.0.1 -f models/latin/Modelfile
   ```

3. Update `LATIN_TAG`/`GREEK_TAG` in your Makefile or environment.
4. `make ensure-models && make test-latin`
