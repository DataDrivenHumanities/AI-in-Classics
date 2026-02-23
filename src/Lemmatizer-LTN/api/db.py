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

        # Add diathesis label for lemma lookups so callers can distinguish
        # active/passive lemma entries (e.g., AMO100 vs AMOR100).
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
            SELECT
                combined.*,
                CASE
                    WHEN upper(COALESCE(combined.lemma_code, '')) ~ 'OR[0-9]+$' THEN 'passive'
                    WHEN upper(COALESCE(combined.lemma_code, '')) ~ 'O[0-9]+$' THEN 'active'
                    WHEN COALESCE(combined.pos, '') ILIKE '%%passive%%' THEN 'passive'
                    WHEN COALESCE(combined.pos, '') ILIKE '%%active%%' THEN 'active'
                    ELSE 'unknown'
                END AS lemma_diathesis
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
# Query: random_forms  (no lemma required)
# ---------------------------------------------------------------------------

def random_forms(
    n: int = 50,
    pos: Optional[str] = None,
    mood: Optional[str] = None,
    tense: Optional[str] = None,
    voice: Optional[str] = None,
    person: Optional[str] = None,
    number: Optional[str] = None,
    gender: Optional[str] = None,
    case: Optional[str] = None,
    degree: Optional[str] = None,
    verb_form: Optional[str] = None,
    exclude_proper: bool = True,
    allow_nonfinite: bool = False,
    rarity_mode: str = "balanced",
) -> List[Dict[str, Any]]:
    """
    Return *n* random forms matching the given morphological filters.
    No lemma or form input is needed — it pulls from the whole DB.
    Optionally filter the parent lemma by *pos* substring.
    """
    query = """
        SELECT
            f.*,
            l.lemma_nod,
            l.lemma_diac,
            l.lemma_code,
            l.pos,
            CASE
                WHEN upper(COALESCE(l.lemma_code, '')) ~ 'OR[0-9]+$' THEN 'passive'
                WHEN upper(COALESCE(l.lemma_code, '')) ~ 'O[0-9]+$' THEN 'active'
                WHEN COALESCE(l.pos, '') ILIKE '%%passive%%' THEN 'passive'
                WHEN COALESCE(l.pos, '') ILIKE '%%active%%' THEN 'active'
                ELSE 'unknown'
            END AS lemma_diathesis
        FROM forms f
        JOIN lemmas l ON l.id = f.lemma_id
        WHERE 1=1
    """
    params: list[Any] = []

    if pos:
        query += " AND l.pos ILIKE '%%' || %s || '%%'"
        params.append(pos)

    if exclude_proper:
        query += " AND COALESCE(l.pos, '') !~* %s"
        params.append(r"(proper|name)")

    filter_values = {
        "mood": mood, "tense": tense, "voice": voice,
        "person": person, "number": number, "gender": gender,
        "case": case, "degree": degree, "verb_form": verb_form,
    }
    for col, val in filter_values.items():
        if val is not None:
            col_ref = f'f."{col}"' if col == "case" else f"f.{col}"
            query += f" AND {col_ref} = %s"
            params.append(val)

    # Prefer finite verb forms unless explicitly allowed.
    if not allow_nonfinite:
        query += " AND (f.verb_form IS NULL OR f.verb_form = '')"

    # Heuristic quality/rarity controls:
    # - common: stricter lexical cleanup
    # - balanced: mostly clean while keeping variety
    # - all: no lexical cleanup beyond explicit filters
    if rarity_mode == "common":
        query += " AND l.lemma_nod ~ %s"
        params.append(r"^[a-z]{2,12}$")
        query += " AND COALESCE(l.pos, '') !~* %s"
        params.append(r"(abbrev|symbol|interj|particle|indeclin)")
    elif rarity_mode == "balanced":
        query += " AND l.lemma_nod ~ %s"
        params.append(r"^[a-z][a-z-]{1,17}$")
        query += " AND COALESCE(l.pos, '') !~* %s"
        params.append(r"(abbrev|symbol)")
    elif rarity_mode != "all":
        raise ValueError("rarity_mode must be one of: common, balanced, all")

    # If caller asks for active voice, avoid passive-looking finite endings.
    if voice == "active":
        query += " AND f.form_nod !~ %s"
        params.append(r"(tur|ntur|mur|mini|ris|r)$")

    query += " ORDER BY random() LIMIT %s"
    params.append(n)

    pool = _get_pool()
    with pool.connection() as conn:
        rows = conn.execute(query, tuple(params)).fetchall()
        return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Query: random_lemmas
# ---------------------------------------------------------------------------

def random_lemmas(
    n: int = 10,
    pos: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Return *n* random lemmas, optionally filtered by POS substring."""
    pool = _get_pool()
    with pool.connection() as conn:
        if pos:
            query = """
                SELECT * FROM lemmas
                WHERE pos ILIKE '%%' || %s || '%%'
                ORDER BY random()
                LIMIT %s
            """
            rows = conn.execute(query, (pos, n)).fetchall()
        else:
            query = "SELECT * FROM lemmas ORDER BY random() LIMIT %s"
            rows = conn.execute(query, (n,)).fetchall()
        return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Query: batch_forms
# ---------------------------------------------------------------------------

def batch_forms(
    queries: List[Dict[str, Any]],
) -> List[List[Dict[str, Any]]]:
    """
    Resolve multiple form queries in a single DB connection.
    Each entry in *queries* is a dict with 'lemma' (required) plus
    optional morphological filters (mood, tense, voice, etc.).
    Returns a list of result-lists, one per input query.
    """
    pool = _get_pool()
    results: List[List[Dict[str, Any]]] = []
    with pool.connection() as conn:
        for q in queries:
            lemma = q.get("lemma")
            if not lemma:
                results.append([])
                continue

            base = """
                SELECT f.* FROM lemmas l
                JOIN forms f ON f.lemma_id = l.id
                WHERE l.lemma_nod = norm(%s)
            """
            params: list[Any] = [lemma]

            for col in _FILTER_COLUMNS:
                val = q.get(col)
                if val:
                    col_ref = f'f."{col}"' if col == "case" else f"f.{col}"
                    base += f" AND {col_ref} = %s"
                    params.append(val)

            base += (
                ' ORDER BY f.mood, f.tense, f.voice, f.person, f.number, '
                'f.gender, f."case", f.degree, f.verb_form, f.form_nod'
            )
            rows = conn.execute(base, tuple(params)).fetchall()
            results.append([dict(r) for r in rows])
    return results


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
