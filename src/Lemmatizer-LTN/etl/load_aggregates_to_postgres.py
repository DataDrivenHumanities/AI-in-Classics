#!/usr/bin/env python3
"""Load aggregate CSVs (lemmas.csv, forms.csv) into PostgreSQL using COPY for speed."""
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

    with psycopg.connect(dsn) as conn:
        # Apply schema
        if args.schema and Path(args.schema).exists():
            with conn.cursor() as cur:
                cur.execute(Path(args.schema).read_text(encoding="utf-8"))
            conn.commit()

        # Truncate
        if args.truncate:
            print("Truncating tables...")
            with conn.cursor() as cur:
                cur.execute("TRUNCATE TABLE forms RESTART IDENTITY CASCADE")
                cur.execute("TRUNCATE TABLE lemmas RESTART IDENTITY CASCADE")
            conn.commit()

        # Load lemmas using COPY
        print("Loading lemmas...")
        with conn.cursor() as cur:
            # Create temp table with same structure but text columns for norm() computation
            cur.execute("""
                CREATE TEMP TABLE lemmas_staging (
                    lemma_code TEXT,
                    lemma_diac TEXT,
                    pos TEXT,
                    gender TEXT,
                    page_url TEXT
                ) ON COMMIT DROP
            """)
            
            # COPY CSV into temp table (skip header, skip lemma_nod column)
            # CSV columns: lemma_code, lemma_nod, lemma_diac, pos, gender, page_url
            with open(lemmas_csv, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                next(reader)  # Skip header
                with cur.copy("COPY lemmas_staging (lemma_code, lemma_diac, pos, gender, page_url) FROM STDIN WITH (FORMAT CSV)") as copy:
                    for row in reader:
                        if len(row) < 6:
                            continue
                        # Skip lemma_nod (index 1), keep: 0, 2, 3, 4, 5
                        copy.write_row([
                            row[0] or "",  # lemma_code
                            row[2] or "",  # lemma_diac
                            row[3] or "",  # pos
                            row[4] or "",  # gender
                            row[5] or ""   # page_url
                        ])
            
            # Insert from staging into lemmas with norm() computation
            cur.execute("""
                INSERT INTO lemmas (lemma_code, lemma_nod, lemma_diac, pos, gender, page_url)
                SELECT 
                    NULLIF(lemma_code, ''),
                    norm(lemma_diac),
                    lemma_diac,
                    NULLIF(pos, ''),
                    NULLIF(gender, ''),
                    NULLIF(page_url, '')
                FROM lemmas_staging
                ON CONFLICT (lemma_nod) DO UPDATE SET
                    lemma_code = EXCLUDED.lemma_code,
                    lemma_diac = EXCLUDED.lemma_diac,
                    pos = EXCLUDED.pos,
                    gender = EXCLUDED.gender,
                    page_url = EXCLUDED.page_url
            """)
            
            lemma_count = cur.rowcount
            print(f"Loaded {lemma_count} lemmas")
        
        conn.commit()

        # Build lemma cache
        print("Building lemma cache...")
        cache = {}
        with conn.cursor() as cur:
            cur.execute("SELECT id, lemma_nod FROM lemmas")
            for row in cur.fetchall():
                cache[str(row[1]).lower()] = row[0]
        
        print(f"Cached {len(cache)} lemma IDs")

        # Load forms using COPY
        print("Loading forms...")
        with conn.cursor() as cur:
            # Create temp table
            cur.execute("""
                CREATE TEMP TABLE forms_staging (
                    lemma_nod TEXT,
                    form_diac TEXT,
                    label TEXT,
                    mood TEXT,
                    tense TEXT,
                    voice TEXT,
                    person TEXT,
                    number TEXT,
                    gender TEXT,
                    "case" TEXT,
                    degree TEXT,
                    verb_form TEXT,
                    page_url TEXT
                ) ON COMMIT DROP
            """)
            
            # COPY CSV into temp table (skip form_nod column)
            # CSV columns: lemma_nod, form_nod, form_diac, label, mood, tense, voice, person, number, gender, case, degree, verb_form, page_url
            with open(forms_csv, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                next(reader)  # Skip header
                with cur.copy("COPY forms_staging (lemma_nod, form_diac, label, mood, tense, voice, person, number, gender, \"case\", degree, verb_form, page_url) FROM STDIN WITH (FORMAT CSV)") as copy:
                    for row in reader:
                        if len(row) < 14:
                            continue
                        # Skip form_nod (index 1), keep: 0, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13
                        copy.write_row([
                            row[0] or "",   # lemma_nod
                            row[2] or "",   # form_diac
                            row[3] or "",   # label
                            row[4] or "",   # mood
                            row[5] or "",   # tense
                            row[6] or "",   # voice
                            row[7] or "",   # person
                            row[8] or "",   # number
                            row[9] or "",   # gender
                            row[10] or "",  # case
                            row[11] or "",  # degree
                            row[12] or "",  # verb_form
                            row[13] or ""   # page_url
                        ])
            
            # Insert from staging into forms with lemma_id lookup and norm() computation
            cur.execute("""
                INSERT INTO forms (lemma_id, form_nod, form_diac, mood, tense, voice, 
                                  person, number, gender, "case", degree, verb_form, page_url)
                SELECT 
                    l.id,
                    norm(s.form_diac),
                    s.form_diac,
                    NULLIF(s.mood, ''),
                    NULLIF(s.tense, ''),
                    NULLIF(s.voice, ''),
                    NULLIF(s.person, ''),
                    NULLIF(s.number, ''),
                    NULLIF(s.gender, ''),
                    NULLIF(s."case", ''),
                    NULLIF(s.degree, ''),
                    NULLIF(s.verb_form, ''),
                    NULLIF(s.page_url, '')
                FROM forms_staging s
                JOIN lemmas l ON l.lemma_nod = norm(s.lemma_nod)
                ON CONFLICT DO NOTHING
            """)
            
            form_count = cur.rowcount
            print(f"Loaded {form_count} forms")
        
        conn.commit()
        
        print("Done!")


if __name__ == "__main__":
    main()
