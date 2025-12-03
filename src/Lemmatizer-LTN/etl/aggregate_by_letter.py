#!/usr/bin/env python3
"""
Aggregate individual per-lemma CSV files into letter-based CSVs (a.csv, b.csv, ..., z.csv).
This dramatically reduces the number of files to upload to Google Drive.
"""

from pathlib import Path
import csv
import glob
from collections import defaultdict

BASE = Path(__file__).resolve().parents[1]  # .../Lemmatizer-LTN
OUT_DIR = BASE / "out"
LETTER_DIR = OUT_DIR / "by_letter"

def get_first_letter(filename: str) -> str:
    """Extract the first alphabetic character from filename."""
    stem = Path(filename).stem
    for ch in stem:
        if ch.isalpha():
            return ch.lower()
    return "misc"

def aggregate_by_letter():
    """Aggregate all per-lemma CSV files into letter-based files."""
    LETTER_DIR.mkdir(parents=True, exist_ok=True)
    
    # Find all per-lemma CSVs (exclude aggregates)
    paths = [
        Path(p) for p in glob.glob(str(OUT_DIR / "*.csv"))
        if Path(p).name not in ("lemmas.csv", "forms.csv")
    ]
    
    if not paths:
        print("No per-lemma CSV files found to aggregate")
        return
    
    print(f"Found {len(paths)} per-lemma CSV files to aggregate")
    
    # Group files by first letter
    letter_groups = defaultdict(list)
    for p in paths:
        letter = get_first_letter(p.name)
        letter_groups[letter].append(p)
    
    print(f"Aggregating into {len(letter_groups)} letter-based files...")
    
    # Process each letter group
    for letter in sorted(letter_groups.keys()):
        files = letter_groups[letter]
        output_file = LETTER_DIR / f"{letter}.csv"
        
        all_rows = []
        headers = None
        
        # Read all files for this letter
        for csv_file in files:
            try:
                with open(csv_file, "r", newline="", encoding="utf-8") as f:
                    reader = csv.DictReader(f)
                    if headers is None:
                        headers = reader.fieldnames
                    
                    for row in reader:
                        all_rows.append(row)
            except Exception as e:
                print(f"Warning: Failed to read {csv_file.name}: {e}")
        
        # Write aggregated file
        if all_rows and headers:
            with open(output_file, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=headers)
                writer.writeheader()
                writer.writerows(all_rows)
            
            print(f"  {letter}.csv: {len(files)} source files, {len(all_rows)} total rows")
        else:
            print(f"  {letter}: No data to write")
    
    print(f"\nAggregation complete!")
    print(f"Output directory: {LETTER_DIR}")
    print(f"Total files created: {len(letter_groups)}")
    
    # Summary
    total_original = len(paths)
    total_aggregated = len(letter_groups)
    reduction = (1 - total_aggregated / total_original) * 100 if total_original > 0 else 0
    print(f"\nFile reduction: {total_original} → {total_aggregated} ({reduction:.1f}% reduction)")

if __name__ == "__main__":
    aggregate_by_letter()

