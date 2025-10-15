import asyncio
import aiohttp
from aiohttp import ClientResponseError, ClientConnectorError
from bs4 import BeautifulSoup
from urllib.parse import urlparse, parse_qs, urljoin
from pathlib import Path
import csv
import re
import unicodedata
import argparse
import random
import time

BASE = "https://www.online-latin-dictionary.com"
INDEX_URL = BASE + "/latin-english-dictionary.php?typ=pg&pg={pg}"
FLEXION_URL = BASE + "/latin-dictionary-flexion.php?lemma={lemma}"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; DDHBot/1.0)"
}

def strip_accents(s: str) -> str:
    nfkd = unicodedata.normalize("NFD", s or "")
    return "".join(ch for ch in nfkd if not unicodedata.combining(ch))

def slugify_lemma(lemma_text: str) -> str:
    s = strip_accents(lemma_text).lower()
    s = re.sub(r"[^a-z0-9]+", "_", s)
    s = re.sub(r"_+", "_", s).strip("_")
    return s or "lemma"

def parse_index_for_lemmas(html_text: str):
    soup = BeautifulSoup(html_text, "html.parser")
    lemmas = []
    for a in soup.select("div.browse a.adv"):
        href = a.get("href", "")
        if "latin-english-dictionary.php" in href and "lemma=" in href:
            q = parse_qs(urlparse(urljoin(BASE, href)).query)
            code = q.get("lemma", [None])[0]
            if code:
                lemmas.append(code)
    return lemmas

_whitespace = re.compile(r"\s+")

def flatten_ff_value(cell):
    out = []
    for node in cell.children:
        name = getattr(node, "name", None)
        classes = set(getattr(node, "get", lambda *_: [])("class", []))
        if name == "span" and "radice" in classes:
            rad = node.get_text("", strip=True)
            nxt = node.find_next_sibling()
            if getattr(nxt, "name", None) == "span" and "desinenza" in set(nxt.get("class", [])):
                out.append(rad + nxt.get_text("", strip=True))
            else:
                out.append(rad)
        elif name == "span" and "desinenza" in classes:
            out.append(node.get_text("", strip=True))
        else:
            if hasattr(node, "get_text"):
                out.append(node.get_text(" ", strip=False))
            else:
                s = str(node)
                if s:
                    out.append(s)
    s = "".join(out)
    s = _whitespace.sub(" ", s).strip()
    return s

def parse_flexion_tables(html_text: str, page_url: str):
    soup = BeautifulSoup(html_text, "html.parser")
    h2 = soup.select_one("#myth h2")
    lemma_text = h2.get_text(strip=True) if h2 else ""
    pos = soup.select_one("#myth .grammatica")
    pos_text = pos.get_text(" ", strip=True) if pos else ""

    rows = []
    for cont in soup.select(".conjugation-container .ff_tbl_container"):
        titles = [t.get_text(" ", strip=True) for t in cont.find_all_previous("div", class_="ff_tbl_title", limit=3)]
        titles = list(reversed(titles))
        for r in cont.select(".ff_tbl_row"):
            cols = r.select(".ff_tbl_col")
            if not cols:
                continue
            label = cols[0].get_text(" ", strip=True)
            value = flatten_ff_value(cols[-1])
            rows.append({
                "lemma_text": lemma_text,
                "pos": pos_text,
                "context_1": titles[0] if len(titles) > 0 else "",
                "context_2": titles[1] if len(titles) > 1 else "",
                "context_3": titles[2] if len(titles) > 2 else "",
                "label": label,
                "value": value,
                "page_url": page_url,
            })
    return lemma_text, rows

async def fetch_text(session: aiohttp.ClientSession, url: str, timeout: int = 20, retries: int = 4, delay: float = 0.2):
    for attempt in range(retries + 1):
        try:
            async with session.get(url, timeout=timeout) as resp:
                resp.raise_for_status()
                return await resp.text()
        except (ClientResponseError, ClientConnectorError, asyncio.TimeoutError) as e:
            if attempt >= retries:
                raise
            backoff = delay * (2 ** attempt) + random.uniform(0, delay)
            await asyncio.sleep(backoff)

async def gather_index_range(session, start: int, step: int, end: int, sem: asyncio.Semaphore, delay: float):
    all_codes = set()
    async def one(pg: int):
        url = INDEX_URL.format(pg=pg)
        async with sem:
            html = await fetch_text(session, url)
            codes = parse_index_for_lemmas(html)
            # tiny polite jitter
            if delay > 0:
                await asyncio.sleep(delay)
            return codes
    tasks = [asyncio.create_task(one(pg)) for pg in range(start, end + 1, step)]
    for t in asyncio.as_completed(tasks):
        try:
            codes = await t
            all_codes.update(codes)
        except Exception as e:
            # Log and continue
            print(f"[index] warn: {e}")
    return sorted(all_codes)

