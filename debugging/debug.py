#!/usr/bin/env python3

import os
import sys
import re
from typing import List, Dict, Any

import requests
import psycopg
from dotenv import load_dotenv
from cltk import NLP

OLLAMA_API_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "latin-sentiment-llama31-5class"

WORD_RE = re.compile(r"[A-Za-z]+", re.UNICODE)
CONTEXT_MODE = "POLAR_ONLY"
MAX_CONTEXT_ITEMS = 10


def normalize_lemma(s: str) -> str:
    s = (s or "").strip().lower()
    s = re.sub(r"\d+$", "", s)
    return s


def ollama_generate(prompt: str, timeout_s: int = 180) -> str:
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {
            "num_predict": 400,
            "temperature": 0,
            "top_p": 0.9,
        },
    }
    r = requests.post(OLLAMA_API_URL, json=payload, timeout=timeout_s)
    r.raise_for_status()
    return (r.json().get("response") or "").strip()


def fetch_lemma_context(conn: psycopg.Connection, lemmas: List[str]) -> List[Dict[str, Any]]:
    lemmas = [normalize_lemma(x) for x in lemmas if x]
    lemmas = sorted(set(lemmas))
    if not lemmas:
        return []

    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT lemma, pos, polarity_score, has_polarity, provenance
            FROM lila.sentiment
            WHERE lemma = ANY(%s)
            """,
            (lemmas,),
        )
        rows = cur.fetchall()

    out: List[Dict[str, Any]] = []
    for lemma, pos, polarity_score, has_polarity, provenance in rows:
        rec = {
            "lemma": normalize_lemma(lemma),
            "pos": pos,
            "polarity_score": polarity_score,
            "has_polarity": has_polarity,
            "provenance": provenance,
        }

        if CONTEXT_MODE == "POLAR_ONLY" and rec["polarity_score"] is None:
            continue

        out.append(rec)

    def keyfn(r):
        ps = r["polarity_score"]
        try:
            return (0, -abs(float(ps)), r["lemma"])
        except Exception:
            return (1, 0, r["lemma"])

    out.sort(key=keyfn)
    return out[:MAX_CONTEXT_ITEMS]


def format_context_rows(rows: List[Dict[str, Any]]) -> str:
    if not rows:
        return "Lexicon evidence (lila.sentiment): (no lemma matches found)"

    lines = ["Lexicon evidence (lila.sentiment; lemma-matched):"]
    for r in rows:
        lines.append(
            f"- lemma={r['lemma']} pos={r.get('pos')} polarity_score={r.get('polarity_score')} "
            f"has_polarity={r.get('has_polarity')} provenance={r.get('provenance')}"
        )
    return "\n".join(lines)


def build_debug_prompt(sentence: str, context_rows: List[Dict[str, Any]]) -> str:
    ctx = format_context_rows(context_rows)
    return f"""
You are debugging the Latin sentiment classifier whose system prompt you already follow.

Instead of outputting only a label, explain how you arrive at it.

Sentence:
{sentence}

{ctx}

Answer in this structure:

1. Literal sense
- Briefly translate/explain the Latin sentence.

2. Main sentiment cue
- Identify the main event or emotional situation.

3. Lexicon influence
- For each lexicon item above, say whether it is helpful, neutral, or misleading.

4. Final label
- Choose exactly one of:
  VERY POSITIVE
  SOMEWHAT POSITIVE
  NEUTRAL
  SOMEWHAT NEGATIVE
  VERY NEGATIVE

5. Reasoning
- Explain why that label fits the sentence better than the others.
- If lexicon entries conflict with the sentence meaning, say so explicitly.
""".strip()


def main():
    load_dotenv()
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        raise SystemExit("DATABASE_URL not found")

    if len(sys.argv) < 2:
        raise SystemExit('Usage: python debug.py "Latin sentence here"')

    sentence = " ".join(sys.argv[1:])
    nlp = NLP("lat")
    doc = nlp.analyze(sentence)

    lemmas: List[str] = []
    for lemma in (doc.lemmata or []):
        if lemma:
            lemmas.append(normalize_lemma(lemma))

    with psycopg.connect(db_url) as conn:
        context_rows = fetch_lemma_context(conn, lemmas)

    print("=" * 80)
    print("SENTENCE")
    print(sentence)
    print("=" * 80)
    print("LEMMAS")
    print(lemmas)
    print("=" * 80)
    print("CONTEXT")
    print(format_context_rows(context_rows))
    print("=" * 80)

    prompt = build_debug_prompt(sentence, context_rows)
    response = ollama_generate(prompt)

    print("MODEL DEBUG RESPONSE")
    print(response)
    print("=" * 80)


if __name__ == "__main__":
    main()