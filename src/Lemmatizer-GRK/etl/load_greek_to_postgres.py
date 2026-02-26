#!/usr/bin/env python3
import os
import csv
from pathlib import Path
import psycopg

# Paths
BASE = Path(__file__).resolve().parents[1]
CSV_FILE = BASE / "database" / "GREEK_FULL_DATASET_REPLICABLE.csv"
SCHEMA_FILE = BASE / "ops" / "init_db_greek.sql"

# Local DB Connection string matching your docker-compose.yml
DSN = "postgresql://postgres:mysecretpassword@localhost:5432/greek_lemmatizer"

def main():
    print("🚀 Starting Greek PostgreSQL Loader...")

    if not CSV_FILE.exists():
        raise SystemExit(f"❌ CSV not found: {CSV_FILE}")

    with psycopg.connect(DSN, autocommit=True) as conn:
        
        # 1. Apply Schema
        print("📜 Applying SQL Schema...")
        conn.execute(SCHEMA_FILE.read_text(encoding="utf-8"))

        # 2. Extract Data from CSV
        print("📖 Reading CSV data...")
        lemmas_dict = {}
        forms_list = []

        with open(CSV_FILE, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Capture unique lemmas
                lemma_nod = row['lemma_nod']
                if lemma_nod not in lemmas_dict:
                    lemmas_dict[lemma_nod] = {
                        'lemma_code': row['atlas_id'],
                        'lemma_nod': lemma_nod,
                        'lemma_diac': row.get('lemma_diac', ''),
                        'english_definition': row.get('english_definition', ''),
                        'pos': row.get('label', ''),
                        'gender': row.get('gender', ''),
                        'page_url': row['page_url']
                    }
                
                # Capture form (store lemma_nod to link it later)
                forms_list.append(row)

        # 3. Load Lemmas
        print(f"📥 Loading {len(lemmas_dict)} unique lemmas...")
        lemma_cache = {} # To store the new DB IDs

        for nod, l in lemmas_dict.items():
            result = conn.execute("""
                INSERT INTO lemmas (lemma_code, lemma_nod, lemma_diac, english_definition, pos, gender, page_url)
                VALUES (%s, norm(%s), %s, %s, %s, %s, %s)
                ON CONFLICT (lemma_nod) DO UPDATE SET
                    lemma_code = EXCLUDED.lemma_code,
                    lemma_diac = EXCLUDED.lemma_diac,
                    english_definition = EXCLUDED.english_definition
                RETURNING id;
            """, (l['lemma_code'], l['lemma_nod'], l['lemma_diac'], l['english_definition'], l['pos'], l['gender'], l['page_url']))
            
            # Save the ID Postgres generated for this lemma
            lemma_cache[nod] = result.fetchone()[0]

        # 4. Load Forms in Batches
        print(f"📥 Loading {len(forms_list)} forms...")
        
        with conn.cursor() as cur:
            for r in forms_list:
                lemma_id = lemma_cache.get(r['lemma_nod'])
                if not lemma_id: continue

                cur.execute("""
                    INSERT INTO forms (lemma_id, form_nod, form_diac, mood, tense, voice, person, number, gender, "case", degree, verb_form, page_url)
                    VALUES (%s, norm(%s), %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT DO NOTHING;
                """, (
                    lemma_id, r['form_nod'], r.get('form_diac', ''), r.get('mood', ''), 
                    r.get('tense', ''), r.get('voice', ''), r.get('person', ''), 
                    r.get('number', ''), r.get('gender', ''), r.get('case', ''), 
                    r.get('degree', ''), r.get('verb_form', ''), r['page_url']
                ))

        print("\n" + "="*50)
        print("✅ DATABASE LOAD COMPLETE!")
        print("="*50)

if __name__ == "__main__":
    main()