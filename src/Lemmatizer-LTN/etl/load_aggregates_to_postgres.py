#!/usr/bin/env python3
"""Load aggregate CSVs (lemmas.csv, forms.csv) into PostgreSQL."""
import os
import csv
import argparse
from pathlib import Path
import psycopg

BASE = Path(__file__).resolve().parents[1]
OUT_DIR = BASE / "out"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--outdir", default=str(OUT_DIR))
    ap.add_argument("--schema", default=str(BASE / "ops" / "init_db.sql"))
    ap.add_argument("--truncate", action="store_true")
    args = ap.parse_args()

    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        raise SystemExit("DATABASE_URL not set")

    outdir = Path(args.outdir)
    lemmas_csv = outdir / "lemmas.csv"
    forms_csv = outdir / "forms.csv"

    if not lemmas_csv.exists() or not forms_csv.exists():
        raise SystemExit(f"CSVs not found: {lemmas_csv}, {forms_csv}")

    with psycopg.connect(dsn, autocommit=True) as conn:
        # Apply schema
        if args.schema and Path(args.schema).exists():
            conn.execute(Path(args.schema).read_text(encoding="utf-8"))

        # Truncate
        if args.truncate:
            conn.execute("TRUNCATE TABLE forms RESTART IDENTITY CASCADE")
            conn.execute("TRUNCATE TABLE lemmas RESTART IDENTITY CASCADE")

        # Load lemmas
        print("Loading lemmas...")
        with open(lemmas_csv, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for i, row in enumerate(reader, 1):
                lemma_diac = row["lemma_diac"]
                
                conn.execute(
                    "INSERT INTO lemmas (lemma_code, lemma_nod, lemma_diac, pos, gender, page_url) "
                    "VALUES (%s, norm(%s), %s, %s, %s, %s) "
                    "ON CONFLICT (lemma_nod) DO UPDATE SET "
                    "lemma_code=EXCLUDED.lemma_code, lemma_diac=EXCLUDED.lemma_diac, "
                    "pos=EXCLUDED.pos, gender=EXCLUDED.gender, page_url=EXCLUDED.page_url",
                    (
                        row.get("lemma_code") or None,
                        lemma_diac,  # norm() computed in database
                        lemma_diac,
                        row.get("pos") or None,
                        row.get("gender") or None,
                        row.get("page_url") or None,
                    )
                )
                if i % 1000 == 0:
                    print(f"  {i} lemmas...")
        print(f"Loaded {i} lemmas")

        # Build lemma cache
        print("Building lemma cache...")
        cache = {}
        for row in conn.execute("SELECT id, lemma_nod FROM lemmas"):
            cache[str(row[1]).lower()] = row[0]

        # Load forms
        print("Loading forms...")
        with open(forms_csv, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for i, row in enumerate(reader, 1):
                lemma_nod = row["lemma_nod"]
                lemma_id = cache.get(lemma_nod.lower())
                if not lemma_id:
                    continue

                form_diac = row["form_diac"]
                
                conn.execute(
                    "INSERT INTO forms (lemma_id, form_nod, form_diac, mood, tense, voice, "
                    "person, number, gender, \"case\", degree, verb_form, page_url) "
                    "VALUES (%s, norm(%s), %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) "
                    "ON CONFLICT DO NOTHING",
                    (
                        lemma_id,
                        form_diac,  # norm() computed in database
                        form_diac,
                        row.get("mood") or None,
                        row.get("tense") or None,
                        row.get("voice") or None,
                        row.get("person") or None,
                        row.get("number") or None,
                        row.get("gender") or None,
                        row.get("case") or None,
                        row.get("degree") or None,
                        row.get("verb_form") or None,
                        row.get("page_url") or None,
                    )
                )
                if i % 10000 == 0:
                    print(f"  {i} forms...")
        print(f"Loaded {i} forms")


if __name__ == "__main__":
    main()