async def discover_lemmas_dynamic(session, start: int, step: int, sem: asyncio.Semaphore, delay: float, max_empty: int = 2):
    """Sequentially walk index pages until we see 'max_empty' empty pages, returns a set of lemma codes."""
    all_codes = set()
    empty_run = 0
    pg = start
    while True:
        url = INDEX_URL.format(pg=pg)
        async with sem:
            try:
                html = await fetch_text(session, url)
            except Exception as e:
                print(f"[index pg={pg}] warn: {e}")
                break
            codes = parse_index_for_lemmas(html)
            print(f"[index pg={pg}] lemmas: {len(codes)}")
            if codes:
                all_codes.update(codes)
                empty_run = 0
            else:
                empty_run += 1
                if empty_run >= max_empty:
                    print("[index] stopping after consecutive empty pages")
                    break
            if delay > 0:
                await asyncio.sleep(delay)
        pg += step
    return sorted(all_codes)

async def fetch_and_write_lemma(session, code: str, outdir: Path, sem: asyncio.Semaphore, delay: float):
    url = FLEXION_URL.format(lemma=code)
    async with sem:
        try:
            html = await fetch_text(session, url)
        except Exception as e:
            print(f"[lemma {code}] warn: {e}")
            return 0
        lemma_text, rows = parse_flexion_tables(html, url)
        if not rows:
            return 0
        outdir.mkdir(parents=True, exist_ok=True)
        name = slugify_lemma(lemma_text) + ".csv"
        path = outdir / name
        with path.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=[
                "lemma_text","pos","context_1","context_2","context_3","label","value","page_url"
            ])
            w.writeheader()
            for r in rows:
                w.writerow(r)
        if delay > 0:
            await asyncio.sleep(delay)
        return len(rows)

async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--outdir", default="out", help="Directory for per-lemma CSVs")
    ap.add_argument("--start", type=int, default=1, help="First index page number (pg=...)")
    ap.add_argument("--step", type=int, default=50, help="Pagination step (default 50)")
    ap.add_argument("--end", type=int, default=None, help="Last index page number (if omitted, use --dynamic)")
    ap.add_argument("--dynamic", action="store_true", help="Sequentially discover index pages until empty, then parallelize lemma fetching")
    ap.add_argument("--index-concurrency", type=int, default=8, help="Concurrent index fetches")
    ap.add_argument("--lemma-concurrency", type=int, default=16, help="Concurrent lemma fetches")
    ap.add_argument("--timeout", type=int, default=20, help="HTTP timeout seconds")
    ap.add_argument("--retries", type=int, default=4, help="Retry count per request")
    ap.add_argument("--delay", type=float, default=0.2, help="Polite small delay between requests")
    args = ap.parse_args()

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    connector = aiohttp.TCPConnector(limit= args.index_concurrency + args.lemma_concurrency, ssl=False)
    timeout = aiohttp.ClientTimeout(total=None, sock_connect=args.timeout, sock_read=args.timeout)
    async with aiohttp.ClientSession(headers=HEADERS, connector=connector, timeout=timeout) as session:
        # Phase 1: collect lemmas
        index_sem = asyncio.Semaphore(args.index_concurrency)
        if args.dynamic or args.end is None:
            print("[index] dynamic discovery mode")
            lemma_codes = await discover_lemmas_dynamic(session, args.start, args.step, index_sem, args.delay)
        else:
            print(f"[index] fetching range {args.start}..{args.end} step {args.step}")
            lemma_codes = await gather_index_range(session, args.start, args.step, args.end, index_sem, args.delay)
        print(f"[index] unique lemmas: {len(lemma_codes)}")

        # Phase 2: fetch lemmas
        lemma_sem = asyncio.Semaphore(args.lemma_concurrency)
        tasks = [asyncio.create_task(fetch_and_write_lemma(session, code, outdir, lemma_sem, args.delay)) for code in lemma_codes]
        done = 0
        rows_total = 0
        for t in asyncio.as_completed(tasks):
            try:
                n = await t
                rows_total += n
            except Exception as e:
                print(f"[lemma] warn: {e}")
            done += 1
            if done % 50 == 0 or done == len(tasks):
                print(f"[lemma] progress: {done}/{len(tasks)} CSVs")
        print(f"[lemma] finished. rows written: {rows_total}")

if __name__ == "__main__":
    asyncio.run(main())
