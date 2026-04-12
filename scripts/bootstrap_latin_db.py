#!/usr/bin/env python3
"""
Bootstrap a single PostgreSQL database to host:

- Scraped Latin lemmatizer schema (lemmas/forms + norm() + indexes)
- LiLa/LEMLAT sentiment table + convenience views (lila_sentiment + lila_* views)

This script is schema-only. It does NOT import the large LEMLAT dump or scraped CSV data.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRAPED_SCHEMA_SQL = PROJECT_ROOT / "src" / "Lemmatizer-LTN" / "ops" / "init_db.sql"
LILA_SCHEMA_SQL = (
    PROJECT_ROOT
    / "src"
    / "Lemmatizer-LTN-LiLa"
    / "ops"
    / "create_lila_schema.sql"
)


def _read_sql(path: Path) -> str:
    if not path.exists():
        raise SystemExit(f"SQL file not found: {path}")
    return path.read_text(encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--dsn",
        default="",
        help="PostgreSQL DSN (defaults to DATABASE_URL).",
    )
    ap.add_argument(
        "--skip-scraped",
        action="store_true",
        help="Skip applying scraped lemmas/forms schema.",
    )
    ap.add_argument(
        "--skip-lila",
        action="store_true",
        help="Skip applying LiLa sentiment tables/views.",
    )
    args = ap.parse_args()

    # Load DATABASE_URL from .env if present (for local dev ergonomics).
    try:
        from dotenv import load_dotenv  # type: ignore

        env_path = PROJECT_ROOT / ".env"
        if env_path.exists():
            load_dotenv(env_path)
    except Exception:
        pass

    dsn = (args.dsn or os.getenv("DATABASE_URL") or "").strip()
    if not dsn:
        raise SystemExit("Set DATABASE_URL or pass --dsn.")

    try:
        import psycopg2  # type: ignore
    except Exception as exc:  # pragma: no cover
        raise SystemExit(
            "psycopg2 is required to bootstrap the database. "
            "Install in your venv (e.g. `pip install psycopg2-binary`)."
        ) from exc

    conn = psycopg2.connect(dsn)
    conn.autocommit = True
    try:
        with conn.cursor() as cur:
            if not args.skip_scraped:
                cur.execute(_read_sql(SCRAPED_SCHEMA_SQL))
                print(f"[ok] Applied scraped schema: {SCRAPED_SCHEMA_SQL}")
            if not args.skip_lila:
                cur.execute(_read_sql(LILA_SCHEMA_SQL))
                print(f"[ok] Applied LiLa schema: {LILA_SCHEMA_SQL}")
    finally:
        conn.close()

    print("[done] Database bootstrap complete.")


if __name__ == "__main__":
    main()
