# Runs ops/init_db.sql, then loads lemmas/forms CSVs
import os, subprocess, sys
import psycopg

PROJECT_ROOT = os.environ["PROJECT_ROOT"]          # .../Lemmatizer-LTN
DSN          = os.environ["DATABASE_URL"]
LEMMA_CSV    = os.environ["LEMMA_CSV"]
FORM_CSV     = os.environ["FORM_CSV"]

sql_path = os.path.join(PROJECT_ROOT, "ops", "init_db.sql")
with open(sql_path, "r", encoding="utf-8") as f:
    init_sql = f.read()

with psycopg.connect(DSN) as conn:
    with conn.cursor() as cur:
        cur.execute(init_sql)
    conn.commit()
print("Schema initialized.")

subprocess.check_call([
    sys.executable, os.path.join(PROJECT_ROOT, "etl", "load_to_postgres.py"),
    "--db", DSN, "--lemmas", LEMMA_CSV, "--forms", FORM_CSV
])
