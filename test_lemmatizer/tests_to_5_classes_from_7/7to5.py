#!/usr/bin/env python3
"""
normalize_sentiment_5class_numeric.py

Convert expected_sentiment like 'MODERATELY POSITIVE (+1)' or
'EXTREMELY NEGATIVE (-3)' into a 5-class scheme with numeric values:

    VERY POSITIVE (+1)
    SOMEWHAT POSITIVE (+0.5)
    NEUTRAL (0)
    SOMEWHAT NEGATIVE (-0.5)
    VERY NEGATIVE (-1)

Writes a new JSON file alongside the original.
"""

import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
IN_PATH = HERE / "LatinSentenceTestDatav2.json"
OUT_PATH = HERE / "LatinSentenceTestDatav2_5class_numeric.json"


def to_5class_numeric(label: str) -> str:
    """
    Map old labels like 'MODERATELY POSITIVE (+1)' or
    'EXTREMELY NEGATIVE (-3)' to the new 5-class label + numeric value.
    """
    s = (label or "").strip()
    # Drop trailing " (+1)" etc.
    s = re.sub(r"\s*\([^)]+\)\s*$", "", s)
    s = s.strip().upper()

    # First map to 5-class textual label
    text_map = {
        "VERY POSITIVE": "VERY POSITIVE",
        "MODERATELY POSITIVE": "SOMEWHAT POSITIVE",
        "SOMEWHAT POSITIVE": "SOMEWHAT POSITIVE",

        "NEUTRAL": "NEUTRAL",

        "MODERATELY NEGATIVE": "SOMEWHAT NEGATIVE",
        "SOMEWHAT NEGATIVE": "SOMEWHAT NEGATIVE",
        "VERY NEGATIVE": "VERY NEGATIVE",
        "EXTREMELY NEGATIVE": "VERY NEGATIVE",
    }
    text_label = text_map.get(s)
    if text_label is None:
        # Unexpected label: treat as NEUTRAL and keep raw in a comment-like suffix
        return "NEUTRAL (0)"

    # Then assign numeric value in [-1, -0.5, 0, 0.5, 1]
    num_map = {
        "VERY POSITIVE": 1.0,
        "SOMEWHAT POSITIVE": 0.5,
        "NEUTRAL": 0.0,
        "SOMEWHAT NEGATIVE": -0.5,
        "VERY NEGATIVE": -1.0,
    }
    v = num_map[text_label]

    # Format as e.g. "VERY POSITIVE (+1)" or "SOMEWHAT NEGATIVE (-0.5)"
    if v == int(v):
        num_str = f"{int(v)}"
    else:
        num_str = f"{v}"
    sign = "+" if v > 0 else ""
    return f"{text_label} ({sign}{num_str})"


def main():
    data = json.loads(IN_PATH.read_text(encoding="utf-8"))

    if isinstance(data, list):
        cases = data
        wrapper_key = None
    else:
        cases = data.get("test_cases", [])
        wrapper_key = "test_cases"

    for item in cases:
        old = item.get("expected_sentiment", "")
        item["expected_sentiment"] = to_5class_numeric(old)

    if wrapper_key is None:
        out_obj = cases
    else:
        out_obj = {"test_cases": cases}

    OUT_PATH.write_text(json.dumps(out_obj, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote 5-class numeric labels to {OUT_PATH}")


if __name__ == "__main__":
    main()