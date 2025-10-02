# Ollama Full Setup

## Prerequisites

- macOS, Windows or linux

- Installed Ollama: <https://ollama.com/download>

- 8-10 GB free disk space

- Python

## Start the Ollama server

```bash
ollama serve
```

Default REST API: http://localhost:11434

## Build model

```bash
ollama create greek_model:1.0.0 -f models/greek/Modelfile
```

### Verify tags exist

```bash
ollama list
# expect lines like:
# latin_model:1.0.0
# greek_model:1.0.0
```

### Smoke-test api

```bash
# Latin
curl -s http://localhost:11434/api/generate \
  -d '{"model":"latin_model:1.0.0","prompt":"Classify: Caelum pulchrum est.","stream":false}'

# Greek (example)
curl -s http://localhost:11434/api/generate \
  -d '{"model":"greek_model:1.0.0","prompt":"Classify: ἀγαθὸς ἀνήρ.","stream":false}'
```

## Run Current latin Test

```bash
python tests/Latin_Sentiment_Sentences_Test_Cases.py
```
