-- LiLa / LatinAffectus schema objects (safe to run on an empty DB)

CREATE SCHEMA IF NOT EXISTS lila;

-- LatinAffectus sentiment lexicon
CREATE TABLE IF NOT EXISTS lila.sentiment (
    id SERIAL PRIMARY KEY,
    lemma TEXT NOT NULL,
    pos TEXT,
    polarity_score NUMERIC(3, 1), -- supports e.g., -1.0, 0.5
    has_polarity TEXT, -- 'positive', 'negative', 'neutral'
    provenance TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_lila_sentiment_lemma ON lila.sentiment(lemma);

