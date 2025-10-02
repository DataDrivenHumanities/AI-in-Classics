# Development Guide

Pick **one** setup path: **Poetry**, **plain Python (venv)**, or **Docker**.  
Then (optionally) build the **Ollama** models for sentiment tests.

> We recommend **Poetry** or **Docker** for the smoothest experience.

---

## Prerequisites

- **Python 3.10+**
- **Make** (macOS/Linux preinstalled; Windows: `choco install make` or use WSL)
- **Ollama** (for local LLM): <https://ollama.com/download>
- **Docker** (optional): <https://docs.docker.com/get-docker/>

---

## Quick Start (Poetry)

```bash
# from repo root
make setup          # installs deps via Poetry (auto-detects)
make web            # runs Streamlit app (src/app/app.py)
# or
make run            # runs python src/app/app.py
```

### Tests, formatting

```bash
make test           # pytest
make check          # black --check
make fix            # black (format)
```

---

## uick Start (Plain Python venv)

If you don't use Poetry:

```bash
make setup-venn     # creates .venv and installs requirements.txt (if present)
make web            # runs Streamlit
# or
make run
```

> If you don't have a `requirements.txt`, either generate one from Poetry (`poetry export -f requirements.txt --output requirements.txt`) or switch to the Poetry path.

---

## Quick Start (Docker)

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

## 4) Ollama Models (Latin & Greek Sentiment)

These steps build light wrappers on top of a base model (default **llama3.1:8b**).

### 4.1 Start the Ollama server

```bash
ollama serve
```

Keep this terminal open (or run it as a service).

### 4.2 Pull the base model

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
- `make run` — Runs `src/app/app.py`
- `make web` — Runs Streamlit app
- `make test` / `make check` / `make fix`

Docker:

- `make docker-build` / `make docker-run` / `make docker-dev` / `make docker-bash` / `make docker-clean`

Ollama:

- `make ollama-serve` — Foreground server
- `make ollama-pull` — Pull base (`llama3.1:8b`)
- `make build-latin` / `make build-greek` — Create project model tags
- `make ensure-models` — Verify tags are present on server
- `make smoke-latin` / `make smoke-greek`
- `make health` — 200 OK from `/api/tags`
- `make ollama-list`

Config via env vars:

```bash
# defaults shown
OLLAMA_HOST=http://localhost:11434
LATIN_TAG=latin_model:1.0.0
GREEK_TAG=greek_model:1.0.0
BASE_MODEL=llama3.1:8b
PORT=8501
APP_ENTRY=src/app/app.py
STREAMLIT_APP=src/app/app.py
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

- Keep temperature at 0 in Modelfiles and enforce a one-word response in prompts.
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
