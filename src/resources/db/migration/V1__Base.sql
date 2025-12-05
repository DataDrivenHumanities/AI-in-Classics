-- Baseline schema for Trojan Parse Project PostgreSQL database.
-- Provides core linguistic processing, model registry, feedback, and training tables.

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Core lookup tables
CREATE TABLE IF NOT EXISTS languages (
    id SERIAL PRIMARY KEY,
    code TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Documents store raw text (or externally referenced via metadata)
CREATE TABLE IF NOT EXISTS documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    language_id INT NOT NULL REFERENCES languages(id) ON DELETE CASCADE,
    source_type TEXT DEFAULT 'unknown', -- e.g. 'upload','corpus','api'
    title TEXT,
    raw_text TEXT, -- Future: move to separate storage for very large texts
    checksum BYTEA, -- MD5/SHA digest for dedup detection
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_documents_language ON documents(language_id);

-- Sentences segmented from documents
CREATE TABLE IF NOT EXISTS sentences (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    seq_num INT NOT NULL, -- order within document
    text TEXT NOT NULL,
    text_hash BYTEA, -- optional hash for dedup
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(document_id, seq_num)
);
CREATE INDEX IF NOT EXISTS idx_sentences_document ON sentences(document_id);

-- Tokens within sentences
CREATE TABLE IF NOT EXISTS tokens (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    sentence_id UUID NOT NULL REFERENCES sentences(id) ON DELETE CASCADE,
    seq_num INT NOT NULL,
    surface TEXT NOT NULL,
    normalized TEXT NOT NULL,
    char_start INT,
    char_end INT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(sentence_id, seq_num)
);
CREATE INDEX IF NOT EXISTS idx_tokens_sentence ON tokens(sentence_id);
CREATE INDEX IF NOT EXISTS idx_tokens_normalized ON tokens(normalized);

-- Lemmas canonical forms
CREATE TABLE IF NOT EXISTS lemmas (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    language_id INT NOT NULL REFERENCES languages(id) ON DELETE CASCADE,
    lemma_text TEXT NOT NULL,
    pos TEXT, -- part of speech
    gloss TEXT, -- short meaning
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(language_id, lemma_text, pos)
);
CREATE INDEX IF NOT EXISTS idx_lemmas_language ON lemmas(language_id);
CREATE INDEX IF NOT EXISTS idx_lemmas_text ON lemmas(lemma_text);

-- Morphological feature annotations (one row per token optionally linked to lemma)
CREATE TABLE IF NOT EXISTS morphological_features (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    token_id UUID NOT NULL REFERENCES tokens(id) ON DELETE CASCADE,
    lemma_id UUID REFERENCES lemmas(id) ON DELETE SET NULL,
    pos TEXT,
    tense TEXT,
    voice TEXT,
    mood TEXT,
    "case" TEXT,
    number TEXT,
    gender TEXT,
    person TEXT,
    degree TEXT,
    features_json JSONB, -- catch‑all for additional features
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_morph_token ON morphological_features(token_id);
CREATE INDEX IF NOT EXISTS idx_morph_lemma ON morphological_features(lemma_id);

-- Lemmatizer cache: fast lookup of normalized token -> lemma
CREATE TABLE IF NOT EXISTS lemma_cache (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    language_id INT NOT NULL REFERENCES languages(id) ON DELETE CASCADE,
    token_norm TEXT NOT NULL,
    lemma_text TEXT NOT NULL,
    pos TEXT,
    lemma_id UUID REFERENCES lemmas(id) ON DELETE SET NULL,
    hits INT NOT NULL DEFAULT 1,
    last_seen TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(language_id, token_norm)
);
CREATE INDEX IF NOT EXISTS idx_lemma_cache_token ON lemma_cache(token_norm);

-- Sentiment results per sentence per model
CREATE TABLE IF NOT EXISTS sentiment_results (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    sentence_id UUID NOT NULL REFERENCES sentences(id) ON DELETE CASCADE,
    model_id UUID, -- references model_registry(id) after registry load (can be NULL initially)
    sentiment_label TEXT NOT NULL,
    confidence NUMERIC(5,4),
    raw_json JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(sentence_id, model_id)
);
CREATE INDEX IF NOT EXISTS idx_sentiment_sentence ON sentiment_results(sentence_id);
CREATE INDEX IF NOT EXISTS idx_sentiment_label ON sentiment_results(sentiment_label);

-- Model registry (generalised from JSON file)
CREATE TABLE IF NOT EXISTS model_registry (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    model_key TEXT UNIQUE NOT NULL, -- e.g. 'latin_model:1.0.0'
    name TEXT NOT NULL,
    provider TEXT NOT NULL DEFAULT 'ollama',
    version TEXT,
    available BOOLEAN NOT NULL DEFAULT TRUE,
    tags TEXT[],
    metadata_json JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_model_registry_available ON model_registry(available);
CREATE INDEX IF NOT EXISTS idx_model_registry_tags ON model_registry USING GIN(tags);

-- Training jobs referencing models
CREATE TABLE IF NOT EXISTS training_jobs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    model_id UUID REFERENCES model_registry(id) ON DELETE SET NULL,
    preset_name TEXT,
    strategy TEXT,
    filters_json JSONB,
    status TEXT NOT NULL DEFAULT 'pending',
    feedback_count INT NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_training_jobs_status ON training_jobs(status);
CREATE INDEX IF NOT EXISTS idx_training_jobs_model ON training_jobs(model_id);

-- User feedback records
CREATE TABLE IF NOT EXISTS user_feedback (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    model_id UUID REFERENCES model_registry(id) ON DELETE SET NULL,
    text TEXT NOT NULL,
    got_json JSONB,
    want_json JSONB,
    notes TEXT,
    tags TEXT[],
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_feedback_model ON user_feedback(model_id);
CREATE INDEX IF NOT EXISTS idx_feedback_tags ON user_feedback USING GIN(tags);

-- Schema migrations bookkeeping for custom migrator
CREATE TABLE IF NOT EXISTS schema_migrations (
    version TEXT PRIMARY KEY,
    applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    checksum TEXT
);

-- Seed data for languages (idempotent)
INSERT INTO languages(code, name)
    VALUES ('grc', 'Ancient Greek') ON CONFLICT (code) DO NOTHING;
INSERT INTO languages(code, name)
    VALUES ('lat', 'Latin') ON CONFLICT (code) DO NOTHING;