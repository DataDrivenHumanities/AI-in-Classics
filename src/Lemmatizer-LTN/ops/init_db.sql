-- ops/init_db.sql

-- Required extensions
CREATE EXTENSION IF NOT EXISTS unaccent;
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS citext;

-- Normalizer used by queries/loader (NOT used in indexes)
-- unaccent() isn't immutable, so keep this function STABLE.
CREATE OR REPLACE FUNCTION norm(t text)
RETURNS text
LANGUAGE sql
STABLE
PARALLEL SAFE
RETURNS NULL ON NULL INPUT
AS $$
  SELECT unaccent(lower(t));
$$;

-- -----------------------------------------------------------------------------
-- Text Search configuration that pipes tokens through unaccent
-- (so indexes can use to_tsvector('public.simple_unaccent', ...) which IS immutable)
-- -----------------------------------------------------------------------------
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_ts_config WHERE cfgname = 'simple_unaccent') THEN
    CREATE TEXT SEARCH CONFIGURATION public.simple_unaccent ( COPY = pg_catalog.simple );
    ALTER TEXT SEARCH CONFIGURATION public.simple_unaccent
      ALTER MAPPING FOR hword, hword_part, word WITH unaccent, simple;
  END IF;
END$$;

-- -----------------------------------------------------------------------------
-- Tables
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS lemmas (
  id          BIGSERIAL PRIMARY KEY,
  lemma_code  text,
  lemma_nod   citext NOT NULL,
  lemma_diac  text,
  pos         text,
  gender      text,
  page_url    text,
  created_at  timestamptz DEFAULT now(),
  UNIQUE (lemma_nod)
);

-- trigram on citext needs cast to text
CREATE INDEX IF NOT EXISTS lemmas_trgm_idx
  ON lemmas USING gin ((lemma_nod::text) gin_trgm_ops);

CREATE TABLE IF NOT EXISTS forms (
  id                BIGSERIAL PRIMARY KEY,
  lemma_id          BIGINT NOT NULL REFERENCES lemmas(id) ON DELETE CASCADE,
  form_nod          citext NOT NULL,
  form_diac         text,
  label             text,
  mood              text,
  tense             text,
  voice             text,
  person            text,
  number            text,
  gender            text,
  "case"            text,
  degree            text,
  source_context_1  text,
  source_context_2  text,
  source_context_3  text,
  page_url          text
);

CREATE INDEX IF NOT EXISTS forms_lemma_id_idx ON forms(lemma_id);
CREATE INDEX IF NOT EXISTS forms_form_nod_idx ON forms(form_nod);
CREATE INDEX IF NOT EXISTS forms_form_trgm_idx
  ON forms USING gin ((form_nod::text) gin_trgm_ops);

-- -----------------------------------------------------------------------------
-- Full-text search (IMMUTABLE expressions)
-- Use the custom config instead of calling unaccent() directly
-- -----------------------------------------------------------------------------
-- Option A: expression indexes (simple & robust)
CREATE INDEX IF NOT EXISTS lemmas_fts_idx
  ON lemmas USING gin (to_tsvector('public.simple_unaccent', coalesce(lemma_diac, '')));

CREATE INDEX IF NOT EXISTS forms_fts_idx
  ON forms  USING gin (to_tsvector('public.simple_unaccent', coalesce(form_diac,  '')));

-- (Optional) If you prefer generated columns, these also work because the expression is immutable:
-- ALTER TABLE lemmas ADD COLUMN IF NOT EXISTS lemma_fts tsvector
--   GENERATED ALWAYS AS (to_tsvector('public.simple_unaccent', coalesce(lemma_diac,''))) STORED;
-- CREATE INDEX IF NOT EXISTS lemmas_fts_gc_idx ON lemmas USING gin(lemma_fts);
-- ALTER TABLE forms  ADD COLUMN IF NOT EXISTS form_fts  tsvector
--   GENERATED ALWAYS AS (to_tsvector('public.simple_unaccent', coalesce(form_diac,''))) STORED;
-- CREATE INDEX IF NOT EXISTS forms_fts_gc_idx  ON forms  USING gin(form_fts);

-- -----------------------------------------------------------------------------
-- Helper functions (unchanged semantics)
-- -----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION get_forms_by_lemma(q text)
RETURNS SETOF forms
LANGUAGE sql
STABLE
AS $$
  SELECT f.*
  FROM   lemmas l
  JOIN   forms  f ON f.lemma_id = l.id
  WHERE  l.lemma_nod = norm(q)
  ORDER  BY f.mood, f.tense, f.voice, f.person, f.number, f.gender, f."case", f.degree, f.form_nod;
$$;

CREATE OR REPLACE FUNCTION get_lemma_by_form(q text)
RETURNS lemmas
LANGUAGE sql
STABLE
AS $$
  SELECT l.*
  FROM   forms  f
  JOIN   lemmas l ON l.id = f.lemma_id
  WHERE  f.form_nod = norm(q)
  LIMIT  1;
$$;

CREATE OR REPLACE FUNCTION inflect_within_lemma(
  q text,
  p_mood   text DEFAULT NULL, p_tense  text DEFAULT NULL, p_voice  text DEFAULT NULL,
  p_person text DEFAULT NULL, p_number text DEFAULT NULL, p_gender text DEFAULT NULL,
  p_case   text DEFAULT NULL, p_degree text DEFAULT NULL
)
RETURNS SETOF forms
LANGUAGE sql
STABLE
AS $$
  WITH base AS (
    SELECT l.id AS lemma_id
    FROM   forms f
    JOIN   lemmas l ON l.id = f.lemma_id
    WHERE  f.form_nod = norm(q)
    LIMIT  1
  )
  SELECT f.*
  FROM   forms f
  JOIN   base  b ON f.lemma_id = b.lemma_id
  WHERE  (p_mood   IS NULL OR f.mood   = p_mood)
     AND (p_tense  IS NULL OR f.tense  = p_tense)
     AND (p_voice  IS NULL OR f.voice  = p_voice)
     AND (p_person IS NULL OR f.person = p_person)
     AND (p_number IS NULL OR f.number = p_number)
     AND (p_gender IS NULL OR f.gender = p_gender)
     AND (p_case   IS NULL OR f."case" = p_case)
     AND (p_degree IS NULL OR f.degree = p_degree)
  ORDER  BY f.form_nod;
$$;
