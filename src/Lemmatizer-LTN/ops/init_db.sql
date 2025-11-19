-- Extensions
CREATE EXTENSION IF NOT EXISTS unaccent;
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS citext;

-- Immutable normalizer for indexes/uniques
CREATE OR REPLACE FUNCTION norm(t text) RETURNS text
LANGUAGE sql IMMUTABLE PARALLEL SAFE AS $$
  SELECT unaccent(lower(t));
$$;

-- Lemmas
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

CREATE INDEX IF NOT EXISTS lemmas_trgm_idx ON lemmas USING gin (lemma_nod gin_trgm_ops);

-- Forms
CREATE TABLE IF NOT EXISTS forms (
  id        BIGSERIAL PRIMARY KEY,
  lemma_id  BIGINT NOT NULL REFERENCES lemmas(id) ON DELETE CASCADE,
  form_nod  citext NOT NULL,
  form_diac text,
  label     text,
  mood      text,
  tense     text,
  voice     text,
  person    text,
  number    text,
  gender    text,
  "case"    text,
  degree    text,
  page_url  text
);

-- Remove any legacy context columns if they still exist
ALTER TABLE forms DROP COLUMN IF EXISTS source_context_1;
ALTER TABLE forms DROP COLUMN IF EXISTS source_context_2;
ALTER TABLE forms DROP COLUMN IF EXISTS source_context_3;

-- Helpful indexes
CREATE INDEX IF NOT EXISTS forms_lemma_id_idx ON forms(lemma_id);
CREATE INDEX IF NOT EXISTS forms_form_nod_idx ON forms(form_nod);
CREATE INDEX IF NOT EXISTS forms_form_trgm_idx ON forms USING gin (form_nod gin_trgm_ops);

-- FTS on diacritics-stripped forms/lemmas
ALTER TABLE lemmas ADD COLUMN IF NOT EXISTS lemma_fts tsvector
  GENERATED ALWAYS AS (to_tsvector('simple', unaccent(coalesce(lemma_diac,'')))) STORED;
ALTER TABLE forms  ADD COLUMN IF NOT EXISTS form_fts  tsvector
  GENERATED ALWAYS AS (to_tsvector('simple', unaccent(coalesce(form_diac ,'')))) STORED;

CREATE INDEX IF NOT EXISTS lemmas_fts_idx ON lemmas USING gin(lemma_fts);
CREATE INDEX IF NOT EXISTS forms_fts_idx  ON forms  USING gin(form_fts);

-- Idempotent unique to avoid dup forms on reloads
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_indexes
    WHERE schemaname = 'public'
      AND indexname  = 'forms_unique_idx'
  ) THEN
    EXECUTE $I$
      CREATE UNIQUE INDEX forms_unique_idx ON forms(
        lemma_id, form_nod, label, coalesce(mood,''), coalesce(tense,''), coalesce(voice,''),
        coalesce(person,''), coalesce(number,''), coalesce(gender,''), coalesce("case",''), coalesce(degree,'')
      )
    $I$;
  END IF;
END$$;

-- Convenience selectors
CREATE OR REPLACE FUNCTION get_forms_by_lemma(q text)
RETURNS SETOF forms LANGUAGE sql STABLE AS $$
  SELECT f.* FROM lemmas l
  JOIN forms f ON f.lemma_id = l.id
  WHERE l.lemma_nod = norm(q)
  ORDER BY f.mood, f.tense, f.voice, f.person, f.number, f.gender, f."case", f.degree, f.form_nod;
$$;

CREATE OR REPLACE FUNCTION get_lemma_by_form(q text)
RETURNS lemmas LANGUAGE sql STABLE AS $$
  SELECT l.* FROM forms f
  JOIN lemmas l ON l.id = f.lemma_id
  WHERE f.form_nod = norm(q)
  LIMIT 1;
$$;

CREATE OR REPLACE FUNCTION inflect_within_lemma(
  q text,
  p_mood text DEFAULT NULL, p_tense text DEFAULT NULL, p_voice text DEFAULT NULL,
  p_person text DEFAULT NULL, p_number text DEFAULT NULL, p_gender text DEFAULT NULL,
  p_case text DEFAULT NULL, p_degree text DEFAULT NULL
)
RETURNS SETOF forms LANGUAGE sql STABLE AS $$
  WITH base AS (
    SELECT l.id AS lemma_id
    FROM forms f JOIN lemmas l ON l.id = f.lemma_id
    WHERE f.form_nod = norm(q)
    LIMIT 1
  )
  SELECT f.* FROM forms f, base b
  WHERE f.lemma_id = b.lemma_id
    AND (p_mood   IS NULL OR f.mood   = p_mood)
    AND (p_tense  IS NULL OR f.tense  = p_tense)
    AND (p_voice  IS NULL OR f.voice  = p_voice)
    AND (p_person IS NULL OR f.person = p_person)
    AND (p_number IS NULL OR f.number = p_number)
    AND (p_gender IS NULL OR f.gender = p_gender)
    AND (p_case   IS NULL OR f."case" = p_case)
    AND (p_degree IS NULL OR f.degree = p_degree)
  ORDER BY f.form_nod;
$$;
