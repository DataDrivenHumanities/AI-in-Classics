# Ollama setup (local LLM)

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

## Pull the base model

```bash
ollama pull llama3.1:8b-instruct
```

## Build this repo’s models (Modelfiles)

From repo root:

```bash
make build-latin LATIN_TAG=latin_model:1.0.0
make build-greek GREEK_TAG=greek_model:1.0.0
```

### Verify tags exist

```bash
ollama list
# expect lines like:
# latin_model:1.0.0
# greek_model:1.0.0
# llama3.1:8b-instruct
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
./.venv/bin/python3 -m pytest -q tests/test_latin_sentiment.py
```

## RAG payload smoke-test (lexicon priors → prompt injection)

```bash
./.venv/bin/python3 scripts/latin_lexicon_annotator_debug.py \
  --file src/sample_text/latin/rag_test_sample_1.txt \
  --payload-only --compact --top-k 10
```
