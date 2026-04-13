"""
Scrape English definitions for Latin lemmas and backfill `public.lemmas.definition`.

Usage:
  python ./src/Lemmatizer-LTN/tools/scrape_definitions.py --limit 100000

Requires:
  - DATABASE_URL set to a Postgres DSN
  - aiohttp
  - beautifulsoup4
"""

from __future__ import annotations

import argparse
import asyncio
import re
from typing import Iterable, Optional, Tuple

import aiohttp
from bs4 import BeautifulSoup
import psycopg


HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; AI-in-Classics/1.0)"}
_WS = re.compile(r"\s+")


def _clean_text(s: str) -> str:
    s = (s or "").strip()
    s = _WS.sub(" ", s)
    return s


def extract_definition_from_html(html: str) -> str:
    soup = BeautifulSoup(html or "", "html.parser")
    # online-latin-dictionary uses `.english` blocks for English glosses.
    el = soup.select_one(".english")
    if not el:
        return ""
    return _clean_text(el.get_text(" ", strip=True))


async def fetch_one(
    session: aiohttp.ClientSession,
    sem: asyncio.Semaphore,
    lemma_id: int,
    url: str,
) -> Tuple[int, str]:
    async with sem:
        try:
            async with session.get(url, headers=HEADERS, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                resp.raise_for_status()
                html = await resp.text(errors="ignore")
        except Exception:
            return lemma_id, ""
    return lemma_id, extract_definition_from_html(html)


async def scrape(
    rows: Iterable[Tuple[int, str]],
    *,
    concurrency: int,
) -> list[Tuple[int, str]]:
    sem = asyncio.Semaphore(max(1, int(concurrency)))
    async with aiohttp.ClientSession() as session:
        tasks = [
            asyncio.create_task(fetch_one(session, sem, int(lemma_id), str(url).replace("latin-dictionary-flexion.php", "latin-english-dictionary.php")))
            for (lemma_id, url) in rows
            if url
        ]
        out: list[Tuple[int, str]] = []
        for coro in asyncio.as_completed(tasks):
            out.append(await coro)
        return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dsn", default=None, help="Postgres DSN (defaults to DATABASE_URL env var)")
    ap.add_argument("--limit", type=int, default=1000, help="Max lemmas to scrape")
    ap.add_argument("--concurrency", type=int, default=40, help="Concurrent HTTP fetches")
    ap.add_argument("--dry-run", action="store_true", help="Fetch + parse but do not update DB")
    args = ap.parse_args()

    dsn: Optional[str] = args.dsn
    if not dsn:
        import os
        from dotenv import load_dotenv
        load_dotenv()

        dsn = os.getenv("DATABASE_URL")
    if not dsn:
        raise SystemExit("Set DATABASE_URL or pass --dsn.")

    limit = max(1, int(args.limit))

    with psycopg.connect(dsn) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, page_url
                FROM public.lemmas
                WHERE (definition IS NULL OR definition = '')
                  AND page_url IS NOT NULL AND page_url <> ''
                ORDER BY id
                LIMIT %s
                """,
                (limit,),
            )
            rows = [(int(r[0]), str(r[1])) for r in cur.fetchall()]

        if not rows:
            print("No rows to update.")
            return

        print(f"Scraping {len(rows):,} lemma pages…")
        results = asyncio.run(scrape(rows, concurrency=int(args.concurrency)))
        updates = [(definition, lemma_id) for (lemma_id, definition) in results if definition]

        print(f"Parsed {len(updates):,} definitions.")
        if args.dry_run:
            return

        with conn.cursor() as cur:
            cur.executemany(
                "UPDATE public.lemmas SET definition = %s WHERE id = %s",
                updates,
            )
        conn.commit()
        print("Done.")


if __name__ == "__main__":
    main()

