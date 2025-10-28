#!/usr/bin/env python3
"""
LSJ Headwords Scraper for Perseus Hopper

- Source: Henry George Liddell, Robert Scott, A Greek-English Lexicon (Perseus)
- Index page: https://www.perseus.tufts.edu/hopper/text?doc=Perseus:text:1999.04.0057
- Strategy:
  1) Fetch the LSJ index page and collect all "entry group" links (alphabetic ranges).
  2) For each entry group URL, parse all headword entry links.
  3) Collect headword text and entry URL, write to CSV/JSON.

CLI examples:
  python lsj_headwords_scraper.py --out lsj_headwords.csv
  python lsj_headwords_scraper.py --out lsj_headwords.json --format json --limit 200

Notes:
- Read-only scraper with polite delays.
- Targets stable URL patterns. If Perseus HTML changes, update the regex/CSS selectors.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
import time
from dataclasses import dataclass, asdict
from typing import Iterable, List, Optional
from urllib.parse import unquote

import requests
from bs4 import BeautifulSoup

BASE_INDEX_URL = "https://www.perseus.tufts.edu/hopper/text?doc=Perseus:text:1999.04.0057"
# Simple substring targets used after URL-decoding
ENTRY_GROUP_SUBSTR = "Perseus:text:1999.04.0057:alphabetic+letter="
ENTRY_GROUP_AND = ":entry+group="
ENTRY_PAGE_SUBSTR = "Perseus:text:1999.04.0057:entry="

HEADERS = {
    "User-Agent": (
        "AI-in-Classics LSJ Headword Scraper (+https://github.com/ahulloli/AI-in-Classics)"
    )
}


@dataclass
class Headword:
    lemma: str
    url: str
    source: str = "LSJ"
    language: str = "grc"


def fetch(url: str, session: Optional[requests.Session] = None, timeout: int = 45) -> str:
    s = session or requests.Session()
    resp = s.get(url, headers=HEADERS, timeout=timeout)
    resp.raise_for_status()
    return resp.text


def extract_entry_group_links(html: str) -> List[str]:
    """Extract all absolute entry-group URLs from the LSJ index page."""
    soup = BeautifulSoup(html, "html.parser")
    links: List[str] = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        href_dec = unquote(href)
        if (ENTRY_GROUP_SUBSTR in href_dec) and (ENTRY_GROUP_AND in href_dec):
            if href.startswith("/hopper/"):
                href = f"https://www.perseus.tufts.edu{href}"
            elif href.startswith("http"):
                pass  # already absolute
            else:
                href = f"https://www.perseus.tufts.edu/hopper/{href.lstrip('/')}"
            links.append(href)
    # Deduplicate while preserving order
    seen = set()
    unique: List[str] = []
    for u in links:
        if u not in seen:
            seen.add(u)
            unique.append(u)
    return unique


def generate_letter_urls() -> List[str]:
    """Deterministically construct the LSJ letter overview URLs.

    Perseus uses star-prefixed Latin transcriptions for Greek letters, e.g. *a, *b, *g, etc.
    """
    letters = [
        "*a","*b","*g","*d","*e","*z","*h","*q","*i","*k","*l","*m",
        "*n","*c","*o","*p","*r","*s","*t","*u","*f","*x","*y","*w",
    ]
    urls = [
        f"https://www.perseus.tufts.edu/hopper/text?doc=Perseus:text:1999.04.0057:alphabetic+letter={ltr}"
        for ltr in letters
    ]
    return urls


def extract_headwords_from_entry_group(html: str) -> List[Headword]:
    """Extract LSJ headwords (lemma text and entry URL) from an entry-group page."""
    soup = BeautifulSoup(html, "html.parser")
    results: List[Headword] = []

    # Heuristic: LSJ entry links have hrefs containing 'Perseus:text:1999.04.0057:entry='
    for a in soup.find_all("a", href=True):
        href = a["href"]
        href_dec = unquote(href)
        if ENTRY_PAGE_SUBSTR in href_dec:
            text = a.get_text(strip=True)
            if not text:
                continue
            if href.startswith("/hopper/"):
                full_url = f"https://www.perseus.tufts.edu{href}"
            elif href.startswith("http"):
                full_url = href
            else:
                full_url = f"https://www.perseus.tufts.edu/hopper/{href.lstrip('/')}"
            results.append(Headword(lemma=text, url=full_url))

    # Some entry groups may list headwords inside lists/tables; if needed, add
    # fallback selectors here.

    return results


def write_csv(path: str, items: Iterable[Headword]) -> None:
    os.makedirs(os.path.dirname(os.path.abspath(path)) or ".", exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["language", "source", "lemma", "url"])  # header
        for it in items:
            w.writerow([it.language, it.source, it.lemma, it.url])


def write_json(path: str, items: Iterable[Headword]) -> None:
    os.makedirs(os.path.dirname(os.path.abspath(path)) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump([asdict(i) for i in items], f, ensure_ascii=False, indent=2)


def scrape_lsj_headwords(
    out_path: str,
    out_format: str = "csv",
    limit: Optional[int] = None,
    delay_sec: float = 0.8,
    max_retries: int = 3,
) -> int:
    """Return the number of headwords written."""
    session = requests.Session()

    # 1) Fetch index and collect entry-group URLs
    for attempt in range(max_retries):
        try:
            index_html = fetch(BASE_INDEX_URL, session=session)
            break
        except Exception as e:
            if attempt + 1 >= max_retries:
                raise
            time.sleep(1.5 * (attempt + 1))
    # Prefer deterministic letter URL generation for robustness
    letters = generate_letter_urls()
    print(f"INFO: generated {len(letters)} letter page URLs.")
    entry_groups: List[str] = extract_entry_group_links(index_html)
    print(f"INFO: found {len(entry_groups)} entry-group links on index.")
    # For each generated letter page, also gather entry groups
    for letter_url in letters:
        try:
            letter_html = fetch(letter_url, session=session)
        except Exception as e:
            print(f"WARN: failed to fetch letter page {letter_url}: {e}", file=sys.stderr)
            continue
        eg_links = extract_entry_group_links(letter_html)
        print(f"INFO: {letter_url} -> {len(eg_links)} entry-groups")
        for u in eg_links:
            if u not in entry_groups:
                entry_groups.append(u)
        if limit is not None and len(entry_groups) >= max(limit, 50):
            # Ensure we have enough groups for headword extraction; if limit is small, still collect some extra groups
            break
        time.sleep(delay_sec)
    if not entry_groups:
        print("No entry-group links found on LSJ index or letter pages.", file=sys.stderr)
        return 0

    collected: List[Headword] = []

    # 2) Iterate entry-group pages and collect headwords
    for i, url in enumerate(entry_groups):
        try:
            html = fetch(url, session=session)
        except Exception as e:
            print(f"WARN: failed to fetch entry-group {url}: {e}", file=sys.stderr)
            continue
        items = extract_headwords_from_entry_group(html)
        collected.extend(items)

        if limit is not None and len(collected) >= limit:
            collected = collected[:limit]
            break
        time.sleep(delay_sec)

    # Deduplicate by lemma text (keep first occurrence)
    seen = set()
    unique_items: List[Headword] = []
    for hw in collected:
        key = hw.lemma
        if key in seen:
            continue
        seen.add(key)
        unique_items.append(hw)

    # 3) Write output
    if out_format.lower() == "csv":
        write_csv(out_path, unique_items)
    elif out_format.lower() == "json":
        write_json(out_path, unique_items)
    else:
        raise ValueError("Unsupported format. Use 'csv' or 'json'.")

    return len(unique_items)


def main(argv: Optional[List[str]] = None) -> int:
    p = argparse.ArgumentParser(description="Scrape LSJ Greek headwords (lemmas) from Perseus.")
    p.add_argument("--out", required=True, help="Output file path (e.g., lsj_headwords.csv)")
    p.add_argument("--format", default="csv", choices=["csv", "json"], help="Output format.")
    p.add_argument("--limit", type=int, default=None, help="Optional maximum number of headwords to collect.")
    p.add_argument("--delay", type=float, default=0.8, help="Delay between requests (seconds).")
    p.add_argument("--retries", type=int, default=3, help="Max retries for fetching the index page.")
    args = p.parse_args(argv)

    try:
        count = scrape_lsj_headwords(
            out_path=args.out,
            out_format=args.format,
            limit=args.limit,
            delay_sec=args.delay,
            max_retries=args.retries,
        )
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1

    print(f"Wrote {count} Greek headwords to {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
