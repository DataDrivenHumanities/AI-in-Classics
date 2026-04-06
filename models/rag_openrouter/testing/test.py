#!/usr/bin/env python3
"""
openrouter_context_sentiment_eval.py

Evaluate an OpenRouter Latin sentiment classifier with *lemma-matched lexicon context*
retrieved from Postgres (lila.sentiment) for the lemmas found in each sentence.

Requirements:
  pip install requests psycopg[binary] python-dotenv cltk

Env:
  DATABASE_URL=postgresql://...
  OPENROUTER_API_KEY=sk-or-v1-...
"""

import os
import json
import csv
import time
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Tuple

import requests
import psycopg
from dotenv import load_dotenv

from cltk.lemmatize.latin.backoff import BackoffLatinLemmatizer as LatinBackoffLemmatizer


OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
# Set your desired OpenRouter models here
MODELS = [
    "google/gemini-2.5-pro",
    "google/gemini-2.5-flash",
    "openai/gpt-4o",
    "openai/o3-mini"
]

HERE = Path(__file__).resolve().parent
TEST_JSON = HERE / "LatinSentenceTestDatav2.json"
OUT_DIR = HERE

LABELS_7 = [
    "EXTREMELY POSITIVE",
    "VERY POSITIVE",
    "MODERATELY POSITIVE",
    "NEUTRAL",
    "MODERATELY NEGATIVE",
    "VERY NEGATIVE",
    "EXTREMELY NEGATIVE",
]
LABELS_3 = ["POSITIVE", "NEUTRAL", "NEGATIVE"]
LABEL_SET_7 = set(LABELS_7)
LABEL_SET_3 = set(LABELS_3)

WORD_RE = re.compile(r"[A-Za-z]+", re.UNICODE)

# Context controls
CONTEXT_MODE = "POLAR_ONLY"  # "ALL" or "POLAR_ONLY"
MAX_CONTEXT_ITEMS = 30       # maximum lemma rows to inject
SLEEP_S = 1.0                # throttle between requests for OpenRouter rate limits

SYSTEM_PROMPT = """You are an expert in Ancient Latin sentiment analysis trained on 9,000 examples. You classify Latin texts into seven emotional categories:

Categories:
- EXTREMELY POSITIVE (+3): exsultatio, jubilum, beatitudo, summa felicitas
- VERY POSITIVE (+2): gaudium, laetitia, amor, gloria, victoria, laudare
- MODERATELY POSITIVE (+1): felix, laetus, bonus, pulcher, spes
- NEUTRAL (0): factual statements
- MODERATELY NEGATIVE (-1): malus, tristis, anxius, timor
- VERY NEGATIVE (-2): dolor magnus, timor vehemens, ira, furor
- EXTREMELY NEGATIVE (-3): desperatio, exitium, cruciatus, malum

You may be given a Context section containing lemma-matched lexicon evidence from a database.
Each entry includes a polarity_score in {-1.0, -0.5, 0.0, 0.5, 1.0}:
- polarity_score > 0 indicates positive valence (0.5 mild, 1.0 strong).
- polarity_score < 0 indicates negative valence (-0.5 mild, -1.0 strong).
- polarity_score = 0 indicates neutral valence.

Use the lexicon evidence when it is relevant, but still classify the overall sentence sentiment.
Respond with ONLY the category name (exactly one of the seven labels)."""


def load_test_cases(path: Path) -> List[Dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, list):
        return data
    return data.get("test_cases", [])


def expected_category_7(expected_sentiment: str) -> str:
    s = (expected_sentiment or "").strip()
    s = re.sub(r"\s*\([^)]+\)\s*$", "", s)
    return s.strip().upper()


def normalize_prediction_7(text: str) -> str:
    s = (text or "").strip()
    up = s.upper()

    # Search the entire output first, in case it's buried in markdown or explanation
    for lab in LABELS_7:
        if lab in up:
            return lab

    # Fallback parsing
    if s:
        s = s.splitlines()[0].strip()
        s = s.strip(" \t\r\n\"'`.,:;!")
    return s.upper()  # unknown


def collapse_to_3(label_7: str) -> str:
    up = (label_7 or "").upper()
    if "POSITIVE" in up:
        return "POSITIVE"
    if "NEGATIVE" in up:
        return "NEGATIVE"
    if "NEUTRAL" in up:
        return "NEUTRAL"
    return "UNKNOWN"


def tokenize_simple(text: str) -> List[str]:
    return [m.group(0).lower() for m in WORD_RE.finditer(text or "")]


def normalize_lemma(s: str) -> str:
    s = (s or "").strip().lower()
    s = re.sub(r"\d+$", "", s)
    return s


