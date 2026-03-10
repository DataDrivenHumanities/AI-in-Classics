import json
import csv
import time
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any

import requests

OLLAMA_API_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "latin-sentiment-llama31"

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

HERE = Path(__file__).resolve().parent
TEST_JSON = HERE / "LatinSentenceTestDatav2.json"
OUT_DIR = HERE


def load_test_cases(path: Path) -> List[Dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, list):
        return data
    return data.get("test_cases", [])


def expected_category_7(expected_sentiment: str) -> str:
    # "MODERATELY POSITIVE (+1)" -> "MODERATELY POSITIVE"
    s = (expected_sentiment or "").strip()
    s = re.sub(r"\s*\([^)]+\)\s*$", "", s)
    return s.strip().upper()


def normalize_prediction_7(text: str) -> str:
    s = (text or "").strip()
    s = s.splitlines()[0].strip()
    s = s.strip(" \t\r\n\"'`.,:;!")
    up = s.upper()

    if up in LABEL_SET_7:
        return up

    # salvage label if extra text appears
    for lab in LABELS_7:
        if lab in up:
            return lab

    return up  # unknown


def collapse_to_3(label_7: str) -> str:
    up = (label_7 or "").upper()
    if "POSITIVE" in up:
        return "POSITIVE"
    if "NEGATIVE" in up:
        return "NEGATIVE"
    if "NEUTRAL" in up:
        return "NEUTRAL"
    return "UNKNOWN"


def ollama_generate(prompt: str, timeout_s: int = 180) -> str:
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {"num_predict": 10, "temperature": 0.1, "top_p": 0.9},
    }
    r = requests.post(OLLAMA_API_URL, json=payload, timeout=timeout_s)
    r.raise_for_status()
    return (r.json().get("response") or "").strip()


def main():
    cases = load_test_cases(TEST_JSON)
    if not cases:
        raise SystemExit(f"No test cases found in {TEST_JSON}")

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_csv = OUT_DIR / f"results_{ts}.csv"
    summary_json = OUT_DIR / f"summary_{ts}.json"

    # per-class stats
    per7 = {lab: {"total": 0, "correct": 0} for lab in LABELS_7}
    per3 = {lab: {"total": 0, "correct": 0} for lab in LABELS_3}

    # confusion matrices
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

    with results_csv.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(
            f,
            fieldnames=[
                "idx",
                "sentence",
                "translation",
                "expected_sentiment",
                "expected_7",
                "predicted_raw",
                "predicted_7",
                "expected_3",
                "predicted_3",
                "is_correct_7",
                "is_correct_3",
                "latency_s",
            ],
        )
        w.writeheader()

        for idx, item in enumerate(cases, start=1):
            sent = item.get("sentence", "")
            trans = item.get("translation", item.get("expected_translation", "")) or ""
            exp_full = item.get("expected_sentiment", item.get("sentiment", "")) or ""
            exp7 = expected_category_7(exp_full)
            exp3 = collapse_to_3(exp7)

            if exp7 in per7:
                per7[exp7]["total"] += 1
            if exp3 in per3:
                per3[exp3]["total"] += 1

            t0 = time.perf_counter()
            try:
                raw = ollama_generate(sent)
            except Exception as e:
                raw = f"__ERROR__: {type(e).__name__}: {e}"
            latency = time.perf_counter() - t0

            pred7 = normalize_prediction_7(raw)
            pred3 = collapse_to_3(pred7)

            ok7 = (pred7 == exp7)
            ok3 = (pred3 == exp3)

            if ok7:
                correct7 += 1
                per7[exp7]["correct"] += 1
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
                    "predicted_raw": raw,
                    "predicted_7": pred7,
                    "expected_3": exp3,
                    "predicted_3": pred3,
                    "is_correct_7": ok7,
                    "is_correct_3": ok3,
                    "latency_s": f"{latency:.3f}",
                }
            )

            time.sleep(0.2)

    elapsed = time.perf_counter() - t_suite0

    def acc(c: int, t: int) -> float:
        return (c / t) if t else 0.0

    summary = {
        "model": OLLAMA_MODEL,
        "ollama_api": OLLAMA_API_URL,
        "input_file": str(TEST_JSON),
        "results_csv": str(results_csv),
        "total_tests": total,
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

    summary_path = OUT_DIR / f"summary_{ts}.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print(f"7-class accuracy: {correct7}/{total} = {acc(correct7,total)*100:.2f}%")
    print(f"3-class accuracy: {correct3}/{total} = {acc(correct3,total)*100:.2f}%")
    print(f"Wrote: {results_csv}")
    print(f"Wrote: {summary_path}")
    print(f"Elapsed: {elapsed:.1f}s")


if __name__ == "__main__":
    main()
