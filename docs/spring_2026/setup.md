## INSTALL UV

https://docs.astral.sh/uv/getting-started/installation/

### INSTALL BREW

[Homebrew — The Missing Package Manager for macOS (or Linux)](https://brew.sh/)

```
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

```
brew install uv
uv python install 3.12
```

or on windows

```
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### Create Env

```
# create venv
uv venv .venv --python 3.12
```

### Install python deps

```
uv sync
```

### build jupyter lite

```
uv run python -m jupyter lite build --output-dir src/frontend/public/jlite --force
```

## Setup Ollama

### install

```
brew install ollama
```

or on windows

```

irm https://ollama.com/install.ps1 | iex
```

### pull

```
ollama pull llama3.1:8b
ollama pull gemma4:e4b

ollama create latin_model:1.0.0 -f models/latin_model/Modelfile
ollama create greek_model:1.0.0 -f models/greek_model/Modelfile
ollama create latin-sentiment-llama31-5class -f ./models/rag_v31_5classes/Modelfile.fiveclasses

```

### serve

```

ollama serve

```

### Setup BERT

```

uv run src/latin_bert/_0_download.py

```

### install frontend deps

```

cd src/frontend
npm install
cd ../..

```

## CLEAR PORTS

```

fuser -k 5050/tcp; fuser -k 8501/tcp; fuser -k 3000/tcp

rm -rf /root/stanza_resources
ln -s /root/.cache/stanza/1.11.0/resources /root/stanza_resources

```

or on windows

```

for /f "tokens=5" %a in ('netstat -aon ^| findstr ":5050 :8501 :3000"') do taskkill /F /PID %a

```

## POSTGRES SETUP

```

brew install postgresql@17

```

or for windows

```

winget install -e --id PostgreSQL.PostgreSQL.17
setx PATH "%PATH%;C:\Program Files\PostgreSQL\17\bin"

```

Then follow these comands

[LILA_SETUP](lila_setup)

## Start servers (run each in a separate terminal)

```
uv run --env-file run.env uvicorn app.server_fast:app --host 0.0.0.0 --port 5050 --reload --app-dir src

```

```

cd src/frontend
npm run dev -- -p 3000

```

# Sample sentence for ui - postive

```

Caelum pulchrum est.

```
