## LiLa / LEMLAT local data

data/lila/ contains local data files used to build the Latin LiLa/LEMLAT + LatinAffectus PostgreSQL database.

## Local DB setup (one Postgres DB, two schemas)

We use **one local Postgres database** (default: `lemlat_db`) with:

- `public.*` tables = web-scraped morphology/dictionary layer (`public.lemmas`, `public.forms`) + derived tables (`public.lemma_sentiment_map`, `public.word_lookup`)
- `lila.*` tables = LiLa/LEMLAT backbone + sentiment (`lila.lemmario`, `lila.analysis`, `lila.sentiment`)

High level: bootstrap schema → import LEMLAT dump + sentiment → (optionally) load scraped CSVs → build cross-schema lookup tables.

### 0) Prereqs

- Postgres running locally
- Python venv with deps (these scripts currently use both driver APIs):
  - `psycopg2-binary` (used by `scripts/bootstrap_latin_db.py` and `src/Lemmatizer-LTN-LiLa/ops/import_lila_data.py`)
  - `psycopg` (used by `src/Lemmatizer-LTN/etl/load_to_postgres.py`)
  - `python-dotenv`, `pandas`

```
#setup user and password
sudo -u postgres createuser --superuser root
sudo -u postgres psql -c "\password root"
```

or on windows

```
psql -U postgres -c "CREATE USER root WITH SUPERUSER PASSWORD 'yourpassword';"
```

### 1) Create DB + set `DATABASE_URL`

```bash
uv run scripts/download_lemlat.py
```

```bash
createdb -U root -W lemlat_db
```

Create a repo-root `.env` (not committed) with:

```bash
DATABASE_URL=postgresql://root:yourpassword@127.0.0.1/lemlat_db
```

### 2) Bootstrap schema objects (tables/functions/extensions)

Applies:

- `public` scraped schema from `src/Lemmatizer-LTN/ops/init_db.sql`
- `lila` schema objects from `src/Lemmatizer-LTN-LiLa/ops/create_lila_schema.sql` (currently just `lila.sentiment`)

```bash
uv run scripts/bootstrap_latin_db.py
```

### 3) Import LiLa/LEMLAT dump + LatinAffectus sentiment + LiLa views

1. Ensure the LEMLAT dump exists locally at `data/lila/lemlat_db.sql` (ignored by git).
2. Run:

```bash
uv run src/Lemmatizer-LTN-LiLa/ops/import_lila_data.py
```

This will:

- import the LEMLAT tables into schema `lila` (e.g. `lila.lemmario`, `lila.analysis`, …)
- (re)load sentiment from `data/lila/LatinAffectusv4.tsv` into `lila.sentiment`
- create convenience views from `src/Lemmatizer-LTN-LiLa/ops/create_lila_views.sql` (e.g. `lila.analysis_with_lemma`)

### 4) (Optional) Load the web-scraped CSV outputs into `public.*`

After scraping finishes and `src/Lemmatizer-LTN/out/` contains the per-lemma CSVs:

```bash
uv run src/Lemmatizer-LTN/etl/load_to_postgres.py --outdir src/Lemmatizer-LTN/out --truncate

```

Note: `--truncate` only wipes `public.forms`/`public.lemmas`. It does not touch `lila.*`.

### 5) Build `public.lemma_sentiment_map` + `public.word_lookup`

Requires both `lila.sentiment` (step 3) and `public.lemmas`/`public.forms` (step 4).

The single script creates two tables in order:

1. **`lemma_sentiment_map`** – joins sentiment entries against the dictionary
   tables so each sentiment lemma is mapped to its dictionary lemma ID
   (via direct lemma match or inflected-form fallback).
2. **`word_lookup`** – unified lookup of every known word-form: all rows from
   `public.forms` plus unmatched sentiment lemmas (those with `match = FALSE`
   in `lemma_sentiment_map`).

```bash
uv run src/Lemmatizer-LTN-LiLa/ops/load_lemma_sentiment_map.py
```

The script is idempotent -- re-running drops and recreates both tables.

### 6) Backfill English definitions (recommended for Lexicon Highlight popups)

The Lexicon Highlight UI shows a definition popup when `public.lemmas.definition` is populated.

Fast path (fills definitions for **sentiment-mapped** dictionary lemmas first):

```bash
uv run src/Lemmatizer-LTN/tools/scrape_definitions.py --only-sentiment --limit 6000
```

Broader backfill (all lemmas; slower):

```bash
uv run src/Lemmatizer-LTN/tools/scrape_definitions.py --limit 100000
```

### 7) Quick verification

```bash
psql -U root -d lemlat_db -c "\dt lila.*"
psql -U root -d lemlat_db -c "select count(*) as lemlat_lemmas from lila.lemmario;"
psql -U root -d lemlat_db -c "select count(*) as affectus from lila.sentiment;"
psql -U root -d lemlat_db -c "select count(*) as scraped_lemmas from public.lemmas;"
psql -U root -d lemlat_db -c "select count(*) as scraped_forms from public.forms;"
psql -U root -d lemlat_db -c "select count(*) as sentiment_map from public.lemma_sentiment_map;"
psql -U root -d lemlat_db -c "select count(*) as word_lookup from public.word_lookup;"
```

### 8) Quick payload smoke-test (lexicon priors)

```bash
uv run scripts/latin_lexicon_annotator_debug.py --file src/sample_text/latin/rag_test_sample_1.txt --payload-only --compact --top-k 10
```

### Tracked

- `LatinAffectusv4.tsv`: lemma-level sentiment lexicon. To be used for RAG pipeline for Llama Model
  - Link Here - https://github.com/CIRCSE/Latin_Sentiment_Lexicons

### Not tracked (large / reproducible)

- `lemlat_db.sql`: the LEMLAT 3.0 SQL dump (≈40MB)
  - download here at directory root https://github.com/CIRCSE/LEMLAT3

If `lemlat_db.sql` is missing, `src/Lemmatizer-LTN-LiLa/ops/import_lila_data.py` cannot import LEMLAT.