def openrouter_generate(prompt: str, api_key: str, model_name: str, timeout_s: int = 180) -> str:
    headers = {
        "Authorization": f"Bearer {api_key}",
        "HTTP-Referer": "http://localhost",
        "X-Title": "Latin Sentiment Benchmark",
    }
    
    payload = {
        "model": model_name,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ]
    }
    
    r = requests.post(OPENROUTER_API_URL, headers=headers, json=payload, timeout=timeout_s)
    r.raise_for_status()
    
    resp_data = r.json()
    if "choices" in resp_data and len(resp_data["choices"]) > 0:
        return resp_data["choices"][0].get("message", {}).get("content", "").strip()
    return ""


def fetch_lemma_context(conn: psycopg.Connection, lemmas: List[str]) -> List[Dict[str, Any]]:
    lemmas = [normalize_lemma(x) for x in lemmas if x]
    lemmas = sorted(set(lemmas))
    if not lemmas:
        return []

    with conn.cursor() as cur:
        # psycopg3: use ANY(%s) and pass a list; common pattern is wrapping list in another list
        cur.execute(
            """
            SELECT lemma, pos, polarity_score, has_polarity, provenance
            FROM lila.sentiment
            WHERE lemma = ANY(%s)
            """,
            (lemmas,),
        )
        rows = cur.fetchall()

    out = []
    for lemma, pos, polarity_score, has_polarity, provenance in rows:
        rec = {
            "lemma": normalize_lemma(lemma),
            "pos": pos,
            "polarity_score": polarity_score,
            "has_polarity": has_polarity,
            "provenance": provenance,
        }
        if CONTEXT_MODE == "POLAR_ONLY":
            # Keep only entries that really look like they carry sentiment.
            if rec["polarity_score"] is None:
                continue
            if rec["has_polarity"] in (None, "", "0", "false", "False", "no", "No"):
                # still allow if polarity_score exists
                pass
        out.append(rec)

    # stable ordering: stronger polarity first if available, else lemma
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
        return "Lexicon evidence (lila.sentiment): (no lemma matches found)\n"

    lines = ["Lexicon evidence (lila.sentiment; lemma-matched):"]
    for r in rows:
        lines.append(
            f"- lemma={r['lemma']} pos={r.get('pos')} polarity_score={r.get('polarity_score')} "
            f"has_polarity={r.get('has_polarity')} provenance={r.get('provenance')}"
        )
    return "\n".join(lines) + "\n"


def build_prompt(sentence: str, context_rows: List[Dict[str, Any]]) -> str:
    ctx = format_context_rows(context_rows)
    return f"Context (lemma lexicon evidence) + Latin text:\n{ctx}\nLatin text: {sentence}\n\nSentiment:"


