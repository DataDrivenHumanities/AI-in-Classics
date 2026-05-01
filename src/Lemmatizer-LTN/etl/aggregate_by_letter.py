#!/usr/bin/env python3
"""
Split forms.csv into letter-based CSVs (a.csv, b.csv, ..., z.csv)
grouped by the first letter of lemma_nod.
"""

from pathlib import Path
import csv
from collections import defaultdict

BASE = Path(__file__).resolve().parents[1]  # .../Lemmatizer-LTN
OUT_DIR = BASE / "out"
LETTER_DIR = OUT_DIR / "by_letter"
FORMS_CSV = OUT_DIR / "forms.csv"


def aggregate_by_letter(forms_csv=None, letter_dir=None):
    forms_csv = Path(forms_csv or FORMS_CSV)
    letter_dir = Path(letter_dir or LETTER_DIR)
    letter_dir.mkdir(parents=True, exist_ok=True)

    if not forms_csv.exists():
        print(f"forms.csv not found at {forms_csv}, skipping letter split")
        return

    # Read forms.csv and group rows by first letter of lemma_nod
    letter_rows = defaultdict(list)
    headers = None
    total = 0

    with open(forms_csv, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        headers = reader.fieldnames
        for row in reader:
            lemma_nod = row.get("lemma_nod", "")
            letter = lemma_nod[0].lower() if lemma_nod and lemma_nod[0].isalpha() else "misc"
            letter_rows[letter].append(row)
            total += 1

    if not headers or total == 0:
        print("No form data to split")
        return

    # Write one CSV per letter
    for letter in sorted(letter_rows):
        rows = letter_rows[letter]
        out_path = letter_dir / f"{letter}.csv"
        with open(out_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
            writer.writerows(rows)

    letters = sorted(letter_rows.keys())
    print(f"Split {total} forms into {len(letters)} letter files: {', '.join(letters)}")
    print(f"Output: {letter_dir}")


if __name__ == "__main__":
    aggregate_by_letter()
