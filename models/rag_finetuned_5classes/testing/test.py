#!/usr/bin/env python3

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
from cltk import NLP


OLLAMA_API_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "latin-sentiment-5class"

HERE = Path(__file__).resolve().parent
TEST_JSON = HERE / "testdata5classes.json"
OUT_DIR = HERE

LABELS_5 = [
    "VERY POSITIVE",
    "SOMEWHAT POSITIVE",
    "NEUTRAL",
    "SOMEWHAT NEGATIVE",
    "VERY NEGATIVE",
]

LABELS_3 = ["POSITIVE", "NEUTRAL", "NEGATIVE"]

LABEL_SET_5 = set(LABELS_5)
LABEL_SET_3 = set(LABELS_3)

WORD_RE = re.compile(r"[A-Za-z]+", re.UNICODE)

CONTEXT_MODE = "POLAR_ONLY"   # "ALL" or "POLAR_ONLY"
MAX_CONTEXT_ITEMS = 30
SLEEP_S = 0.2


def load_test_cases(path: Path) -> List[Dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, list):
        return data
    return data.get("test_cases", [])


def normalize_lemma(s: str) -> str:
    s = (s or "").strip().lower()
    s = re.sub(r"\d+$", "", s)
    return s


def tokenize_simple(text: str) -> List[str]:
    return [m.group(0).lower() for m in WORD_RE.finditer(text or "")]


def score_to_label_5(score) -> str:
    try:
        x = float(score)
    except Exception:
        return "UNKNOWN"

    if x == 1:
        return "VERY POSITIVE"
    if x == 0.5:
        return "SOMEWHAT POSITIVE"
    if x == 0:
        return "NEUTRAL"
    if x == -0.5:
        return "SOMEWHAT NEGATIVE"
    if x == -1:
        return "VERY NEGATIVE"
    return "UNKNOWN"


def expected_category_5(expected_sentiment) -> str:
    s = str(expected_sentiment or "").strip()

    try:
        return score_to_label_5(float(s))
    except Exception:
        pass

    s = re.sub(r"\s*\([^)]+\)\s*$", "", s).strip().upper()

    allowed = {
        "VERY POSITIVE",
        "SOMEWHAT POSITIVE",
        "NEUTRAL",
        "SOMEWHAT NEGATIVE",
        "VERY NEGATIVE",
    }

    if s in allowed:
        return s

    return "UNKNOWN"

def normalize_prediction_5(text: str) -> str:
    s = (text or "").strip()
    up = s.upper()

    for lab in LABELS_5:
        if lab in up:
            return lab

    if s:
        s = s.splitlines()[0].strip()
        s = s.strip(" \t\r\n\"'`.,:;!")
    return s.upper()

def collapse_to_3(label_5: str) -> str:
    up = (label_5 or "").upper()
    if "POSITIVE" in up:
        return "POSITIVE"
    if "NEGATIVE" in up:
        return "NEGATIVE"
    if up == "NEUTRAL":
        return "NEUTRAL"
    return "UNKNOWN"


def ollama_generate(prompt: str, timeout_s: int = 180) -> str:
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {"num_predict": 12, "temperature": 0, "top_p": 0.9},
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
            if rec["polarity_score"] is None:
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
        return (
            "Lexicon evidence (lila.sentiment): (no lemma matches found)\n\n"
            "Return exactly one label from this set:\n"
            "VERY POSITIVE\n"
            "SOMEWHAT POSITIVE\n"
            "NEUTRAL\n"
            "SOMEWHAT NEGATIVE\n"
            "VERY NEGATIVE\n"
        )

    lines = [
        "Lexicon evidence (lila.sentiment; lemma-matched):"
    ]
    for r in rows:
        lines.append(
            f"- lemma={r['lemma']} pos={r.get('pos')} polarity_score={r.get('polarity_score')} "
            f"has_polarity={r.get('has_polarity')} provenance={r.get('provenance')}"
        )

    lines.extend([
        "",
        "Return exactly one label from this set:",
        "VERY POSITIVE",
        "SOMEWHAT POSITIVE",
        "NEUTRAL",
        "SOMEWHAT NEGATIVE",
        "VERY NEGATIVE",
    ])
    return "\n".join(lines) + "\n"


def build_prompt(sentence: str, context_rows: List[Dict[str, Any]]) -> str:
    ctx = format_context_rows(context_rows)
    return (
        f"{ctx}\n"
        f"Latin text: {sentence}\n\n"
        "Classify the overall sentiment of the Latin text. "
        "Output only one label and no explanation.\n"
    )


