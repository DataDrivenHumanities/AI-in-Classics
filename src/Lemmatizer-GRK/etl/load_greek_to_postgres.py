#!/usr/bin/env python3
import os
import csv
from pathlib import Path
import psycopg
import unicodedata

# Paths - Adjusted to look at the 'out' folder
BASE = Path(__file__).resolve().parents[1]
OUT_DIR = BASE / "out"
SCHEMA_FILE = BASE / "ops" / "init_db_greek.sql"

# Local DB Connection string
DSN = "postgresql://postgres:mysecretpassword@localhost:5432/greek_lemmatizer"

def strip_accents(text):
    """Removes Greek accents to create the 'nod' (no diacritics) search strings."""
    if not text: return ""
    normalized = unicodedata.normalize('NFD', text)
    return "".join(c for c in normalized if unicodedata.category(c) != 'Mn')

def main():
    print("🚀 Starting Greek PostgreSQL Loader...")

    if not OUT_DIR.exists():
        raise SystemExit(f"❌ Output directory not found: {OUT_DIR}")

    csv_files = list(OUT_DIR.glob("*.csv"))
    
    # Filter out the metadata file if it accidentally gets read
    csv_files = [f for f in csv_files if not f.name.startswith("_meta")]
    
    if not csv_files:
        raise SystemExit(f"❌ No CSV files found in {OUT_DIR}")

    with psycopg.connect(DSN, autocommit=True) as conn:
        
        # 1. Apply Schema
        print("📜 Applying SQL Schema...")
        conn.execute(SCHEMA_FILE.read_text(encoding="utf-8"))

        # 2. Extract Data from all CSVs
        print(f"📖 Reading data from {len(csv_files)} CSV files...")
        lemmas_dict = {}
        forms_list = []

        for file_path in csv_files:
            with open(file_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    # Deriving data from the scraper's specific column names
                    lemma_diac = row.get('lemma_text', '')
                    lemma_nod = strip_accents(lemma_diac)
                    page_url = row.get('page_url', '')
                    
                    # Extract the Perseus ID from the URL
                    atlas_id = page_url.strip("/").split("/")[-1] if page_url else ""

                    # Capture unique lemmas
                    if lemma_nod not in lemmas_dict:
                        lemmas_dict[lemma_nod] = {
                            'lemma_code': atlas_id,
                            'lemma_nod': lemma_nod,
                            'lemma_diac': lemma_diac,
                            'english_definition': '', # Scraper doesn't pull this yet
                            'pos': row.get('pos', ''),
                            'gender': row.get('gender', ''),
                            'page_url': page_url
                        }
                    
                    # Store the form mapping
                    row['lemma_nod_link'] = lemma_nod
                    forms_list.append(row)

        # 3. Load Lemmas
        print(f"📥 Loading {len(lemmas_dict)} unique lemmas into database...")
        lemma_cache = {} # To store the new DB IDs

        for nod, l in lemmas_dict.items():
            result = conn.execute("""
                INSERT INTO lemmas (lemma_code, lemma_nod, lemma_diac, english_definition, pos, gender, page_url)
                VALUES (%s, norm(%s), %s, %s, %s, %s, %s)
                ON CONFLICT (lemma_code) DO UPDATE SET
                    lemma_nod = EXCLUDED.lemma_nod,
                    lemma_diac = EXCLUDED.lemma_diac
                RETURNING id;
            """, (l['lemma_code'], l['lemma_nod'], l['lemma_diac'], l['english_definition'], l['pos'], l['gender'], l['page_url']))
            
            lemma_cache[nod] = result.fetchone()[0]

        # 4. Load Forms
        print(f"📥 Loading {len(forms_list)} inflected forms into database...")
        
        with conn.cursor() as cur:
            for r in forms_list:
                lemma_id = lemma_cache.get(r['lemma_nod_link'])
                if not lemma_id: continue

                form_diac = r.get('form', '')
                form_nod = strip_accents(form_diac)

                cur.execute("""
                    INSERT INTO forms (lemma_id, form_nod, form_diac, mood, tense, voice, person, number, gender, "case", page_url)
                    VALUES (%s, norm(%s), %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT DO NOTHING;
                """, (
                    lemma_id, form_nod, form_diac, r.get('mood', ''), 
                    r.get('tense', ''), r.get('voice', ''), r.get('person', ''), 
                    r.get('number', ''), r.get('gender', ''), r.get('case', ''), 
                    r.get('page_url', '')
                ))

        print("\n" + "="*50)
        print("✅ DATABASE LOAD COMPLETE!")
        print("="*50)

if __name__ == "__main__":
    main()