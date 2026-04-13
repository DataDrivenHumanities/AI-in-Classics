# Latin Lemmatizer - Technical Documentation

A comprehensive ETL pipeline and query system for Latin lemmatization and morphological analysis. This system scrapes Latin dictionary data from online sources, normalizes and processes it, stores it in PostgreSQL with full-text search capabilities, and provides a Python client for querying lemmas and inflected forms.

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Data Flow](#data-flow)
- [Components](#components)
  - [Web Scraper](#web-scraper)
  - [ETL Pipeline](#etl-pipeline)
  - [Database Schema](#database-schema)
  - [Query Client](#query-client)
- [Technical Details](#technical-details)
  - [Text Normalization](#text-normalization)
  - [Morphological Parsing](#morphological-parsing)
  - [Full-Text Search](#full-text-search)
  - [Performance Optimizations](#performance-optimizations)
- [Pipeline Configuration](#pipeline-configuration)
- [Development](#development)

## Overview

The Latin Lemmatizer system extracts, transforms, and loads (ETL) Latin dictionary data from [online-latin-dictionary.com](https://www.online-latin-dictionary.com), processes morphological information, and stores it in a PostgreSQL database optimized for fast lookups and full-text search.

**Key Features:**

- **Web Scraping**: Asynchronous scraping of lemma pages and inflection tables
- **Morphological Analysis**: Automatic extraction and normalization of grammatical features (mood, tense, voice, person, number, gender, case, degree, verb forms)
- **Text Normalization**: Unicode-aware normalization for diacritics and accents
- **Full-Text Search**: PostgreSQL GIN indexes with trigram matching for fuzzy search
- **Query API**: Python client with convenience functions for lemma and form lookups
- **CI/CD Integration**: Azure Pipelines for automated scraping and database updates

## Architecture

The system follows a modular ETL architecture:

```
┌─────────────────┐
│  Web Scraper    │  (tools/scrape_tables.py)
│  (Async HTTP)   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Per-Lemma CSVs │  (out/*.csv)
│  (Raw Data)     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Aggregation    │  (etl/aggregate_out_to_csvs.py)
│  & Normalization│
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Aggregate CSVs │  (out/lemmas.csv, forms.csv)
│  (Processed)    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  PostgreSQL DB  │  (ops/init_db.sql)
│  (Optimized)    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Query Client   │  (latin_lemmatizer/client.py)
│  (Python API)   │
└─────────────────┘
```

## Data Flow

### 1. Extraction (Scraping)

The scraper (`tools/scrape_tables.py`) performs asynchronous HTTP requests to extract data:

1. **Index Discovery**: Scrapes paginated index pages to discover lemma codes
2. **Lemma Pages**: Fetches individual lemma pages containing inflection tables
3. **HTML Parsing**: Uses BeautifulSoup to extract:
   - Lemma text (with diacritics)
   - Part of speech and grammatical information
   - Inflection tables with morphological labels
   - Form reconstruction from roots (`radice`) and endings (`desinenza`)

**Key Technical Details:**

- **Async I/O**: Uses `aiohttp` for concurrent requests (configurable concurrency)
- **Rate Limiting**: Random delays between requests to respect server resources
- **Error Handling**: Retries with exponential backoff for transient failures
- **Form Reconstruction**: Handles complex cases like periphrastic forms (e.g., "abalienatus sum") by combining roots with comma-separated endings and suffixes

### 2. Transformation (ETL)

The ETL pipeline processes raw scraped data:

1. **Aggregation** (`etl/aggregate_out_to_csvs.py`):

   - Combines per-lemma CSVs into unified `lemmas.csv` and `forms.csv`
   - Handles dash-prefixed endings (e.g., "–a, –um") by combining with base forms
   - Extracts lemma codes from URLs
   - Detects verb forms (infinitive, participle, gerund, gerundive, supine)

2. **Normalization** (`etl/latin_norm.py`):

   - Normalizes morphological labels to canonical values:
     - Mood: `indicative`, `subjunctive`, `imperative`
     - Tense: `present`, `imperfect`, `future`, `perfect`, `pluperfect`, `future perfect`
     - Voice: `active`, `passive`, `deponent`, `middle`
     - Person: `first`, `second`, `third`
     - Number: `singular`, `plural`
     - Gender: `masculine`, `feminine`, `neuter`
     - Case: `nominative`, `genitive`, `dative`, `accusative`, `ablative`, `vocative`, `locative`
     - Degree: `positive`, `comparative`, `superlative`
     - Verb Forms: `infinitive`, `participle`, `gerund`, `gerundive`, `supine`
   - Extracts voice hints from lemma headings
   - Handles abbreviations and variations in source data

3. **Text Processing**:
   - Strips accents for normalization (`lemma_nod`, `form_nod`)
   - Preserves diacritics for display (`lemma_diac`, `form_diac`)
   - Cleans lemma text (removes "Active/Passive diathesis" suffixes)

### 3. Loading (Database)

The loader (`etl/load_aggregates_to_postgres.py`) efficiently bulk-loads data:

* Add flag --recreate to load_aggregates_to_postgres to drop existing tables and regenerate completely.
1. **Schema Initialization** (`ops/init_db.sql`):

   - Creates `lemmas` and `forms` tables with foreign key relationships
   - Sets up PostgreSQL extensions:
     - `unaccent`: For accent-insensitive normalization
     - `pg_trgm`: For trigram-based fuzzy matching
     - `citext`: For case-insensitive text columns
   - Creates indexes:
     - GIN indexes for trigram matching (`gin_trgm_ops`)
     - GIN indexes for full-text search (`tsvector`)
     - B-tree indexes for foreign keys and lookups
   - Defines `norm()` function for consistent normalization

2. **Bulk Loading**:
   - Uses `psycopg.sql.execute_values()` for efficient batch inserts (1000 rows per transaction)
   - Computes `lemma_nod` and `form_nod` in-database using `norm()` function
   - Handles NULL values and empty strings with `NULLIF`
   - Enforces uniqueness via composite unique index on forms

## Components

### Web Scraper

**File**: `tools/scrape_tables.py`

**Responsibilities:**

- Discover lemma codes from index pages
- Fetch lemma pages and inflection tables
- Parse HTML to extract forms and morphological data
- Reconstruct complete forms from roots and endings
- Write per-lemma CSV files

**Key Functions:**

- `parse_index_for_lemmas()`: Extracts lemma codes from index pages
- `flatten_ff_value()`: Reconstructs forms from HTML structure (handles complex cases like periphrastic forms)
- `scrape_lemma()`: Main scraping function for individual lemmas
- `main()`: Orchestrates async scraping with configurable concurrency

**Output**: Per-lemma CSV files in `out/` directory

### ETL Pipeline

**Files**:

- `etl/aggregate_out_to_csvs.py`: Aggregates per-lemma CSVs
- `etl/latin_norm.py`: Normalizes morphological features
- `etl/load_aggregates_to_postgres.py`: Loads data into PostgreSQL

**Aggregation Process:**

1. Discovers all per-lemma CSVs (excludes aggregate files)
2. Extracts lemma metadata (code, text, POS, gender, URL)
3. Processes forms with context-aware splitting for dash-prefixed endings
4. Detects verb forms (infinitive, participle, etc.)
5. Writes unified `lemmas.csv` and `forms.csv`

**Loading Process:**

1. Truncates tables (optional, for fresh loads)
2. Reads aggregate CSVs using `csv.reader` (index-based access for reliability)
3. Batch inserts using `execute_values()` (1000 rows per batch)
4. Computes normalized fields in-database using `norm()` function

### Database Schema

**File**: `ops/init_db.sql`

**Tables:**

#### `lemmas`

Stores dictionary headwords:

- `id`: Primary key (BIGSERIAL)
- `lemma_code`: Source lemma code (from URL)
- `lemma_nod`: Normalized lemma (no diacritics, lowercase) - **indexed for lookups**
- `lemma_diac`: Lemma with diacritics (for display)
- `pos`: Part of speech
- `gender`: Gender (if applicable)
- `page_url`: Source URL
- `lemma_fts`: Generated full-text search vector (GIN indexed)

#### `forms`

Stores inflected forms:

- `id`: Primary key (BIGSERIAL)
- `lemma_id`: Foreign key to `lemmas(id)`
- `form_nod`: Normalized form (no diacritics, lowercase) - **indexed for lookups**
- `form_diac`: Form with diacritics (for display)
- Morphological fields: `mood`, `tense`, `voice`, `person`, `number`, `gender`, `case`, `degree`, `verb_form`
- `page_url`: Source URL
- `form_fts`: Generated full-text search vector (GIN indexed)

**Indexes:**

- `lemmas_trgm_idx`: GIN trigram index on `lemma_nod` (fuzzy matching)
- `forms_form_trgm_idx`: GIN trigram index on `form_nod` (fuzzy matching)
- `lemmas_fts_idx`: GIN index on `lemma_fts` (full-text search)
- `forms_fts_idx`: GIN index on `form_fts` (full-text search)
- `forms_unique_idx`: Composite unique index to prevent duplicates
- B-tree indexes on foreign keys and commonly queried fields

**Functions:**

- `norm(text)`: Immutable normalization function (strips accents, lowercases)
- `get_forms_by_lemma(q)`: Convenience function for form lookups
- `get_lemma_by_form(q)`: Convenience function for lemma lookups
- `inflect_within_lemma(q, ...)`: Inflection function with filters

### Query Client

**File**: `latin_lemmatizer/client.py`

**Class**: `LatinLemmatizer`

**Key Features:**

- Singleton pattern for default client instance
- Automatic `.env` file loading (via `python-dotenv`)
- Connection pooling and transaction error recovery
- Dynamic SQL query building (avoids `IndeterminateDatatype` errors)

**API:**

```python
# Convenience functions (use default client)
get_lemma(word: str) -> Optional[Dict]
get_form(lemma=None, form=None, mood=None, tense=None, ...) -> List[Dict]

# Client class (explicit control)
client = LatinLemmatizer(dsn="...")
lemma = client.get_lemma("amo")
forms = client.get_form(lemma="amo", tense="present")
```

**Query Optimization:**

- Dynamically builds WHERE clauses (only includes non-None parameters)
- Uses `norm()` function for case-insensitive, accent-insensitive matching
- Leverages GIN indexes for fast lookups
- Handles transaction errors with automatic rollback and recovery

## Technical Details

### Text Normalization

The system uses a two-tier normalization approach:

1. **Display Text** (`lemma_diac`, `form_diac`):

   - Preserves all Unicode characters and diacritics
   - Used for human-readable output

2. **Normalized Text** (`lemma_nod`, `form_nod`):
   - Strips accents using Unicode NFD decomposition
   - Converts to lowercase
   - Used for lookups and matching

**Implementation:**

```sql
CREATE FUNCTION norm(t text) RETURNS text
LANGUAGE sql IMMUTABLE PARALLEL SAFE AS $$
  SELECT unaccent(lower(t));
$$;
```

This function is:

- **IMMUTABLE**: Can be used in indexes and computed columns
- **PARALLEL SAFE**: Can be used in parallel queries
- **Indexed**: Used in unique constraints and lookup indexes

### Morphological Parsing

The normalization system (`etl/latin_norm.py`) handles:

1. **Abbreviation Mapping**: Converts abbreviations (e.g., "NOM." → "nominative")
2. **Case Variations**: Handles both abbreviated and full forms
3. **Voice Detection**: Extracts voice from lemma headings and morphological labels
4. **Verb Form Detection**: Identifies infinitive, participle, gerund, gerundive, supine
5. **Context-Aware Parsing**: Uses multiple fields to disambiguate features

**Example Normalization:**

```
Source: "NOM. SING. MASC."
→ case: "nominative"
→ number: "singular"
→ gender: "masculine"
```

### Full-Text Search

PostgreSQL full-text search is configured for both lemmas and forms:

1. **Generated Columns**: `lemma_fts` and `form_fts` are automatically generated
2. **Text Search Configuration**: Uses `simple` configuration (no stemming, language-agnostic)
3. **GIN Indexes**: Fast lookups on `tsvector` columns
4. **Trigram Matching**: Additional GIN indexes for fuzzy matching with `pg_trgm`

**Usage:**

```sql
-- Full-text search
SELECT * FROM lemmas WHERE lemma_fts @@ to_tsquery('simple', 'amo');

-- Trigram fuzzy matching
SELECT * FROM lemmas WHERE lemma_nod % 'amo' ORDER BY similarity(lemma_nod, 'amo') DESC;
```

### Performance Optimizations

1. **Batch Inserts**: Uses `execute_values()` for 1000-row batches (vs. individual INSERTs)
2. **Index Strategy**:
   - GIN indexes for text search (fast lookups, slower writes)
   - B-tree indexes for foreign keys and exact matches
   - Composite unique index prevents duplicate inserts
3. **Connection Management**: Singleton client with connection reuse
4. **Query Building**: Dynamic WHERE clauses avoid unnecessary parameter passing
5. **Normalization**: Immutable `norm()` function enables index usage

## Pipeline Configuration

**File**: `azure-pipelines.yml`

The Azure DevOps pipeline supports three modes:

1. **Full E2E Pipeline** (default):

   - Scrapes data from web
   - Aggregates CSVs
   - Uploads to Google Drive
   - Loads into PostgreSQL

2. **Scrape + Upload to Drive**:

   - Scrapes and aggregates
   - Uploads to Google Drive only
   - Skips database loading

3. **Upload to Database**:
   - Downloads CSVs from Google Drive
   - Loads into PostgreSQL
   - Skips scraping

**Pipeline Steps:**

1. Python environment setup (3.11.9)
2. Virtual environment and dependencies
3. Google Service Account authentication
4. Scraping (conditional)
5. CSV aggregation (conditional)
6. Upload to Google Drive (conditional)
7. Download from Google Drive (conditional)
8. Database initialization
9. Database loading (conditional)

**Configuration:**

- Testing mode: Limits scraping to first 10 pages
- Concurrency: Configurable async workers for scraping
- Retry logic: Exponential backoff for transient failures
- Error handling: ASCII-safe output for Windows PowerShell

## Development

### Project Structure

```
Lemmatizer-LTN/
├── tools/
│   └── scrape_tables.py          # Web scraper
├── etl/
│   ├── aggregate_out_to_csvs.py  # CSV aggregation
│   ├── latin_norm.py             # Morphological normalization
│   ├── load_aggregates_to_postgres.py  # Database loader
│   ├── download_from_drive.py    # Google Drive downloader
│   └── requirements.txt           # Python dependencies
├── ops/
│   └── init_db.sql               # Database schema
├── latin_lemmatizer/
│   ├── client.py                 # Query client
│   ├── setup.py                  # Package configuration
│   └── README.md                 # User-facing documentation
├── examples/
│   └── basic_usage.ipynb         # Usage examples
└── out/                          # Output directory (CSVs)
```

### Dependencies

**ETL Pipeline:**

- `aiohttp`: Async HTTP client for scraping
- `beautifulsoup4`: HTML parsing
- `psycopg[binary]`: PostgreSQL adapter
- `google-api-python-client`: Google Drive API

**Query Client:**

- `psycopg[binary]`: PostgreSQL adapter
- `python-dotenv`: Environment variable loading

### Environment Variables

- `DATABASE_URL`: PostgreSQL connection string (required for client)
- `GOOGLE_SERVICE_ACCOUNT_JSON_BASE64`: Base64-encoded Google service account JSON (for pipeline)

### Running Locally

This pipeline expects a Postgres database with the schema in `ops/init_db.sql`.

1) Set `DATABASE_URL` (recommended: repo-root `.env`, not committed):

```bash
DATABASE_URL=postgresql://127.0.0.1/lemlat_db
```

2) Get the scrape outputs (recommended: download from Drive)

- Download `out.zip` from the shared Google Drive.
- Unzip it into `src/Lemmatizer-LTN/` so you end up with `src/Lemmatizer-LTN/out/*.csv`

Example:

```bash
unzip out.zip -d src/Lemmatizer-LTN
```

3) Load into Postgres:

```bash
./.venv/bin/python3 src/Lemmatizer-LTN/etl/load_to_postgres.py \
  --outdir src/Lemmatizer-LTN/out \
  --truncate
```

Optional: scrape yourself instead of using Drive (slower; produces the same raw CSV shape):

```bash
./.venv/bin/python3 src/Lemmatizer-LTN/tools/scrape_tables.py \
  --outdir src/Lemmatizer-LTN/out \
  --dynamic
```

**Query Client:**

```python
from latin_lemmatizer import get_lemma, get_form

lemma = get_lemma("amo")
forms = get_form(lemma="amo", tense="present")
```

### Testing

The pipeline supports a "testing" mode that limits scraping to the first 10 pages for quick iteration:

```yaml
parameters:
  - name: testing
    type: boolean
    default: false
```

When enabled, the scraper only processes pages 1-10, significantly reducing runtime for development and testing.

---

## Contributors

Aidan Burrowes & Abraham Stefanos