def main():
    load_dotenv()
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        raise SystemExit("DATABASE_URL not found. Put it in .env or set it in your shell.")

    cases = load_test_cases(TEST_JSON)
    if not cases:
        raise SystemExit(f"No test cases found in {TEST_JSON}")

    # CLTK 1.x Latin pipeline
    lemmatizer = NLP("lat")

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_csv = OUT_DIR / f"results_lemmactx_5class_{ts}.csv"
    summary_path = OUT_DIR / f"summary_lemmactx_5class_{ts}.json"

    per5 = {lab: {"total": 0, "correct": 0} for lab in LABELS_5}
    per3 = {lab: {"total": 0, "correct": 0} for lab in LABELS_3}

    conf5 = {e: {p: 0 for p in LABELS_5} for e in LABELS_5}
    conf5_unknown = {e: 0 for e in LABELS_5}

    conf3 = {e: {p: 0 for p in LABELS_3} for e in LABELS_3}
    conf3_unknown = {e: 0 for e in LABELS_3}

    total = len(cases)
    correct5 = 0
    correct3 = 0
    unknown5 = 0
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
                "expected_5",
                "expected_3",
                "lemmas",
                "context_hits",
                "prompt_chars",
                "predicted_raw",
                "predicted_5",
                "predicted_3",
                "is_correct_5",
                "is_correct_3",
                "latency_s",
            ],
        )
        w.writeheader()

        for idx, item in enumerate(cases, start=1):
            sent = item.get("sentence", "") or ""
            trans = item.get("translation", item.get("expected_translation", "")) or ""
            exp_full = (item.get("expected_sentiment", item.get("sentiment", "")) or "").strip()
            exp5 = expected_category_5(exp_full)  # still for 3-class & confusion
            exp3 = collapse_to_3(exp5)

            if exp5 in per5:
                per5[exp5]["total"] += 1
            if exp3 in per3:
                per3[exp3]["total"] += 1

            # CLTK 1.x: get lemmas from annotations
            doc = lemmatizer.analyze(sent)

            lemmas: List[str] = []
            for lemma in (doc.lemmata or []):
                if lemma:
                    lemmas.append(normalize_lemma(lemma))

            context_rows = fetch_lemma_context(conn, lemmas)

            prompt = build_prompt(sent, context_rows)

            t0 = time.perf_counter()
            try:
                raw = ollama_generate(prompt)
            except Exception as e:
                raw = f"__ERROR__: {type(e).__name__}: {e}"
            latency = time.perf_counter() - t0

            pred5 = normalize_prediction_5(raw)
            pred3 = collapse_to_3(pred5)

            ok5 = (pred5 == exp5)
            ok3 = (pred3 == exp3)

            if ok5:
                correct5 += 1
                if exp5 in per5:
                    per5[exp5]["correct"] += 1
                if exp5 in LABEL_SET_5 and pred5 in LABEL_SET_5:
                    conf5[exp5][pred5] += 1
            else:
                if pred5 in LABEL_SET_5 and exp5 in LABEL_SET_5:
                    conf5[exp5][pred5] += 1
                else:
                    unknown5 += 1
                    if exp5 in conf5_unknown:
                        conf5_unknown[exp5] += 1

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
                    "expected_5": exp5,
                    "expected_3": exp3,
                    "lemmas": " ".join(sorted(set(lemmas))),
                    "context_hits": len(context_rows),
                    "prompt_chars": len(prompt),
                    "predicted_raw": raw,
                    "predicted_5": pred5,
                    "predicted_3": pred3,
                    "is_correct_5": ok5,
                    "is_correct_3": ok3,
                    "latency_s": f"{latency:.3f}",
                }
            )

            time.sleep(SLEEP_S)

    elapsed = time.perf_counter() - t_suite0

    def acc(c: int, t: int) -> float:
        return (c / t) if t else 0.0

    summary = {
        "model": OLLAMA_MODEL,
        "ollama_api": OLLAMA_API_URL,
        "input_file": str(TEST_JSON),
        "results_csv": str(results_csv),
        "total_tests": total,
        "context_mode": CONTEXT_MODE,
        "max_context_items": MAX_CONTEXT_ITEMS,
        "label_scheme": {
            "-1": "VERY NEGATIVE",
            "-0.5": "SOMEWHAT NEGATIVE",
            "0": "NEUTRAL",
            "0.5": "SOMEWHAT POSITIVE",
            "1": "VERY POSITIVE",
        },
        "overall": {
            "correct_5": correct5,
            "accuracy_5": acc(correct5, total),
            "unknown_5": unknown5,
            "correct_3": correct3,
            "accuracy_3": acc(correct3, total),
            "unknown_3": unknown3,
        },
        "per_label_5": {
            lab: {
                "correct": per5[lab]["correct"],
                "total": per5[lab]["total"],
                "accuracy": acc(per5[lab]["correct"], per5[lab]["total"]),
            }
            for lab in LABELS_5
        },
        "per_label_3": {
            lab: {
                "correct": per3[lab]["correct"],
                "total": per3[lab]["total"],
                "accuracy": acc(per3[lab]["correct"], per3[lab]["total"]),
            }
            for lab in LABELS_3
        },
        "confusion_5": {"matrix": conf5, "unknown_by_expected": conf5_unknown},
        "confusion_3": {"matrix": conf3, "unknown_by_expected": conf3_unknown},
        "elapsed_seconds": elapsed,
    }

    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print(f"5-class accuracy: {correct5}/{total} = {acc(correct5, total) * 100:.2f}%")
    print(f"3-class accuracy: {correct3}/{total} = {acc(correct3, total) * 100:.2f}%")
    print(f"Wrote: {results_csv}")
    print(f"Wrote: {summary_path}")
    print(f"Elapsed: {elapsed:.1f}s")

if __name__ == "__main__":
    main()