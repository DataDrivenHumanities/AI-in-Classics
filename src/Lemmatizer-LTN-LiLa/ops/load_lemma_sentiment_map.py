"""
Materialise two derived public tables:

  1. `public.lemma_sentiment_map` – joins lila.sentiment against the
     public lemmas/forms tables.
  2. `public.word_lookup` – unified lookup of all known word-forms
     (dictionary forms + unmatched sentiment lemmas).

Prerequisites (all described in data/lila/README.md):
  - LEMLAT dump imported into `lila.*`
  - LatinAffectus sentiment loaded into `lila.sentiment`
  - Scraped dictionary data loaded into `public.lemmas` / `public.forms`

Usage:
    python src/Lemmatizer-LTN-LiLa/ops/load_lemma_sentiment_map.py
"""

import os
import sys
from pathlib import Path

import psycopg2
from dotenv import load_dotenv

# Env
env_path = Path(".env")
if not env_path.exists():
    for parent in Path.cwd().parents:
        if (parent / ".env").exists():
            env_path = parent / ".env"
            break
load_dotenv(env_path)

SENTIMENT_MAP_TABLE = "public.lemma_sentiment_map"
WORD_LOOKUP_TABLE = "public.word_lookup"

SENTIMENT_MAP_QUERY = """\
SELECT DISTINCT
    s.id            AS sentiment_id,
    s.lemma         AS sentiment_lemma,
    s.pos,
    s.polarity_score,
    s.has_polarity,
    CASE
        WHEN l.id IS NOT NULL OR f.lemma_id IS NOT NULL THEN TRUE
        ELSE FALSE
    END AS match,
    COALESCE(l.id, f.lemma_id)              AS dictionary_lemma_id,
    COALESCE(l.lemma_nod, l_final.lemma_nod) AS dictionary_lemma,
    CASE
        WHEN l.id IS NOT NULL        THEN 'Direct Lemma'
        WHEN f.lemma_id IS NOT NULL  THEN 'Inflected Form'
        ELSE 'No Match'
    END AS match_source
FROM lila.sentiment s
LEFT JOIN lemmas l
    ON s.lemma = l.lemma_nod
LEFT JOIN forms f
    ON s.lemma = f.form_nod AND l.id IS NULL
LEFT JOIN lemmas l_final
    ON f.lemma_id = l_final.id
"""

WORD_LOOKUP_QUERY = """\
SELECT
    id AS form_id,
    lemma_id,
    form_nod,
    NULL::INT AS sentiment_lemma_id,
    number,
    gender,
    "case"
FROM forms

UNION ALL

SELECT
    NULL AS form_id,
    NULL::INT AS lemma_id,
    sentiment_lemma AS form_nod,
    sentiment_id AS sentiment_lemma_id,
    NULL AS number,
    NULL AS gender,
    NULL AS "case"
FROM lemma_sentiment_map
WHERE match = FALSE
"""


def get_dsn() -> str:
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        print("DATABASE_URL not set.")
        return "postgresql://postgres:password@127.0.0.1:5432/lemmatizer"
    return dsn


def _create_table(conn, table: str, query: str) -> int:
    """Drop-and-recreate a table from a SELECT query. Returns row count."""
    with conn.cursor() as cur:
        cur.execute(f"DROP TABLE IF EXISTS {table};")
        cur.execute(f"CREATE TABLE {table} AS\n{query};")
        cur.execute(f"SELECT COUNT(*) FROM {table};")
        count = cur.fetchone()[0]
    conn.commit()
    return count


def load_lemma_sentiment_map(conn) -> int:
    return _create_table(conn, SENTIMENT_MAP_TABLE, SENTIMENT_MAP_QUERY)


def load_word_lookup(conn) -> int:
    return _create_table(conn, WORD_LOOKUP_TABLE, WORD_LOOKUP_QUERY)


def add_sentiment_map_indexes(conn) -> None:
    with conn.cursor() as cur:
        cur.execute(
            f"CREATE INDEX IF NOT EXISTS idx_lsm_sentiment_id "
            f"ON {SENTIMENT_MAP_TABLE} (sentiment_id);"
        )
        cur.execute(
            f"CREATE INDEX IF NOT EXISTS idx_lsm_dictionary_lemma_id "
            f"ON {SENTIMENT_MAP_TABLE} (dictionary_lemma_id);"
        )
        cur.execute(
            f"CREATE INDEX IF NOT EXISTS idx_lsm_match "
            f"ON {SENTIMENT_MAP_TABLE} (match);"
        )
    conn.commit()


def add_word_lookup_indexes(conn) -> None:
    with conn.cursor() as cur:
        cur.execute(
            f"CREATE INDEX IF NOT EXISTS idx_wl_form_nod "
            f"ON {WORD_LOOKUP_TABLE} (form_nod);"
        )
        cur.execute(
            f"CREATE INDEX IF NOT EXISTS idx_wl_lemma_id "
            f"ON {WORD_LOOKUP_TABLE} (lemma_id);"
        )
        cur.execute(
            f"CREATE INDEX IF NOT EXISTS idx_wl_sentiment_lemma_id "
            f"ON {WORD_LOOKUP_TABLE} (sentiment_lemma_id);"
        )
    conn.commit()


def main():
    dsn = get_dsn()
    print("Connecting to database...")
    try:
        conn = psycopg2.connect(dsn)
    except Exception as e:
        print(f"Failed to connect: {e}")
        sys.exit(1)

    try:
        print(f"Building {SENTIMENT_MAP_TABLE} ...")
        count = load_lemma_sentiment_map(conn)
        print(f"  -> {count:,} rows written.")

        print("Creating sentiment-map indexes...")
        add_sentiment_map_indexes(conn)

        print(f"Building {WORD_LOOKUP_TABLE} ...")
        count = load_word_lookup(conn)
        print(f"  -> {count:,} rows written.")

        print("Creating word-lookup indexes...")
        add_word_lookup_indexes(conn)

        print("Done.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
