#!/usr/bin/env python3
import os, csv, argparse
from pathlib import Path
from urllib.parse import urlparse, parse_qs
import psycopg

# robust import for sibling module
try:
    from latin_norm import clean_lemma_text, normalize_morph
except Exception:
    import importlib, sys
    sys.path.append(str(Path(__file__).parent))
    _ln = importlib.import_module("latin_norm")
    clean_lemma_text = _ln.clean_lemma_text
    normalize_morph  = _ln.normalize_morph

BASE = Path(__file__).resolve().parents[1]
OUT_DIR = BASE / "out"

def lemma_code_from_url(u: str) -> str:
    try:
        q = parse_qs(urlparse(u or "").query)
        return (q.get("lemma") or [""])[0]
    except Exception:
        return ""

def upsert_lemma(conn, *, lemma_text: str, pos: str, gender_hint: str, page_url: str) -> int:
    lemma_diac = clean_lemma_text(lemma_text or "")
    lemma_code = lemma_code_from_url(page_url)
    row = conn.execute(
        """
        INSERT INTO lemmas (lemma_code, lemma_nod, lemma_diac, pos, gender, page_url)
        VALUES (%s, norm(%s), %s, %s, %s, %s)
        ON CONFLICT (lemma_nod) DO UPDATE SET
          lemma_code = EXCLUDED.lemma_code,
          lemma_diac = EXCLUDED.lemma_diac,
          pos        = EXCLUDED.pos,
          gender     = EXCLUDED.gender,
          page_url   = EXCLUDED.page_url
        RETURNING id
        """,
        (lemma_code or None, lemma_diac, lemma_diac, pos or None, gender_hint or None, page_url or None),
    ).fetchone()
    return row[0]

def insert_form(conn, lemma_id: int, r: dict):
    n = normalize_morph(r)
    form_diac = (r.get("value") or "").strip()
    if not form_diac:
        return
    conn.execute(
        """
        INSERT INTO forms
          (lemma_id, form_nod, form_diac
           mood, tense, voice, person, number, gender, "case", degree, page_url)
        VALUES
          (%s,      norm(%s), %s,
           %s,  %s,   %s,    %s,     %s,     %s,     %s,    %s,    %s)
        ON CONFLICT DO NOTHING
        """,
        (
            lemma_id,
            form_diac, form_diac,
            (n["mood"] or None), (n["tense"] or None), (n["voice"] or None),
            (n["person"] or None), (n["number"] or None), (n["gender"] or None),
            (n["case"] or None), (n["degree"] or None),
            (r.get("page_url") or None),
        ),
    )

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--outdir",  default=str(OUT_DIR),                      help="Directory of per-lemma CSVs")
    ap.add_argument("--schema",  default=str(BASE / "ops" / "init_db.sql"), help="Apply schema before loading (if present)")
    ap.add_argument("--truncate", action="store_true",                      help="TRUNCATE forms/lemmas before load")
    args = ap.parse_args()

    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        raise SystemExit("Set DATABASE_URL to your Neon Postgres URI")

    outdir = Path(args.outdir)
    if not outdir.exists():
        raise SystemExit(f"Out dir not found: {outdir}")

    with psycopg.connect(dsn, autocommit=True) as conn:
        conn.execute("SET application_name = 'latin-etl';")

        if args.schema and Path(args.schema).exists():
            conn.execute(Path(args.schema).read_text(encoding="utf-8"))

        if args.truncate:
            conn.execute("TRUNCATE TABLE forms RESTART IDENTITY CASCADE;")
            conn.execute("TRUNCATE TABLE lemmas RESTART IDENTITY CASCADE;")

        files = [p for p in outdir.glob("*.csv") if p.name not in ("lemmas.csv","forms.csv")]
        for p in sorted(files):
            with p.open(newline="", encoding="utf-8") as f:
                rows = list(csv.DictReader(f))
            if not rows:
                continue

            head = rows[0]
            head_norm = normalize_morph(head)
            lemma_id = upsert_lemma(
                conn,
                lemma_text = head.get("lemma_text",""),
                pos        = head.get("pos",""),
                gender_hint= head_norm.get("gender",""),
                page_url   = head.get("page_url",""),
            )
            for r in rows:
                insert_form(conn, lemma_id, r)

            print(f"[loaded] {p.name}: {len(rows)} rows")

    print("Load complete.")

if __name__ == "__main__":
    main()
