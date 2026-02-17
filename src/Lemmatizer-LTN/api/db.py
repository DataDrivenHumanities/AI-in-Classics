"""
Database connection pool and query helpers for the Latin Lemmatizer API.

All SQL from the original latin_lemmatizer.client is centralised here.
The pool is created at startup and closed at shutdown via the FastAPI lifespan.
"""

import os
from typing import Optional, List, Dict, Any

import psycopg
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

# ---------------------------------------------------------------------------
# Connection pool (initialised by open_pool / close_pool)
# ---------------------------------------------------------------------------

_pool: Optional[ConnectionPool] = None


def open_pool() -> None:
    """Create the global connection pool.  Call once at app startup."""
    global _pool
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        raise RuntimeError("DATABASE_URL environment variable is not set.")
    _pool = ConnectionPool(
        conninfo=dsn,
        min_size=2,
        max_size=10,
        kwargs={"row_factory": dict_row},
    )
    _pool.wait()  # block until min_size connections are ready


def close_pool() -> None:
    """Shut down the global connection pool.  Call once at app shutdown."""
    global _pool
    if _pool is not None:
        _pool.close()
        _pool = None


def _get_pool() -> ConnectionPool:
    if _pool is None:
        raise RuntimeError("Connection pool is not initialised. Call open_pool() first.")
    return _pool


# ---------------------------------------------------------------------------
# Query: get_lemmas
# ---------------------------------------------------------------------------

def get_lemmas(word: str, pos: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Look up lemmas matching *word*, ranked by relevance.

    First checks the lemmas table for an exact match on lemma_nod,
    then falls back to looking the word up as an inflected form.
    Results from both sources are merged, deduplicated, and ranked:
      1. Exact lemma matches first
      2. Then by whether the lemma_nod is a prefix of the word
      3. Then by lemma_nod length descending (most specific first)

    An optional *pos* filter narrows results to lemmas whose ``pos``
    column contains the given substring (case-insensitive), e.g.
    ``pos="noun"`` matches "feminine noun I declension".
    """
    pool = _get_pool()
    with pool.connection() as conn:
        pos_filter = " AND l.pos ILIKE '%%' || %s || '%%'" if pos else ""

        # Build params in query order
        exact_params: list[Any] = [word]
        if pos:
            exact_params.append(pos)

        via_params: list[Any] = [word]
        if pos:
            via_params.append(pos)

        order_params: list[Any] = [word]

        query = f"""
            WITH exact AS (
                SELECT l.*, 1 AS _src
                FROM lemmas l
                WHERE l.lemma_nod = norm(%s){pos_filter}
            ),
            via_form AS (
                SELECT DISTINCT ON (l.id) l.*, 0 AS _src
                FROM forms f
                JOIN lemmas l ON l.id = f.lemma_id
                WHERE f.form_nod = norm(%s){pos_filter}
            ),
            combined AS (
                SELECT * FROM exact
                UNION
                SELECT * FROM via_form
            )
            SELECT *
            FROM combined
            ORDER BY
                _src DESC,
                (strpos(norm(%s), lemma_nod) = 1)::int DESC,
                length(lemma_nod) ASC
        """

        all_params = exact_params + via_params + order_params
        rows = conn.execute(query, tuple(all_params)).fetchall()
        return [
            {k: v for k, v in dict(r).items() if k != "_src"}
            for r in rows
        ]


# ---------------------------------------------------------------------------
# Query: get_forms
# ---------------------------------------------------------------------------

_FILTER_COLUMNS = [
    "mood",
    "tense",
    "voice",
    "person",
    "number",
    "gender",
    "case",
    "degree",
    "verb_form",
]


def get_forms(
    *,
    lemma: Optional[str] = None,
    form: Optional[str] = None,
    mood: Optional[str] = None,
    tense: Optional[str] = None,
    voice: Optional[str] = None,
    person: Optional[str] = None,
    number: Optional[str] = None,
    gender: Optional[str] = None,
    case: Optional[str] = None,
    degree: Optional[str] = None,
    verb_form: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Return inflected forms matching the given criteria.

    Exactly one of *lemma* or *form* must be provided.
    """
    if (lemma is None) == (form is None):
        raise ValueError("Provide exactly one of: lemma, form")

    params: list[Any] = []

    if lemma is not None:
        base_query = """
            SELECT f.* FROM lemmas l
            JOIN forms f ON f.lemma_id = l.id
            WHERE l.lemma_nod = norm(%s)
        """
        params.append(lemma)
    else:
        base_query = """
            WITH base AS (
                SELECT l.id AS lemma_id
                FROM forms f JOIN lemmas l ON l.id = f.lemma_id
                WHERE f.form_nod = norm(%s)
                LIMIT 1
            )
            SELECT f.* FROM forms f, base b
            WHERE f.lemma_id = b.lemma_id
        """
        params.append(form)

    # Dynamic morphological filters
    filter_values = {
        "mood": mood,
        "tense": tense,
        "voice": voice,
        "person": person,
        "number": number,
        "gender": gender,
        "case": case,
        "degree": degree,
        "verb_form": verb_form,
    }
    filter_clauses: list[str] = []
    for col, val in filter_values.items():
        if val is not None:
            # "case" is a reserved word in SQL — quote it
            col_ref = f'f."{col}"' if col == "case" else f"f.{col}"
            filter_clauses.append(f"{col_ref} = %s")
            params.append(val)

    if filter_clauses:
        base_query += " AND " + " AND ".join(filter_clauses)

    base_query += (
        ' ORDER BY f.mood, f.tense, f.voice, f.person, f.number, '
        'f.gender, f."case", f.degree, f.verb_form, f.form_nod'
    )

    pool = _get_pool()
    with pool.connection() as conn:
        rows = conn.execute(base_query, tuple(params)).fetchall()
        return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

def health_check() -> bool:
    """Return True if the database is reachable."""
    try:
        pool = _get_pool()
        with pool.connection() as conn:
            conn.execute("SELECT 1")
        return True
    except Exception:
        return False
