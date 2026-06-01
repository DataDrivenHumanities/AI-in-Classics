#!/usr/bin/env python3
"""Load aggregate CSVs (lemmas.csv, forms.csv) into PostgreSQL using batch inserts for speed."""
import os
import csv
import argparse
from pathlib import Path
import psycopg
from dotenv import load_dotenv

BASE = Path(__file__).resolve().parents[1]
OUT_DIR = BASE / "out"

# Load .env from current directory or parents
env_path = Path(".env")
if not env_path.exists():
    # Try looking up
    for parent in Path.cwd().parents:
        if (parent / ".env").exists():
            env_path = parent / ".env"
            break
load_dotenv(env_path)


def main(): 
    ap = argparse.ArgumentParser()
    ap.add_argument("--outdir", default=str(OUT_DIR))
    ap.add_argument("--schema", default=str(BASE / "ops" / "init_db.sql"))
    ap.add_argument("--truncate", action="store_true")
    ap.add_argument(
        "--recreate",
        action="store_true",
        help="Drop lemmas/forms tables and recreate from schema before loading",
    )
    args = ap.parse_args()

    dsn = os.getenv("DATABASE_URL")
    print(dsn)
    if not dsn:
        raise SystemExit("DATABASE_URL not set")

    outdir = Path(args.outdir)
    lemmas_csv = outdir / "lemmas.csv"
    forms_csv = outdir / "forms.csv"

    if not lemmas_csv.exists() or not forms_csv.exists():
        raise SystemExit(f"CSVs not found: {lemmas_csv}, {forms_csv}")

    with psycopg.connect(dsn) as conn:
        # Recreate tables from scratch (drop old schema completely)
        if args.recreate:
            print("Dropping existing tables (forms, lemmas)...")
            with conn.cursor() as cur:
                cur.execute("DROP TABLE IF EXISTS forms CASCADE")
                cur.execute("DROP TABLE IF EXISTS lemmas CASCADE")
            conn.commit()

        # Apply schema
        if args.schema and Path(args.schema).exists():
            with conn.cursor() as cur:
                cur.execute(Path(args.schema).read_text(encoding="utf-8"))
            conn.commit()

        # Truncate (only when not recreating)
        if args.truncate and not args.recreate:
            print("Truncating tables...")
            with conn.cursor() as cur:
                cur.execute("TRUNCATE TABLE forms RESTART IDENTITY CASCADE")
                cur.execute("TRUNCATE TABLE lemmas RESTART IDENTITY CASCADE")
            conn.commit()

        # Load lemmas using batch inserts
        print("Loading lemmas...")
        with conn.cursor() as cur:
            # Read CSV and prepare data
            rows = []
            with open(lemmas_csv, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                next(reader)  # Skip header
                for row in reader:
                    if len(row) < 6:
                        continue
                    # CSV: lemma_code, lemma_nod, lemma_diac, pos, gender, page_url, definition
                    # We skip lemma_nod (index 1), norm() will compute it
                    rows.append((
                        row[0] if row[0] else None,  # lemma_code
                        row[2] if row[2] else None,  # lemma_diac (for norm() and storage)
                        row[3] if row[3] else None,  # pos
                        row[4] if row[4] else None,  # gender
                        row[5] if row[5] else None,  # page_url
                        row[6] if len(row) > 6 and row[6] else None  # definition
                    ))
            
            # Batch insert in chunks of 1000 (much faster than individual INSERTs)
            batch_size = 1000
            total_inserted = 0
            for i in range(0, len(rows), batch_size):
                batch = rows[i:i + batch_size]
                # Build VALUES clause with %s placeholders
                values = []
                params = []
                for j, row in enumerate(batch):
                    placeholders = []
                    for k in range(6):
                        placeholders.append("%s")
                        params.append(row[k])
                    values.append(f"({', '.join(placeholders)})")
                
                query = f"""
                    INSERT INTO lemmas (lemma_code, lemma_nod, lemma_diac, pos, gender, page_url, definition)
                    SELECT 
                        v.lemma_code,
                        norm(v.lemma_diac) AS lemma_nod,
                        v.lemma_diac,
                        v.pos,
                        v.gender,
                        v.page_url,
                        v.definition
                    FROM (VALUES {', '.join(values)}) AS v(lemma_code, lemma_diac, pos, gender, page_url, definition)
                    ON CONFLICT (lemma_nod) DO UPDATE SET
                        lemma_code = EXCLUDED.lemma_code,
                        lemma_diac = EXCLUDED.lemma_diac,
                        pos = EXCLUDED.pos,
                        gender = EXCLUDED.gender,
                        page_url = EXCLUDED.page_url,
                        definition = EXCLUDED.definition
                """
                cur.execute(query, params)
                total_inserted += cur.rowcount
                
            print(f"Loaded {total_inserted} lemmas")
        
        conn.commit()

        # Build lemma cache
        print("Building lemma cache...")
        cache = {}
        with conn.cursor() as cur:
            cur.execute("SELECT id, lemma_nod FROM lemmas")
            for row in cur.fetchall():
                cache[str(row[1]).lower()] = row[0]
        
        print(f"Cached {len(cache)} lemma IDs")

        # Load forms using batch inserts
        print("Loading forms...")
        with conn.cursor() as cur:
            # Read CSV and prepare data with lemma_id lookup
            rows = []
            skipped = 0
            with open(forms_csv, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                next(reader)  # Skip header
                for row in reader:
                    if len(row) < 14:
                        continue
                    # CSV: lemma_nod, form_nod, form_diac, label, mood, tense, voice, person, number, gender, case, degree, verb_form, page_url
                    # We skip form_nod (index 1), norm() will compute it
                    lemma_nod = row[0] if row[0] else None
                    lemma_id = cache.get(lemma_nod.lower() if lemma_nod else "") if lemma_nod else None
                    if not lemma_id:
                        skipped += 1
                        continue
                    
                    rows.append((
                        lemma_id,
                        row[2] if row[2] else None,  # form_diac (for norm() and storage)
                        row[4] if row[4] else None,  # mood
                        row[5] if row[5] else None,  # tense
                        row[6] if row[6] else None,  # voice
                        row[7] if row[7] else None,  # person
                        row[8] if row[8] else None,  # number
                        row[9] if row[9] else None,  # gender
                        row[10] if row[10] else None,  # case
                        row[11] if row[11] else None,  # degree
                        row[12] if row[12] else None,  # verb_form
                        row[13] if row[13] else None   # page_url
                    ))
            
            if skipped > 0:
                print(f"Skipped {skipped} forms (no matching lemma)")
            
            # Batch insert in chunks of 1000
            batch_size = 1000
            total_inserted = 0
            for i in range(0, len(rows), batch_size):
                batch = rows[i:i + batch_size]
                # Build VALUES clause with %s placeholders
                values = []
                params = []
                for j, row in enumerate(batch):
                    placeholders = []
                    for k in range(12):
                        placeholders.append("%s")
                        params.append(row[k])
                    values.append(f"({', '.join(placeholders)})")
                
                query = f"""
                    INSERT INTO forms (lemma_id, form_nod, form_diac, mood, tense, voice, 
                                      person, number, gender, "case", degree, verb_form, page_url)
                    SELECT 
                        v.lemma_id,
                        norm(v.form_diac) AS form_nod,
                        v.form_diac,
                        v.mood,
                        v.tense,
                        v.voice,
                        v.person,
                        v.number,
                        v.gender,
                        v."case",
                        v.degree,
                        v.verb_form,
                        v.page_url
                    FROM (VALUES {', '.join(values)}) AS v(lemma_id, form_diac, mood, tense, voice, 
                                                           person, number, gender, "case", degree, verb_form, page_url)
                    ON CONFLICT DO NOTHING
                """
                cur.execute(query, params)
                total_inserted += cur.rowcount
                
            print(f"Loaded {total_inserted} forms")
        
        conn.commit()
        
        print("Done!")


if __name__ == "__main__":
    main()
