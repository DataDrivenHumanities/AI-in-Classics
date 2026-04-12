-- Relevant tables for the lemmatizer + RAG pipeline.
-- This file is intended to be *read* as a compact schema reference (not applied directly).

CREATE TABLE public.lemmas (
  id         bigserial PRIMARY KEY, -- stable lemma ID (FK target for `public.forms.lemma_id`)
  lemma_code text, -- optional scrape-source identifier (derived from `page_url` when present)
  lemma_nod  citext NOT NULL, -- normalized lemma key (`norm(lemma_diac)`); primary join key across datasets
  lemma_diac text, -- scraped lemma spelling (human-readable; may include diacritics)
  pos        text, -- coarse POS from scraped source (light disambiguation / optional prompt hint)
  gender     text, -- coarse gender from scraped source (optional prompt hint)
  page_url   text, -- provenance URL (audit/debug; not injected by default)
  created_at timestamptz DEFAULT now(), -- load timestamp (debugging / freshness checks)
  lemma_fts  tsvector GENERATED ALWAYS AS (to_tsvector('simple', norm(coalesce(lemma_diac,'')))) STORED, -- local search helper (not prompt text)
  UNIQUE (lemma_nod)
);

CREATE TABLE public.forms (
  id        bigserial PRIMARY KEY, -- stable form row ID
  lemma_id  bigint NOT NULL REFERENCES public.lemmas(id) ON DELETE CASCADE, -- lemma this form belongs to
  form_nod  citext NOT NULL, -- normalized surface form key (`norm(form_diac)`); useful for token lookup
  form_diac text, -- scraped surface form (human-readable; may include diacritics)
  mood      text, -- morphology features (mood/tense/voice/person/number/gender/case/degree/verb_form); include sparingly in prompts
  tense     text,
  voice     text,
  person    text,
  number    text,
  gender    text,
  "case"    text,
  degree    text,
  verb_form text,
  page_url  text, -- provenance URL for this specific row (audit/debug; not injected by default)
  form_fts  tsvector GENERATED ALWAYS AS (to_tsvector('simple', norm(coalesce(form_diac,'')))) STORED -- local search helper (not prompt text)
);

CREATE TABLE lila.lemmario (
  id_lemma      integer PRIMARY KEY, -- stable LEMLAT lemma ID (backbone identifier)
  lemma         char(30) NOT NULL, -- lemma string (fixed-width; prefer `lila.lemmario_clean` for trimmed text)
  codlem        char(5)  NOT NULL, -- disambiguation codes (used with analysis to resolve homographs)
  gen           char(1)  NOT NULL,
  codmorf       char(3)  NOT NULL,
  n_id          char(5)  NOT NULL,
  lemma_reduced char(30) NOT NULL, -- often a better join target than `lemma` (fixed-width; see `lila.lemmario_clean`)
  upostag       varchar(10), -- coarse POS tag when present (optional disambiguation / prompt hint)
  upostag_2     varchar(10), -- secondary POS tag when present
  ts            timestamp NOT NULL,
  src           char(1) NOT NULL,
  UNIQUE (lemma, codlem, gen, codmorf, n_id)
);

CREATE TABLE lila.analysis (
  wf_input    char(30) NOT NULL, -- surface wordform (token) to lemmatize (fixed-width; prefer `lila.analysis_clean`)
  wf_analyzed char(30) NOT NULL, -- analyzed/normalized wordform (debugging/token normalization)
  lemma       char(30) NOT NULL, -- lemma candidate string (fixed-width; resolved via disambiguation codes)
  codmorf     char(3)  NOT NULL, -- disambiguation codes that map analysis → `lila.lemmario` (and its `id_lemma`/POS tags)
  codlem      char(5)  NOT NULL,
  gen         char(1)  NOT NULL,
  n_id        char(5)  NOT NULL
);

CREATE TABLE lila.sentiment (
  id             serial PRIMARY KEY,
  lemma          text NOT NULL, -- lemma key in LatinAffectus; join by normalized lemma string (`norm(...)` on both sides)
  pos            text, -- optional POS label in the lexicon (can help disambiguate)
  polarity_score numeric(3,1), -- sentiment prior to inject into the prompt (e.g. -1.0..+1.0)
  has_polarity   text, -- optional categorical label (fallback/bucketing)
  provenance     text, -- traceability (not injected by default)
  created_at     timestamptz DEFAULT now()
);
