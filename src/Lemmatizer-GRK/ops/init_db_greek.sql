-- Extensions for search and normalization
CREATE EXTENSION IF NOT EXISTS unaccent;
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS citext;

-- Immutable normalizer for indexes/expressions
CREATE OR REPLACE FUNCTION norm(t text) RETURNS text
LANGUAGE sql IMMUTABLE PARALLEL SAFE AS $$
  SELECT unaccent(lower(t));
$$;

-- 1. Lemmas Table
CREATE TABLE IF NOT EXISTS lemmas (
  id          BIGSERIAL PRIMARY KEY,
  lemma_code  TEXT,
  lemma_nod   CITEXT NOT NULL,
  lemma_diac  TEXT,
  english_definition TEXT,
  pos         TEXT,
  gender      TEXT,
  page_url    TEXT,
  created_at  TIMESTAMPTZ DEFAULT now(),
  UNIQUE (lemma_nod)
);

CREATE INDEX IF NOT EXISTS lemmas_trgm_idx ON lemmas USING gin (lemma_nod gin_trgm_ops);

-- 2. Forms Table
CREATE TABLE IF NOT EXISTS forms (
  id          BIGSERIAL PRIMARY KEY,
  lemma_id    BIGINT NOT NULL REFERENCES lemmas(id) ON DELETE CASCADE,
  form_nod    CITEXT NOT NULL,
  form_diac   TEXT,
  mood        TEXT,
  tense       TEXT,
  voice       TEXT,
  person      TEXT,
  number      TEXT,
  gender      TEXT,
  "case"      TEXT,
  degree      TEXT,
  verb_form   TEXT,
  page_url    TEXT
);

-- Helpful indexes
CREATE INDEX IF NOT EXISTS forms_lemma_id_idx ON forms(lemma_id);
CREATE INDEX IF NOT EXISTS forms_form_nod_idx ON forms(form_nod);
CREATE INDEX IF NOT EXISTS forms_form_trgm_idx ON forms USING gin (form_nod gin_trgm_ops);

-- 3. Full Text Search (FTS) Columns
ALTER TABLE lemmas ADD COLUMN IF NOT EXISTS lemma_fts tsvector
  GENERATED ALWAYS AS (to_tsvector('simple', norm(coalesce(lemma_diac,'')))) STORED;

ALTER TABLE forms  ADD COLUMN IF NOT EXISTS form_fts tsvector
  GENERATED ALWAYS AS (to_tsvector('simple', norm(coalesce(form_diac ,'')))) STORED;

CREATE INDEX IF NOT EXISTS lemmas_fts_idx ON lemmas USING gin(lemma_fts);
CREATE INDEX IF NOT EXISTS forms_fts_idx  ON forms  USING gin(form_fts);

-- 4. Uniqueness to avoid duplicate forms on reloads
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_indexes
    WHERE schemaname = 'public' AND indexname = 'forms_unique_idx'
  ) THEN
    EXECUTE $I$
      CREATE UNIQUE INDEX forms_unique_idx ON forms(
        lemma_id, form_nod,
        coalesce(mood,''), coalesce(tense,''), coalesce(voice,''),
        coalesce(person,''), coalesce(number,''), coalesce(gender,''),
        coalesce("case",''), coalesce(degree,''), coalesce(verb_form,'')
      )
    $I$;
  END IF;
END$$;