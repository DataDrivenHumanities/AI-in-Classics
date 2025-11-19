#!/usr/bin/env python3
import os, csv, argparse
from pathlib import Path
from urllib.parse import urlparse, parse_qs
import psycopg
from etl.latin_norm import clean_lemma_text, normalize_morph

BASE = Path(__file__).resolve().parents[1]
OUT_DIR = BASE / "out"

def lemma_code_from_url(u: str) -> str:
    try:
        q = parse_qs(urlparse(u or "").query)
        return (q.get("lemma") or [""])[0]
    except Exception:
        return ""

def upsert_lemma(conn, lemma_text: str, pos: str, page_url: str) -> int:
    lemma_text = clean_lemma_text(lemma_text)
    lemma_code = lemma_code_from_url(page_url)
    row = conn.execute(
        """
        insert into lemmas (lemma_code, lemma_text, pos, page_url)
        values ($1, $2, $3, $4)
        on conflict (lemma_nod) do update
          set lemma_text = excluded.lemma_text,
              pos        = excluded.pos,
              page_url   = excluded.page_url
        returning id
        """,
        (lemma_code or None, lemma_text, pos or None, page_url or None),
    ).fetchone()
    return row[0]

def insert_form(conn, lemma_id: int, r: dict):
    n = normalize_morph(r)
    conn.execute(
        """
        insert into forms
          (lemma_id, form_diac, label,
           mood, tense, voice, person, number, gender, "case", degree,
           source_context_1, source_context_2, source_context_3, page_url)
        values
          ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15)
        on conflict do nothing
        """,
        (
            lemma_id,
            r.get("value") or "",
            r.get("label") or "",
            n["mood"] or None, n["tense"] or None, n["voice"] or None,
            n["person"] or None, n["number"] or None, n["gender"] or None,
            n["case"] or None, n["degree"] or None,
            r.get("context_1") or None, r.get("context_2") or None, r.get("context_3") or None,
            r.get("page_url") or None,
        ),
    )

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--outdir", default=str(OUT_DIR), help="Directory of per-lemma CSVs")
    ap.add_argument("--schema", default=str(BASE / "ops" / "schema.sql"), help="Apply schema before loading")
    ap.add_argument("--truncate", action="store_true", help="Truncate lemmas/forms before load")
    args = ap.parse_args()

    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        raise SystemExit("Set DATABASE_URL to your Neon Postgres URI")

    outdir = Path(args.outdir)
    if not outdir.exists():
        raise SystemExit(f"Out dir not found: {outdir}")

    with psycopg.connect(dsn, autocommit=True) as conn:
        conn.execute("set application_name = 'latin-etl';")
        if args.schema and Path(args.schema).exists():
            conn.execute(Path(args.schema).read_text(encoding="utf-8"))
        if args.truncate:
            conn.execute("truncate table forms restart identity cascade;")
            conn.execute("truncate table lemmas restart identity cascade;")

        files = [p for p in outdir.glob("*.csv") if p.name not in ("lemmas.csv","forms.csv")]
        for p in sorted(files):
            with p.open(newline="", encoding="utf-8") as f:
                rows = list(csv.DictReader(f))
            if not rows:
                continue
            head = rows[0]
            lemma_id = upsert_lemma(conn, head.get("lemma_text",""), head.get("pos",""), head.get("page_url",""))
            for r in rows:
                if r.get("value"):
                    insert_form(conn, lemma_id, r)
            print(f"[loaded] {p.name}: {len(rows)} rows")

    print("Load complete.")

if __name__ == "__main__":
    main()
