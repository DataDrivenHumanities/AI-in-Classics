import json
from pathlib import Path

INPUT_FILE = Path("testdata5classes.json")
OUTPUT_FILE = Path("testdata3class.json")

def to_3class(label: str) -> str:
    s = (label or "").strip().upper()

    if "NEUTRAL" in s:
        return "NEUTRAL (0)"
    if "POSITIVE" in s:
        return "POSITIVE (+1.0)"
    if "NEGATIVE" in s:
        return "NEGATIVE (-1.0)"

    return "NEUTRAL (0)"

def main():
    with INPUT_FILE.open("r", encoding="utf-8") as f:
        data = json.load(f)

    test_cases = data["test_cases"] if isinstance(data, dict) else data

    for case in test_cases:
        old_label = case.get("expected_sentiment", "")
        case["expected_sentiment"] = to_3class(old_label)

    out = {"test_cases": test_cases} if isinstance(data, dict) else test_cases

    with OUTPUT_FILE.open("w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    main()