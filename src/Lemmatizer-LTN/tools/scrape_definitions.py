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
import time
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
    """
    Extract English definitions from online-latin-dictionary.com lemma pages.

    Notes:
      - Pages can contain multiple (invalid) duplicate `id="myth"` blocks. The first
        one is the lemma definitions; later ones often contain locutions/examples.
      - Definitions are commonly encoded as: <b>1</b> <span class="english">...</span>
        <b>2</b> <span class="english">...</span> ...
    """
    soup = BeautifulSoup(html or "", "html.parser")

    myth_blocks = soup.find_all(id="myth") or []
    if not myth_blocks:
        return ""

    def _extract_from_myth(myth) -> str:
        # Prefer numbered senses when present.
        senses: list[str] = []
        for b_tag in myth.find_all("b"):
            num = (b_tag.get_text(strip=True) or "").strip()
            if not num.isdigit():
                continue

            english = ""
            for sib in b_tag.next_siblings:
                name = getattr(sib, "name", None)
                if name == "b":
                    break
                if name == "span" and "english" in (sib.get("class") or []):
                    english = _clean_text(sib.get_text(" ", strip=True))
                    break
            if english:
                senses.append(f"{num}. {english}")

        if senses:
            return "; ".join(senses)

        # Fallback: first english gloss if numbering isn't present.
        el = myth.select_one("span.english")
        if not el:
            return ""
        return _clean_text(el.get_text(" ", strip=True))

    # Pick the first myth block that actually contains english glosses.
    for myth in myth_blocks:
        if myth.select_one("span.english"):
            return _extract_from_myth(myth)
    return ""


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
    progress_every: int = 0,
) -> list[Tuple[int, str]]:
    sem = asyncio.Semaphore(max(1, int(concurrency)))
    async with aiohttp.ClientSession() as session:
        tasks = [
            asyncio.create_task(fetch_one(session, sem, int(lemma_id), str(url).replace("latin-dictionary-flexion.php", "latin-english-dictionary.php")))
            for (lemma_id, url) in rows
            if url
        ]
        out: list[Tuple[int, str]] = []
        total = len(tasks)
        done = 0
        ok = 0
        empty = 0
        started = time.perf_counter()
        for coro in asyncio.as_completed(tasks):
            lemma_id, definition = await coro
            out.append((lemma_id, definition))
            done += 1
            if definition:
                ok += 1
            else:
                empty += 1
            if progress_every and (done % max(1, int(progress_every)) == 0):
                elapsed = max(0.001, time.perf_counter() - started)
                rate = done / elapsed
                print(f"  [{done:,}/{total:,}] ok={ok:,} empty={empty:,} rate={rate:.1f}/s", flush=True)
        return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dsn", default=None, help="Postgres DSN (defaults to DATABASE_URL env var)")
    ap.add_argument("--limit", type=int, default=1000, help="Max lemmas to scrape")
    ap.add_argument("--concurrency", type=int, default=40, help="Concurrent HTTP fetches")
    ap.add_argument("--chunk-size", type=int, default=2000, help="Process updates in chunks (safer for long runs)")
    ap.add_argument("--progress-every", type=int, default=200, help="Print progress every N fetched pages (0 disables)")
    ap.add_argument(
        "--only-sentiment",
        action="store_true",
        help="Only scrape lemmas that are mapped from the LatinAffectus sentiment lexicon (fast path for UI).",
    )
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
    chunk_size = max(1, int(args.chunk_size))
    progress_every = max(0, int(args.progress_every))

    with psycopg.connect(dsn) as conn:
        with conn.cursor() as cur:
            if args.only_sentiment:
                cur.execute(
                    """
                    SELECT DISTINCT l.id, l.page_url
                    FROM public.lemma_sentiment_map m
                    JOIN public.lemmas l ON l.id = m.dictionary_lemma_id
                    WHERE m.match = TRUE
                      AND m.dictionary_lemma_id IS NOT NULL
                      AND (l.definition IS NULL OR l.definition = '')
                      AND l.page_url IS NOT NULL AND l.page_url <> ''
                    ORDER BY l.id
                    LIMIT %s
                    """,
                    (limit,),
                )
            else:
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

        mode = "sentiment-mapped lemmas" if args.only_sentiment else "all lemmas"
        print(f"Scraping {len(rows):,} {mode}…", flush=True)

        total_updates = 0
        total_parsed = 0
        total_chunks = (len(rows) + chunk_size - 1) // chunk_size

        for idx in range(total_chunks):
            chunk = rows[idx * chunk_size : (idx + 1) * chunk_size]
            if not chunk:
                continue

            print(f"[chunk {idx + 1}/{total_chunks}] fetching {len(chunk):,}…", flush=True)
            results = asyncio.run(
                scrape(chunk, concurrency=int(args.concurrency), progress_every=progress_every)
            )

            updates = [(definition, lemma_id) for (lemma_id, definition) in results if definition]
            total_parsed += len(updates)
            print(f"[chunk {idx + 1}/{total_chunks}] parsed {len(updates):,} definitions.", flush=True)

            if args.dry_run or not updates:
                continue

            with conn.cursor() as cur:
                cur.executemany(
                    "UPDATE public.lemmas SET definition = %s WHERE id = %s",
                    updates,
                )
            conn.commit()
            total_updates += len(updates)
            print(f"[chunk {idx + 1}/{total_chunks}] committed {len(updates):,}.", flush=True)

        if args.dry_run:
            print(f"[done] Dry run complete. Parsed {total_parsed:,} definitions.", flush=True)
            return
        print(f"[done] Updated {total_updates:,} lemma definitions.", flush=True)


if __name__ == "__main__":
    main()
