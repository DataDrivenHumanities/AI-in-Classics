## LiLa / LEMLAT local data

This folder contains local data files used to build the Latin LiLa/LEMLAT + LatinAffectus PostgreSQL database.

## Local DB setup (one Postgres DB, two schemas)

We use **one local Postgres database** (default: `lemlat_db`) with:

- `public.*` tables = web-scraped morphology/dictionary layer (`public.lemmas`, `public.forms`)
- `lila.*` tables = LiLa/LEMLAT backbone + sentiment (`lila.lemmario`, `lila.analysis`, `lila.sentiment`)

High level: bootstrap schema → import LEMLAT dump + sentiment → (optionally) load scraped CSVs.

### 0) Prereqs

- Postgres running locally
- Python venv with deps (these scripts currently use both driver APIs):
  - `psycopg2-binary` (used by `scripts/bootstrap_latin_db.py` and `src/Lemmatizer-LTN-LiLa/ops/import_lila_data.py`)
  - `psycopg` (used by `src/Lemmatizer-LTN/etl/load_to_postgres.py`)
  - `python-dotenv`, `pandas`

### 1) Create DB + set `DATABASE_URL`

```bash
createdb lemlat_db
```

Create a repo-root `.env` (not committed) with:

```bash
DATABASE_URL=postgresql://127.0.0.1/lemlat_db
```

### 2) Bootstrap schema objects (tables/functions/extensions)

Applies:

- `public` scraped schema from `src/Lemmatizer-LTN/ops/init_db.sql`
- `lila` schema objects from `src/Lemmatizer-LTN-LiLa/ops/create_lila_schema.sql` (currently just `lila.sentiment`)

```bash
./.venv/bin/python3 scripts/bootstrap_latin_db.py
```

### 3) Import LiLa/LEMLAT dump + LatinAffectus sentiment + LiLa views

1) Ensure the LEMLAT dump exists locally at `data/lila/lemlat_db.sql` (ignored by git).
2) Run:

```bash
./.venv/bin/python3 src/Lemmatizer-LTN-LiLa/ops/import_lila_data.py
```

This will:

- import the LEMLAT tables into schema `lila` (e.g. `lila.lemmario`, `lila.analysis`, …)
- (re)load sentiment from `data/lila/LatinAffectusv4.tsv` into `lila.sentiment`
- create convenience views from `src/Lemmatizer-LTN-LiLa/ops/create_lila_views.sql` (e.g. `lila.analysis_with_lemma`)

### 4) (Optional) Load the web-scraped CSV outputs into `public.*`

After scraping finishes and `src/Lemmatizer-LTN/out/` contains the per-lemma CSVs:

```bash
./.venv/bin/python3 src/Lemmatizer-LTN/etl/load_to_postgres.py \
  --outdir src/Lemmatizer-LTN/out \
  --truncate
```

Note: `--truncate` only wipes `public.forms`/`public.lemmas`. It does not touch `lila.*`.

### 5) Quick verification

```bash
psql -d lemlat_db -c "\\dt lila.*"
psql -d lemlat_db -c "select count(*) as lemlat_lemmas from lila.lemmario;"
psql -d lemlat_db -c "select count(*) as affectus from lila.sentiment;"
psql -d lemlat_db -c "select count(*) as scraped_lemmas from public.lemmas;"
psql -d lemlat_db -c "select count(*) as scraped_forms from public.forms;"
```

### 6) Quick payload smoke-test (lexicon priors)

```bash
./.venv/bin/python3 scripts/latin_lexicon_annotator_debug.py \
  --file src/sample_text/latin/rag_test_sample_1.txt \
  --payload-only --compact --top-k 10
```

### Tracked

- `LatinAffectusv4.tsv`: lemma-level sentiment lexicon. To be used for RAG pipeline for Llama Model 
    - Link Here - https://github.com/CIRCSE/Latin_Sentiment_Lexicons
### Not tracked (large / reproducible)

- `lemlat_db.sql`: the LEMLAT 3.0 SQL dump (≈40MB)
    - download here at directory root https://github.com/CIRCSE/LEMLAT3

If `lemlat_db.sql` is missing, `src/Lemmatizer-LTN-LiLa/ops/import_lila_data.py` cannot import LEMLAT.
