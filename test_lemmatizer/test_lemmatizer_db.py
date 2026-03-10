import os
import json
import csv
import re
from pathlib import Path
from typing import Dict, List, Any, Tuple

import psycopg
from dotenv import load_dotenv

from cltk.lemmatize.latin.backoff import BackoffLatinLemmatizer as LatinBackoffLemmatizer  # uses lat_models_cltk backoff pickles [web:39]


HERE = Path(__file__).resolve().parent
TEST_JSON = HERE / "LatinSentenceTestDatav2.json"

OUT_ALL = HERE / "cltk_lemma_db_hits_all.csv"
OUT_HITS = HERE / "cltk_lemma_db_hits_only.csv"
OUT_MISSES = HERE / "cltk_lemma_db_misses_only.csv"

WORD_RE = re.compile(r"[A-Za-z]+", re.UNICODE)


def load_test_cases(path: Path) -> List[Dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, list):
        return data
    return data.get("test_cases", [])


def normalize_lemma(s: str) -> str:
    s = (s or "").strip().lower()

    # Uncomment if your DB uses LEMLAT-style conventions:
    # s = s.replace("v", "u")

    # Optional: strip trailing digits (e.g., marcus1 -> marcus) if your DB does NOT store them
    s = re.sub(r"\d+$", "", s)

    return s


def tokenize_simple(text: str) -> List[str]:
    return [m.group(0).lower() for m in WORD_RE.finditer(text or "")]


def write_csv(path: Path, rows: List[Dict[str, Any]], fieldnames: List[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow(r)


def main():
    load_dotenv()  # loads DATABASE_URL from .env if present [web:72]

    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        raise SystemExit("DATABASE_URL not found. Put it in .env or set it in your shell.")

    cases = load_test_cases(TEST_JSON)
    if not cases:
        raise SystemExit(f"No test cases found in {TEST_JSON}")

    lemmatizer = LatinBackoffLemmatizer()

    token_rows: List[Dict[str, Any]] = []
    unique_lemmas = set()

    for idx, item in enumerate(cases, start=1):
        sent = item.get("sentence", "") or ""
        toks = tokenize_simple(sent)

        pairs: List[Tuple[str, str]] = lemmatizer.lemmatize(toks)  # [web:39]

        for tok, lemma in pairs:
            lem = normalize_lemma(lemma)
            token_rows.append({"idx": idx, "sentence": sent, "token": tok, "lemma": lem})
            if lem:
                unique_lemmas.add(lem)

    lemma_info: Dict[str, Dict[str, Any]] = {}
    with psycopg.connect(db_url) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT lemma, pos, polarity_score, has_polarity, provenance
                FROM lila.sentiment
                WHERE lemma = ANY(%s)
                """,
                (list(unique_lemmas),),
            )
            for lemma, pos, polarity_score, has_polarity, provenance in cur.fetchall():
                lemma_info[normalize_lemma(lemma)] = {
                    "pos": pos,
                    "polarity_score": polarity_score,
                    "has_polarity": has_polarity,
                    "provenance": provenance,
                }

    # Build final rows with DB fields + in_db
    out_rows: List[Dict[str, Any]] = []
    for r in token_rows:
        info = lemma_info.get(r["lemma"])
        out_rows.append(
            {
                **r,
                "in_db": bool(info),
                "db_pos": (info or {}).get("pos"),
                "db_polarity_score": (info or {}).get("polarity_score"),
                "db_has_polarity": (info or {}).get("has_polarity"),
                "db_provenance": (info or {}).get("provenance"),
            }
        )

    fieldnames = [
        "idx",
        "sentence",
        "token",
        "lemma",
        "in_db",
        "db_pos",
        "db_polarity_score",
        "db_has_polarity",
        "db_provenance",
    ]

    hits = [r for r in out_rows if r["in_db"]]
    misses = [r for r in out_rows if not r["in_db"]]

    write_csv(OUT_ALL, out_rows, fieldnames)
    write_csv(OUT_HITS, hits, fieldnames)
    write_csv(OUT_MISSES, misses, fieldnames)

    total_unique = len(unique_lemmas)
    unique_hits = len(lemma_info)
    token_hits = len(hits)

    print(f"Wrote {OUT_ALL}")
    print(f"Wrote {OUT_HITS}")
    print(f"Wrote {OUT_MISSES}")
    print(f"Unique lemmata from test set: {total_unique}")
    print(f"Unique lemmata found in lila.sentiment: {unique_hits}")
    print(f"Unique lemma hit-rate: {unique_hits}/{total_unique} = {(unique_hits/total_unique*100 if total_unique else 0):.2f}%")
    print(f"Token-level hits: {token_hits}/{len(out_rows)} = {(token_hits/len(out_rows)*100 if out_rows else 0):.2f}%")


if __name__ == "__main__":
    main()