def main():
    load_dotenv()  # typical pattern for loading DATABASE_URL and OPENROUTER_API_KEY from .env
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        raise SystemExit("DATABASE_URL not found. Put it in .env or set it in your shell.")
        
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        raise SystemExit("OPENROUTER_API_KEY not found. Put it in .env to run this OpenRouter benchmark script.")

    cases = load_test_cases(TEST_JSON)
    if not cases:
        raise SystemExit(f"No test cases found in {TEST_JSON}")

    lemmatizer = LatinBackoffLemmatizer()

    for model_name in MODELS:
        print(f"\n--- Testing Model: {model_name} ---")
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_model_name = model_name.replace("/", "_")
        results_csv = OUT_DIR / f"results_lemmactx_{safe_model_name}_{ts}.csv"
        summary_path = OUT_DIR / f"summary_lemmactx_{safe_model_name}_{ts}.json"
    
        per7 = {lab: {"total": 0, "correct": 0} for lab in LABELS_7}
        per3 = {lab: {"total": 0, "correct": 0} for lab in LABELS_3}
    
        conf7 = {e: {p: 0 for p in LABELS_7} for e in LABELS_7}
        conf7_unknown = {e: 0 for e in LABELS_7}
    
        conf3 = {e: {p: 0 for p in LABELS_3} for e in LABELS_3}
        conf3_unknown = {e: 0 for e in LABELS_3}
    
        total = len(cases)
        correct7 = 0
        correct3 = 0
        unknown7 = 0
        unknown3 = 0
    
        t_suite0 = time.perf_counter()
    
        with psycopg.connect(db_url) as conn, results_csv.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(
                f,
                fieldnames=[
                    "idx",
                    "sentence",
                    "translation",
                    "expected_sentiment",
                    "expected_7",
                    "expected_3",
                    "lemmas",
                    "context_hits",
                    "prompt_chars",
                    "predicted_raw",
                    "predicted_7",
                    "predicted_3",
                    "is_correct_7",
                    "is_correct_3",
                    "latency_s",
                ],
            )
            w.writeheader()
    
            for idx, item in enumerate(cases, start=1):
                sent = item.get("sentence", "") or ""
                trans = item.get("translation", item.get("expected_translation", "")) or ""
                exp_full = item.get("expected_sentiment", item.get("sentiment", "")) or ""
                exp7 = expected_category_7(exp_full)
                exp3 = collapse_to_3(exp7)
    
                if exp7 in per7:
                    per7[exp7]["total"] += 1
                if exp3 in per3:
                    per3[exp3]["total"] += 1
    
                toks = tokenize_simple(sent)
                pairs: List[Tuple[str, str]] = lemmatizer.lemmatize(toks)
                lemmas = [normalize_lemma(lem) for _, lem in pairs if lem]
                context_rows = fetch_lemma_context(conn, lemmas)
    
                prompt = build_prompt(sent, context_rows)
    
                t0 = time.perf_counter()
                try:
                    raw = openrouter_generate(prompt, api_key, model_name)
                except Exception as e:
                    raw = f"__ERROR__: {type(e).__name__}: {e}"
                latency = time.perf_counter() - t0
    
                pred7 = normalize_prediction_7(raw)
                pred3 = collapse_to_3(pred7)
    
                ok7 = (pred7 == exp7)
                ok3 = (pred3 == exp3)
    
                if ok7:
                    correct7 += 1
                    if exp7 in per7:
                        per7[exp7]["correct"] += 1
                    if exp7 in LABEL_SET_7 and pred7 in LABEL_SET_7:
                        conf7[exp7][pred7] += 1
                else:
                    if pred7 in LABEL_SET_7 and exp7 in LABEL_SET_7:
                        conf7[exp7][pred7] += 1
                    else:
                        unknown7 += 1
                        if exp7 in conf7_unknown:
                            conf7_unknown[exp7] += 1
    
                if exp3 in LABEL_SET_3:
                    if ok3:
                        correct3 += 1
                        per3[exp3]["correct"] += 1
                        if pred3 in LABEL_SET_3:
                            conf3[exp3][pred3] += 1
                    else:
                        if pred3 in LABEL_SET_3:
                            conf3[exp3][pred3] += 1
                        else:
                            unknown3 += 1
                            conf3_unknown[exp3] += 1
    
                w.writerow(
                    {
                        "idx": idx,
                        "sentence": sent,
                        "translation": trans,
                        "expected_sentiment": exp_full,
                        "expected_7": exp7,
                        "expected_3": exp3,
                        "lemmas": " ".join(sorted(set(lemmas))),
                        "context_hits": len(context_rows),
                        "prompt_chars": len(prompt),
                        "predicted_raw": raw,
                        "predicted_7": pred7,
                        "predicted_3": pred3,
                        "is_correct_7": ok7,
                        "is_correct_3": ok3,
                        "latency_s": f"{latency:.3f}",
                    }
                )
    
                time.sleep(SLEEP_S)
    
        elapsed = time.perf_counter() - t_suite0
    
        def acc(c: int, t: int) -> float:
            return (c / t) if t else 0.0
    
        summary = {
            "model": model_name,
            "api": "openrouter.ai/api/v1/chat/completions",
            "input_file": str(TEST_JSON),
            "results_csv": str(results_csv),
            "total_tests": total,
            "context_mode": CONTEXT_MODE,
            "max_context_items": MAX_CONTEXT_ITEMS,
            "overall": {
                "correct_7": correct7,
                "accuracy_7": acc(correct7, total),
                "unknown_7": unknown7,
                "correct_3": correct3,
                "accuracy_3": acc(correct3, total),
                "unknown_3": unknown3,
            },
            "per_label_7": {
                lab: {
                    "correct": per7[lab]["correct"],
                    "total": per7[lab]["total"],
                    "accuracy": acc(per7[lab]["correct"], per7[lab]["total"]),
                }
                for lab in LABELS_7
            },
            "per_label_3": {
                lab: {
                    "correct": per3[lab]["correct"],
                    "total": per3[lab]["total"],
                    "accuracy": acc(per3[lab]["correct"], per3[lab]["total"]),
                }
                for lab in LABELS_3
            },
            "confusion_7": {"matrix": conf7, "unknown_by_expected": conf7_unknown},
            "confusion_3": {"matrix": conf3, "unknown_by_expected": conf3_unknown},
            "elapsed_seconds": elapsed,
        }
    
        summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    
        print(f"7-class accuracy: {correct7}/{total} = {acc(correct7,total)*100:.2f}%")
        print(f"3-class accuracy: {correct3}/{total} = {acc(correct3,total)*100:.2f}%")
        print(f"Wrote: {results_csv}")
        print(f"Wrote: {summary_path}")
        print(f"Elapsed: {elapsed:.1f}s")


if __name__ == "__main__":
    main()
