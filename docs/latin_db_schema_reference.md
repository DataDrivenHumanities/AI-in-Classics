# Latin DB schema reference (local dev)

This repo uses **one Postgres database** (default: `lemlat_db`) with **two schemas**:

- `public` = *web-scraped dictionary/morphology layer* (human-friendly inflection labels + provenance URLs)
- `lila` = *LiLa / LEMLAT 3.0 linguistic backbone* (token → lemma analyses, POS-ish codes) + *LatinAffectus sentiment*

If you only look at one thing in `lila`, use the **views** in `src/Lemmatizer-LTN-LiLa/ops/create_lila_views.sql`:

- `lila.lemmario_clean` (trimmed lemma rows)
- `lila.analysis_clean` (trimmed analyses)
- `lila.analysis_with_lemma` (analysis rows joined to lemma metadata)

## `public` schema (scraped tables)

Created by: `src/Lemmatizer-LTN/ops/init_db.sql`  
Loaded by: `src/Lemmatizer-LTN/etl/load_to_postgres.py`

### `public.lemmas` (1 row per lemma headword)

Purpose: “dictionary lemma registry” for the scraped dataset; stable FK target for forms.

Columns (core):

- `id` `bigserial` (PK)
- `lemma_nod` `citext` (unique; **normalized** via `norm(lemma_diac)` = `unaccent(lower(...))`)
- `lemma_diac` `text` (original spelling w/ diacritics, if present)
- `pos` `text` (scraper POS label)
- `gender` `text`
- `page_url` `text` (provenance link back to the scrape source)
- `lemma_fts` `tsvector` (generated; used for full-text search)

Indexes/constraints (important):

- `UNIQUE (lemma_nod)`
- trigram + FTS indexes for lookup/search

### `public.forms` (many rows per lemma)

Purpose: the “rich morphology layer” for the scraped data (explicit tense/voice/person/case/etc columns).

Columns (core):

- `id` `bigserial` (PK)
- `lemma_id` `bigint` (FK → `public.lemmas.id`)
- `form_nod` `citext` (**normalized** via `norm(form_diac)`)
- `form_diac` `text`
- `mood`, `tense`, `voice`, `person`, `number`, `gender`, `case`, `degree`, `verb_form` (`text`, nullable)
- `page_url` `text`
- `form_fts` `tsvector` (generated)

Indexes/constraints (important):

- FK: `forms.lemma_id → lemmas.id ON DELETE CASCADE`
- `forms_unique_idx` unique index across (`lemma_id`, `form_nod`, and morph feature columns) to make reloads idempotent

### `public.norm(t text) -> text`

Used everywhere as the project-wide normalization function:

- `norm('Āmō') = 'amo'`
- allows consistent joining across sources where one side has diacritics/case differences

## `lila` schema (LEMLAT + sentiment)

Imported by: `src/Lemmatizer-LTN-LiLa/ops/import_lila_data.py`  
Schema objects created by: `src/Lemmatizer-LTN-LiLa/ops/create_lila_schema.sql`

LEMLAT brings in many tables; the ones that matter most for the pipeline are:

- `lila.analysis` = token/form → lemma analyses (fixed-width CHAR columns)
- `lila.lemmario` = lemma inventory / IDs (fixed-width CHAR columns + `upostag` fields)

### `lila.lemmario` (LEMLAT lemma inventory)

Purpose: stable lemma IDs (`id_lemma`) + lemma strings + POS-ish tags.

Columns (as imported):

- `id_lemma` `int` (PK)
- `lemma` `char(30)` (fixed width)
- `lemma_reduced` `char(30)` (often better as a join key than `lemma`)
- `codlem` `char(5)`, `codmorf` `char(3)` (LEMLAT codes used to disambiguate)
- `gen` `char(1)`, `n_id` `char(5)` (more disambiguators)
- `upostag`, `upostag_2` `varchar(10)` (coarse POS tags when present)
- `ts`, `src`

Convenience view:

- `lila.lemmario_clean` trims the fixed-width `char(...)` fields into `text` and normalizes empty `gen` to `NULL`.

### `lila.analysis` (LEMLAT analyses)

Purpose: maps a surface form (“wordform”) to one or more lemma candidates.

Columns (as imported):

- `wf_input` `char(30)` (surface form; fixed width)
- `wf_analyzed` `char(30)` (normalized/analyzed surface; fixed width)
- `lemma` `char(30)` (lemma string; fixed width)
- `codmorf` `char(3)`, `codlem` `char(5)`, `gen` `char(1)`, `n_id` `char(5)`

Convenience views:

- `lila.analysis_clean` trims fixed-width fields into `text`.
- `lila.analysis_with_lemma` left-joins `analysis_clean` to `lila.lemmario` to add `id_lemma` + `upostag` fields.

### `lila.sentiment` (LatinAffectus)

Purpose: lemma-level sentiment priors (small lexicon, ~6k rows) to inject into prompts.

Columns:

- `id` `serial` (PK)
- `lemma` `text` (lemma string as given by LatinAffectus)
- `pos` `text` (optional)
- `polarity_score` `numeric(3,1)` (e.g. `-1.0`, `0.5`)
- `has_polarity` `text` (label like `positive`/`negative`/`neutral`, if present)
- `provenance` `text`
- `created_at` `timestamptz`

Index:

- `idx_lila_sentiment_lemma` on `(lemma)`

## How the two worlds join (recommended key)

There is **no shared numeric ID** between the scraped dataset and LEMLAT; the reliable join is a **normalized lemma string**.

Recommended join key:

- `public.lemmas.lemma_nod`  ↔  `norm(lila.lemmario_clean.lemma_reduced)` (or `norm(lila.lemmario_clean.lemma)`)

Notes:

- `lila.*` strings are fixed-width `CHAR` in the raw tables; use the `*_clean` views (trimmed) before normalizing/joining.
- Lemma homographs exist; when you can, add a secondary disambiguator:
  - POS: `public.lemmas.pos` ↔ `lila.lemmario_clean.upostag` (coarse, not always present/compatible)
  - LEMLAT codes: `codlem/codmorf/gen/n_id` (strong, but scraped side usually lacks these)

## RAG prompt surface (what to “expose”)

For the compact prompt block, you typically only need:

- **Sentiment priors**: `lila.sentiment` (joined by normalized lemma)
- **Lemmatization backbone**: `lila.analysis_with_lemma` (token → lemma candidates; gives `id_lemma` and POS-ish tags)
- **Human-friendly morphology/provenance** (optional, top-K only): `public.forms` + `public.lemmas` (to add terse tense/voice/case hints + source URLs if needed)

## Quick introspection

For a compact, CREATE TABLE-style snapshot of the *relevant* tables, open:

- `docs/latin_db_describe.sql`
