# Latin Lemmatizer — Technical Documentation

An end-to-end system for Latin lemmatization and morphological analysis. It:

1. Scrapes lemmas and inflection tables from an online Latin dictionary.
2. Normalizes and aggregates them into two CSVs (`lemmas.csv`, `forms.csv`).
3. Loads them into a PostgreSQL database with indexes and a `norm()` function.
4. Exposes the data through a FastAPI service (`/api/v1/...`) with Bearer-token auth.
5. Publishes the API through a Cloudflare Tunnel so researchers can query it without VPN.
6. Ships two browser UIs (lookup tool + sentence generator) that sit on top of the API.

## Table of Contents

- [Architecture](#architecture)
- [Data Flow](#data-flow)
- [Components](#components)
  - [Web Scraper](#web-scraper)
  - [ETL Pipeline](#etl-pipeline)
  - [Database Schema](#database-schema)
  - [API Service](#api-service)
  - [Web UIs](#web-uis)
  - [Python Client](#python-client)
- [Technical Details](#technical-details)
  - [Text Normalization](#text-normalization)
  - [Active / Passive Lemma Merging](#active--passive-lemma-merging)
  - [Morphological Parsing](#morphological-parsing)
  - [Full-Text & Fuzzy Search](#full-text--fuzzy-search)
  - [Performance Notes](#performance-notes)
- [Deployment (Spark + Cloudflare Tunnel)](#deployment-spark--cloudflare-tunnel)
- [Pipeline Configuration](#pipeline-configuration)
- [Development](#development)
- [Contributors](#contributors)

## Architecture

The system is an ETL pipeline feeding a live API + UI:

```
┌────────────────────────────┐
│  Online Latin Dictionary   │  (source HTML)
└────────────┬───────────────┘
             │ async HTTP (aiohttp)
             ▼
┌────────────────────────────┐
│  Scraper (tools/)          │
│  scrape_tables.py          │
│  • Follows active/passive  │
│    twin lemma links        │
│  • In-memory aggregation   │
└────────────┬───────────────┘
             │ writes
             ▼
┌────────────────────────────┐
│  out/lemmas.csv            │
│  out/forms.csv             │
└────────────┬───────────────┘
             │ load
             ▼
┌────────────────────────────┐
│  PostgreSQL                │
│  (schema: ops/init_db.sql) │
│  • norm() function         │
│  • citext, unaccent, trgm  │
│  • GIN FTS + trigram idx   │
└────────┬──────────┬────────┘
         │          │
         │          │
         ▼          ▼
┌─────────────┐  ┌─────────────────┐
│ Python      │  │ FastAPI service │
│ client      │  │ api/main.py     │
│ (latin_     │  │ + Bearer auth   │
│ lemmatizer) │  └────────┬────────┘
└─────────────┘           │
                          │ Cloudflare Quick Tunnel
                          ▼
                 ┌─────────────────┐
                 │ ui/index.html   │  Lookup tool
                 │ ui/builder.html │  Sentence generator
                 └─────────────────┘
```

## Data Flow

### 1. Extraction (scraping)

`tools/scrape_tables.py`:

- Walks paginated index pages to discover lemma codes (e.g. `AMO100`, `AMOR100`).
- Fetches each lemma page with `aiohttp` and parses with BeautifulSoup.
- Reconstructs full forms from `radice` (root) + `desinenza` (ending) spans,
  including periphrastic forms like `amatus est`.
- **Follows active/passive twin links** on verb pages and merges the forms from
  both pages under a single canonical lemma. Each form still carries an explicit
  `voice` tag (`active` / `passive` / `deponent` / `middle`).
- Records invariable words (`et`, `semper`, …) with empty morphology rather than
  dropping them.
- Respects the source by adding jittered delays and exponential backoff on
  `429 Too Many Requests`.
- Aggregates all scraped rows **in memory** and writes the two final CSVs
  directly to `out/lemmas.csv` and `out/forms.csv`. The old per-lemma-CSV stage
  has been removed for speed and disk-usage reasons.

### 2. Transformation

Shared helpers live in two files:

- `etl/aggregate_out_to_csvs.py` — normalization regexes, form/ending combining,
  `norm()`-equivalent Python function, verb-form detection, number/voice/tense
  detection. The scraper imports these directly.
- `etl/latin_norm.py` — canonical abbreviation maps (e.g. `NOM.` → `nominative`,
  `SING.` → `singular`, `ACTIVE DIATHESIS` → `active`) and a `normalize_morph()`
  helper used when re-processing raw rows.

Canonical morphological values used throughout the system:

| Feature      | Allowed values |
| ------------ | -------------- |
| Mood         | `indicative`, `subjunctive`, `imperative` |
| Tense        | `present`, `imperfect`, `future`, `perfect`, `pluperfect`, `future perfect` |
| Voice        | `active`, `passive`, `deponent`, `middle` |
| Person       | `first`, `second`, `third` |
| Number       | `singular`, `plural` |
| Gender       | `masculine`, `feminine`, `neuter` |
| Case         | `nominative`, `genitive`, `dative`, `accusative`, `ablative`, `vocative`, `locative` |
| Degree       | `positive`, `comparative`, `superlative` |
| Verb form    | `infinitive`, `participle`, `gerund`, `gerundive`, `supine` |

Every word also carries both:

- A **display** form (`lemma_diac`, `form_diac`) with macrons/breves preserved.
- A **normalized** form (`lemma_nod`, `form_nod`) stripped of diacritics and
  non-alphanumerics, for lookups.

### 3. Loading

`etl/load_aggregates_to_postgres.py`:

1. Reads `lemmas.csv` and `forms.csv`.
2. Applies `ops/init_db.sql` (idempotent).
3. Optionally truncates `forms` and `lemmas`.
4. Loads lemmas in batches of 1000 using `INSERT ... SELECT FROM (VALUES …)`
   with `ON CONFLICT (lemma_nod) DO UPDATE`. `lemma_nod` is computed in the DB
   by the `norm()` function so Python and SQL stay in sync.
5. Builds an in-memory cache of `lemma_nod → id`.
6. Loads forms in batches of 1000 against the same pattern, with
   `ON CONFLICT DO NOTHING` against the composite `forms_unique_idx`.

A simpler legacy path (`etl/load_to_postgres.py`) still exists for quick local
reloads from a single CSV pair.

## Components

### Web Scraper

**File:** `tools/scrape_tables.py`

Responsibilities:

- Discover lemma codes from index pages.
- Fetch and parse each lemma page.
- Rebuild forms from `radice` + `desinenza` spans.
- Merge paired active/passive lemmas under one entry.
- Aggregate results in memory and emit two CSVs.

Key helpers:

- `parse_index_for_lemmas()`
- `flatten_ff_value()` — reconstructs periphrastic forms.
- `scrape_lemma()` — scrapes one lemma page.
- `main()` — async orchestrator with configurable concurrency, backoff, and
  optional "testing" mode limiting to the first N index pages.

Output: `out/lemmas.csv`, `out/forms.csv`.

### ETL Pipeline

```
etl/
├── aggregate_out_to_csvs.py   # Shared normalization + legacy aggregator
├── latin_norm.py              # Abbreviation maps + normalize_morph()
├── load_aggregates_to_postgres.py  # Main DB loader
├── load_to_postgres.py        # Simpler single-pass loader
├── run_pipeline.py            # OS-agnostic phase runner used by Azure Pipelines
├── run_init_and_load.py       # Apply schema + load in one call
├── upload_to_drive.py         # Push lemmas.csv/forms.csv to Google Drive
├── upload_tree_to_drive.py    # Upload a directory tree to Drive
├── download_from_drive.py     # Pull CSVs back from Drive before DB load
├── aggregate_by_letter.py     # Optional per-letter CSV split (a.csv, b.csv…)
└── requirements.txt
```

### Database Schema

**File:** `ops/init_db.sql`

Extensions:

- `unaccent` — accent-insensitive matching.
- `pg_trgm` — trigram similarity for fuzzy search.
- `citext` — case-insensitive text columns.

Core function (keeps Python and SQL normalization in lockstep):

```sql
CREATE OR REPLACE FUNCTION norm(t text) RETURNS text
LANGUAGE sql IMMUTABLE PARALLEL SAFE AS $$
  SELECT regexp_replace(unaccent(lower(t)), '[^a-z0-9]+', '', 'g');
$$;
```

Tables:

`lemmas`
- `id BIGSERIAL PK`
- `lemma_code text` — original source id (e.g. `AMO100`, `AMOR100`)
- `lemma_nod citext UNIQUE NOT NULL` — normalized headword (indexed)
- `lemma_diac text` — headword with macrons/breves
- `pos text`, `gender text`, `page_url text`, `created_at timestamptz`
- `lemma_fts tsvector` — generated FTS column

`forms`
- `id BIGSERIAL PK`
- `lemma_id BIGINT REFERENCES lemmas(id) ON DELETE CASCADE`
- `form_nod citext NOT NULL`, `form_diac text`
- Morphological columns: `mood`, `tense`, `voice`, `person`, `number`, `gender`,
  `"case"`, `degree`, `verb_form`
- `page_url text`, `form_fts tsvector`

Indexes:

- `lemmas_trgm_idx` — GIN trigram on `lemma_nod`
- `forms_form_nod_idx` — B-tree on `form_nod`
- `forms_form_trgm_idx` — GIN trigram on `form_nod`
- `lemmas_fts_idx`, `forms_fts_idx` — GIN full-text
- `forms_lemma_id_idx` — B-tree FK lookup
- `forms_unique_idx` — composite unique over `(lemma_id, form_nod, mood, tense, voice, person, number, gender, case, degree, verb_form)`

Stored helpers:

- `get_forms_by_lemma(q)`
- `get_lemma_by_form(q)`
- `inflect_within_lemma(q, p_mood, p_tense, …)` — single-call inflection with
  optional morphological filters.

### API Service

**Location:** `api/`

- `main.py` — FastAPI app, CORS, lifespan-managed `psycopg_pool.ConnectionPool`,
  loads `.env` from the project root.
- `auth.py` — Bearer-token auth. Valid tokens come from the comma-separated
  `API_TOKENS` environment variable.
- `db.py` — connection pool helpers plus all SQL (`get_lemmas`, `get_forms`,
  `random_forms`, `random_lemmas`, `batch_forms`, `health_check`).
- `routes.py` — HTTP route handlers under the `/api/v1` prefix.
- `models.py` — Pydantic request/response models.

Endpoints:

| Method | Path | Purpose |
| ------ | ---- | ------- |
| `GET`  | `/api/v1/health` | DB + app liveness (no auth) |
| `GET`  | `/api/v1/lemma/{word}` | Look up lemmas matching a word (lemma or form). Returns `lemma_code`, `pos`, `gender`, `lemma_diathesis` (active / passive / unknown), etc. |
| `GET`  | `/api/v1/forms` | Inflected forms for a given `lemma` or `form`, with optional morphological filters |
| `GET`  | `/api/v1/forms/random` | `n` random forms matching morphological filters; no lemma needed. Extras: `exclude_proper`, `allow_nonfinite`, `rarity_mode` (`common` / `balanced` / `all`). Useful for training-data sampling |
| `GET`  | `/api/v1/random-lemmas` | `n` random lemmas, optionally filtered by POS substring |
| `POST` | `/api/v1/forms/batch` | Resolve up to 500 `lemma`-based form queries in one request |

All non-`/health` endpoints require `Authorization: Bearer <token>`.

### Web UIs

Both UIs are zero-dependency single-page apps. They talk to the API via the
user-supplied URL + Bearer token, saved in `localStorage`.

**`ui/index.html` — Lookup tool**

- Three modes: *Look up Lemmas*, *Forms (by lemma)*, *Forms (by form)*.
- Dropdowns for all nine morphological features (mood, tense, voice, person,
  number, gender, case, degree, verb form).
- Lemma results show `lemma_diathesis` (active / passive) so you can tell
  `amo` from `amor` when both are returned.
- Clickable lemma rows auto-query forms for that lemma.
- Forms results offer a **Grouped** view (person × number or case × number
  tables, split by voice/mood/tense) and a **Table** view with sortable headers.
- Light/dark theme, deep-linkable URL hashes, CSV export.

**`ui/builder.html` — Sentence generator**

- Generates up to 5000 random Latin sentences by picking words from
  `GET /api/v1/forms/random` pools per slot.
- Presets are grouped into *Core Patterns*, *Extended Patterns*, and
  *Advanced Tense/Mode* — SVO, SV, SVIO, `Nom + Dat + Acc + et + Acc + V`,
  predicate adjectives, ablative of means, perfect/subjunctive/future/imperfect
  SVO variants, etc.
- Each slot carries quality hints: `excludeProper`, `allowNonfinite`, and a
  `rarityMode` (common / balanced / all) that map straight to the API.
- Fixed tokens (`et`, `est`, …) are supported in presets for conjunctions and
  copulas.
- Output table shows one column per slot with the resolved form, lemma, and
  diathesis, plus an expandable Details row with full metadata per word.
- CSV / JSON export includes `lemma_code` and `lemma_diathesis` for every word,
  which is the payload intended for training downstream AI models.

### Python Client

**Location:** `latin_lemmatizer/`

Originally a direct-to-Postgres client; still shipped so researchers running on
the same machine as the DB can skip the HTTP layer.

```python
from latin_lemmatizer import get_lemma, get_form, LatinLemmatizer

lemma = get_lemma("amavi")               # → lemma row dict
forms = get_form(lemma="amo", tense="present")
forms = get_form(form="amavi", number="plural")

with LatinLemmatizer(dsn="...") as client:
    client.get_lemma("amo")
```

A client that wraps the HTTP API (so notebooks can use the tunnel URL instead
of a DSN) also lives in this package and is the recommended entrypoint now.
See `latin_lemmatizer/README.md` and `examples/basic_usage.ipynb`.

## Technical Details

### Text Normalization

Two-tier approach, used everywhere:

- `*_diac` columns preserve the original Unicode, including macrons and breves,
  for display.
- `*_nod` columns store a normalized form: NFD-decomposed, lowercased, with all
  non-alphanumerics stripped. This is what lookups match against.

The Python `norm()` in `etl/aggregate_out_to_csvs.py` and the SQL `norm()` in
`ops/init_db.sql` are kept strictly in sync so a row inserted via CSV lines up
with a query from the API.

### Active / Passive Lemma Merging

The source dictionary lists active and passive voices of the same verb as two
separate lemma codes (e.g. `AMO100` for *amo* and `AMOR100` for *amor*). The
scraper now:

1. Detects the paired passive link on each active verb page (and vice versa).
2. Fetches both pages.
3. Merges their forms under one canonical lemma entry, with each form tagged
   `voice=active` or `voice=passive`.

At the API layer, `/api/v1/lemma/{word}` and `/api/v1/forms/random` derive a
`lemma_diathesis` label:

- `lemma_code` ending in `OR[0-9]+` → `passive`
- `lemma_code` ending in `O[0-9]+`  → `active`
- POS text containing `passive` / `active` as a fallback
- otherwise `unknown`

The lookup UI renders this as a tag next to each lemma result.

### Morphological Parsing

`etl/latin_norm.py` plus regex helpers in `etl/aggregate_out_to_csvs.py` handle:

- Abbreviation expansion (`NOM. SING. MASC.` → `nominative / singular / masculine`).
- Italian source headings (`PARTICIPIO`, `GERUNDIO`, `SUPIN`, `FUTURO`) mapped
  to English equivalents.
- Voice resolution with a three-level fallback: explicit voice hint from the
  scraper → heading heuristics → VOICE_MAP text match. Inferred passive voice
  from characteristic participial endings is only applied when context is
  silent.
- Context-aware number/case/tense detection (closest heading wins).

### Full-Text & Fuzzy Search

- Generated `tsvector` columns (`simple` config, language-agnostic) feed GIN
  FTS indexes on both `lemmas` and `forms`.
- `pg_trgm` GIN indexes on `lemma_nod` / `form_nod` power fuzzy similarity
  lookups (`%` operator and `similarity()`).

Example:

```sql
-- Full-text match
SELECT * FROM lemmas WHERE lemma_fts @@ to_tsquery('simple', 'amo');

-- Trigram fuzzy match
SELECT * FROM lemmas
WHERE lemma_nod % 'amo'
ORDER BY similarity(lemma_nod, 'amo') DESC;
```

### Performance Notes

- Scraping runs async with bounded concurrency and jittered backoff so the
  source site isn't hammered.
- The loader batches at 1000 rows with `ON CONFLICT` upserts and computes
  `*_nod` inside the DB, avoiding double normalization.
- `norm()` is declared `IMMUTABLE PARALLEL SAFE`, so PostgreSQL can use it in
  generated columns, unique indexes, and query planner optimizations.
- The API uses a `psycopg_pool.ConnectionPool` initialized in the FastAPI
  lifespan, so every request reuses a warm connection.
- `forms_unique_idx` as a composite unique across every morphological axis
  prevents duplicate rows across re-runs.

## Deployment (Spark + Cloudflare Tunnel)

The API runs on the shared Spark machine and is exposed to researchers via a
Cloudflare Quick Tunnel — no VPN, no DNS setup.

Outline:

1. PostgreSQL runs on Spark and is already loaded by the ETL pipeline.
2. The API server is launched as a background `uvicorn` process:

   ```bash
   cd /data/AI-in-Classics/src/Lemmatizer-LTN
   source .venv/bin/activate
   export $(grep -v '^#' .env | xargs)       # DATABASE_URL + API_TOKENS
   nohup uvicorn api.main:app \
     --host 127.0.0.1 --port 8000 \
     > api/out/api.log 2>&1 &
   disown
   ```

3. `cloudflared` (single binary, installed once on the box) is started against
   the local port:

   ```bash
   nohup cloudflared tunnel --url http://127.0.0.1:8000 \
     > api/out/cloudflared.log 2>&1 &
   disown
   ```

4. The tunnel prints a `https://<slug>.trycloudflare.com` URL. Researchers
   paste that URL and their Bearer token into the UIs or into the notebook in
   `examples/basic_usage.ipynb`.

When Spark or `cloudflared` restarts, the Quick Tunnel slug rotates; the
`localStorage`-backed UIs make swapping URLs trivial. For a long-lived
deployment the next step is a named tunnel + custom hostname + Cloudflare
Access policy — all already supported by the same `cloudflared` binary.

## Pipeline Configuration

**File:** `azure-pipelines.yml`

Three run modes, selectable via the `pipelineMode` parameter:

1. **Full E2E Pipeline** (default): scrape → upload to Drive → load Postgres.
2. **Scrape + Upload to Drive**: skip DB load.
3. **Upload to Database**: skip scraping; download the CSVs from Google Drive
   and load Postgres.

A `testing` boolean limits scraping to the first handful of index pages for
quick iteration. All phases go through `etl/run_pipeline.py` so each phase
shows up as its own Azure step.

## Development

### Project Structure

```
Lemmatizer-LTN/
├── README.md
├── tools/
│   └── scrape_tables.py
├── etl/
│   ├── aggregate_out_to_csvs.py
│   ├── aggregate_by_letter.py
│   ├── latin_norm.py
│   ├── load_aggregates_to_postgres.py
│   ├── load_to_postgres.py
│   ├── run_pipeline.py
│   ├── run_init_and_load.py
│   ├── upload_to_drive.py
│   ├── upload_tree_to_drive.py
│   ├── download_from_drive.py
│   └── requirements.txt
├── ops/
│   └── init_db.sql
├── api/
│   ├── main.py
│   ├── routes.py
│   ├── db.py
│   ├── auth.py
│   └── models.py
├── ui/
│   ├── index.html        # Lookup tool
│   └── builder.html      # Sentence generator
├── latin_lemmatizer/
│   ├── client.py
│   ├── setup.py
│   └── README.md
├── examples/
│   ├── basic_usage.ipynb
│   └── sentence_templates_test.ipynb
└── out/                  # Generated CSVs (gitignored)
```

### Dependencies

ETL pipeline (`etl/requirements.txt`):

- `aiohttp` — async HTTP for the scraper
- `beautifulsoup4` — HTML parsing
- `psycopg[binary]` and `psycopg2-binary` — Postgres drivers
- `google-api-python-client`, `google-auth` — Drive upload/download

API service:

- `fastapi`, `uvicorn`
- `psycopg[binary]`, `psycopg_pool`
- `python-dotenv`, `pydantic`

UIs: plain HTML / CSS / JavaScript, no build step.

### Environment Variables

- `DATABASE_URL` — PostgreSQL DSN (used by the loader, the Python client, and
  the API).
- `API_TOKENS` — comma-separated Bearer tokens accepted by the API.
- `GOOGLE_SERVICE_ACCOUNT_JSON_BASE64` — base64-encoded service-account JSON
  for Drive upload/download in the Azure pipeline.

### Running Locally

```bash
# 1. Scrape + aggregate (in-memory) into out/lemmas.csv and out/forms.csv
python tools/scrape_tables.py --outdir out/ --concurrency 8

# 2. Load into Postgres (applies schema, truncates, bulk inserts)
python etl/load_aggregates_to_postgres.py --outdir out/ --truncate

# 3. Start the API
uvicorn api.main:app --host 127.0.0.1 --port 8000

# 4. Open ui/index.html or ui/builder.html in a browser,
#    paste the API URL + a valid token, and query.
```

### Testing

- `examples/basic_usage.ipynb` — end-to-end client demo against the live API.
- `examples/sentence_templates_test.ipynb` — runs a set of master sentence
  templates through the lemmatizer to sanity-check coverage.
- The Azure pipeline has a `testing: true` flag to limit scraping for quick
  iteration.

## Contributors

Aidan Burrowes & Abraham Stefanos
