import sys
import csv
from pathlib import Path

OUTDIR = Path("src/Lemmatizer-GRK/out")

EXPECTED_HEADERS = [
    "lemma_text", "form", "pos", "case", "number", "gender",
    "person", "tense", "mood", "voice", "page_url", "raw_parse"
]

def main():
    if not OUTDIR.exists():
        print("❌ VALIDATION FAILED: Output directory does not exist.")
        sys.exit(1)

    csv_files = list(OUTDIR.glob("*.csv"))
    meta_file = OUTDIR / "_meta_expected_count.txt"

    if not meta_file.exists():
        print("❌ VALIDATION FAILED: Expected count metadata file missing.")
        sys.exit(1)

    expected = int(meta_file.read_text(encoding="utf-8").strip())
    actual = len(csv_files)
    
    # We will collect errors here instead of crashing immediately
    errors = []
    
    print(f"📊 Expecting {expected} files. Found {actual} files.")
    if actual < expected * 0.85:
        errors.append(f"Missing Files: Expected {expected}, got {actual} (More than 15% missing - likely a network failure).")
    elif actual < expected:
        print(f"⚠️ Note: {expected - actual} files were missing. (Likely intentionally skipped punctuation/garbage).")
        
    if not csv_files:
        print("❌ VALIDATION FAILED: No CSV files were generated.")
        sys.exit(1)

    total_rows = 0
    empty_files = 0
    bad_headers = 0
    empty_forms = 0

    # Audit all files
    for file in csv_files:
        with file.open(encoding="utf-8") as f:
            reader = csv.DictReader(f)

            if reader.fieldnames != EXPECTED_HEADERS:
                bad_headers += 1
                errors.append(f"Header mismatch in: {file.name}")
                continue # Skip row checks if headers are bad

            rows = list(reader)
            if not rows:
                empty_files += 1
                errors.append(f"Empty file: {file.name}")
                continue

            for row in rows:
                if not row.get("form") or row["form"].strip() == "":
                    empty_forms += 1
            
            total_rows += len(rows)

    if total_rows < 100:  # threshold
        errors.append(f"Too few total rows scraped: {total_rows}")

    # Print Final Report
    print("\n--- VALIDATION REPORT ---")
    print(f"Total Rows Scraped: {total_rows}")
    print(f"Files Audited:      {len(csv_files)}")
    print(f"Empty Files:        {empty_files}")
    print(f"Empty Forms:        {empty_forms}")
    print("-------------------------\n")

    if errors:
        print("❌ VALIDATION FAILED WITH THE FOLLOWING ERRORS:")
        # Print up to the first 20 errors so the logs don't get spammed
        for e in errors[:20]:
            print(f"  - {e}")
        if len(errors) > 20:
            print(f"  ... and {len(errors) - 20} more errors.")
        sys.exit(1)
    else:
        print("✅ ALL CHECKS PASSED.")
        sys.exit(0)

if __name__ == "__main__":
    main()