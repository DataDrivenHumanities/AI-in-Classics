import csv
from collections import defaultdict
from pathlib import Path

CSV_PATH = Path("results_lemmactx_5class_20260401_192838.csv")  # adjust name

def main():
    groups = defaultdict(list)

    with CSV_PATH.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            exp = row["expected_5"]
            pred = row["predicted_5"]
            key = (exp, pred)
            groups[key].append(row)

    # Print a summary
    print("=== 5-class confusion by (expected, predicted) ===")
    for (exp, pred), rows in sorted(groups.items(), key=lambda kv: (kv[0][0], kv[0][1])):
        print(f"{exp:18s} -> {pred:18s}: {len(rows)}")

    # Optionally, write each group to its own CSV for inspection
    out_dir = CSV_PATH.parent / "groups_5class"
    out_dir.mkdir(exist_ok=True)

    for (exp, pred), rows in groups.items():
        safe_exp = exp.replace(" ", "_")
        safe_pred = pred.replace(" ", "_")
        out_file = out_dir / f"exp-{safe_exp}__pred-{safe_pred}.csv"
        with out_file.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)

    print(f"\nWrote grouped CSVs to: {out_dir}")

if __name__ == "__main__":
    main()