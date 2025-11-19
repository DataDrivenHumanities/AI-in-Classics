#!/usr/bin/env python3
import os
import csv
import re
import argparse
from pathlib import Path
from urllib.parse import urlparse, parse_qs

import psycopg

# --- import normalization helpers -------------------------------------------

try:
    # When run as a module inside etl/
    from latin_norm import clean_lemma_text, normalize_morph
except Exception:
    # When run from elsewhere: add this directory to sys.path
    import importlib, sys
    sys.path.append(str(Path(__file__).parent))
    _ln = importlib.import_module("latin_norm")
    clean_lemma_text = _ln.clean_lemma_text
    normalize_morph = _ln.normalize_morph

# --- constants --------------------------------------------------------------

BASE = Path(__file__).resolve().parents[1]
OUT_DIR = BASE / "out"

# A small set of common Latin endings so we can rebuild forms from
# patterns like "abalienaturos, -as, -auros, -as, -a esse".
LATIN_ENDINGS = [
    "ibus", "arum", "orum", "ium",
    "ius",
    "ntur", "mini", "mur",
    "ris", "sti", "mus", "tis", "nt",
    "ans", "ens",
    "tur", "bor", "beris", "bitur",
    "ius",
    "ius",
    "ior", "ius",
    "ius",
    "us", "um", "os", "is", "ae", "am", "as", "es", "im", "em",
    "is", "e", "o", "u", "i",
]

# sort longest->shortest for suffix matching
LATIN_ENDINGS = sorted(set(LATIN_ENDINGS), key=len, reverse=True)


# --- helpers ----------------------------------------------------------------

def lemma_code_from_url(u: str) -> str:
    try:
        q = parse_qs(urlparse(u or "").query)
        return (q.get("lemma") or [""])[0]
    except Exception:
        return ""


def dedupe_tail(form: str) -> str:
    """
    Fix cases like:
      - abalienoror     -> abalienor
      - abalienareare   -> abalienare
      - abalienandiandi -> abalienandi
      - abalienandoando -> abalienando
      - abalienandumandum -> abalienandum
    by collapsing a repeated short tail.
    """
    s = (form or "").strip()
    # Only operate on single "word-ish" tokens, no spaces or commas
    if not s or " " in s or "," in s:
        return s

    # match: base + short_tail + same short_tail again
    m = re.match(r"^(.+?)([^\W\d_]{1,4})\2$", s, flags=re.UNICODE)
    if m:
        return m.group(1) + m.group(2)
    return s


def expand_value_to_forms(value: str) -> list[str]:
    """
    Take the raw 'value' from the CSV and expand it into one or more
    actual surface forms.

    Examples we want to handle:

      "abalienoror"                     -> ["abalienor"]
      "abalienarisaris, abalienareare" -> ["abalienaris", "abalienare"]
      "abalienaturos, -as, -auros, -as, -a esse"
        -> ["abalienaturos esse",
            "abalienaturas esse",
            "abalienaturauros esse",
            "abalienaturauras esse",
            "abalienatura esse"]

      "abalienaturum, -am, -um esse"
        -> ["abalienaturum esse", "abalienaturam esse"]

    For now we:
      * Keep 'esse' (and anything after it) as a tail attached to each form.
      * Use hyphen shorthand only when we see pieces starting with '-'.
    """
    raw = (value or "").strip()
    if not raw:
        return []

    # 0) Is this just a single weird token? -> dedupe_tail and return
    if "," not in raw and " " not in raw:
        return [dedupe_tail(raw)]

    # 1) Separate a tail like " esse" (periphrastic)
    tail = ""
    head = raw
    m_tail = re.search(r"\s+esse\b.*$", head)
    if m_tail:
        tail = m_tail.group(0)
        head = head[:m_tail.start()].rstrip()

    parts = [p.strip() for p in head.split(",") if p.strip()]
    if not parts:
        return [raw]

    # First part is our base. Always clean its tail-duplication.
    base = dedupe_tail(parts[0])
    rest = parts[1:]

    # Do we have hyphen shorthand?
    has_hyphen = any(p.startswith("-") for p in rest)

    forms: list[str] = []

    if has_hyphen:
        # Try to split base into stem + ending using common Latin endings.
        stem = base
        base_suffix = ""
        lower = base.lower()
        for cand in LATIN_ENDINGS:
            if lower.endswith(cand):
                base_suffix = base[-len(cand):]
                stem = base[:-len(cand)]
                break

        if not base_suffix:
            # Fallback: give up and just treat everything as independent tokens
            forms = [dedupe_tail(p) for p in parts]
        else:
            # Include the base itself
            forms.append(base)
            for raw_suf in rest:
                if not raw_suf.startswith("-"):
                    continue
                suf = raw_suf.lstrip("-").strip()
                if not suf:
                    continue
                new_form = stem + suf
                forms.append(dedupe_tail(new_form))
    else:
        # No hyphen shorthand: split into separate tokens
        forms = [dedupe_tail(p) for p in parts]

    # Attach tail (e.g. " esse") if present
    if tail:
        forms = [f"{f}{tail}" for f in forms]

    # De-duplicate while preserving order
    uniq: list[str] = []
    seen = set()
    for f in forms:
        if f not in seen:
            uniq.append(f)
            seen.add(f)

    return uniq or [raw]


def upsert_lemma(conn, *, lemma_text: str, pos: str, gender_hint: str, page_url: str) -> int:
    """
    Insert or update a lemma row, returning lemma.id.
    We store:
      - lemma_code: short code from URL (?lemma=...)
      - lemma_nod:  normalized (lower + unaccent) version of cleaned lemma
      - lemma_diac: cleaned display lemma with diacritics
      - pos, gender, page_url
    """
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
        (
            lemma_code or None,
            lemma_diac,
            lemma_diac or None,
            pos or None,
            gender_hint or None,
            page_url or None,
        ),
    ).fetchone()
    return row[0]


def insert_form(conn, lemma_id: int, r: dict, lemma_voice_hint: str, lemma_gender_hint: str):
    """
    Insert one or more forms for a given lemma_id.

    We:
      * Normalize morph tags via normalize_morph(row).
      * Expand 'value' into one or more surface forms.
      * Apply lemma-level voice/gender as fallback if row-level parsing
        didn't find them.
    """
    n = normalize_morph(r)

    mood = n.get("mood") or None
    tense = n.get("tense") or None
    voice = (n.get("voice") or lemma_voice_hint) or None
    person = n.get("person") or None
    number = n.get("number") or None
    gender = (n.get("gender") or lemma_gender_hint) or None
    case = n.get("case") or None
    degree = n.get("degree") or None

    raw_val = (r.get("value") or "").strip()
    if not raw_val:
        return

    forms = expand_value_to_forms(raw_val)

    page_url = (r.get("page_url") or None)

    for form_diac in forms:
        form_diac = form_diac.strip()
        if not form_diac:
            continue
        # form_nod is accent-stripped lower, implemented in SQL as norm()
        conn.execute(
            """
            INSERT INTO forms
              (lemma_id, form_nod, form_diac,
               mood, tense, voice, person, number, gender, "case", degree, page_url)
            VALUES
              (%s,      norm(%s), %s,
               %s,  %s,   %s,    %s,     %s,     %s,     %s,    %s,    %s)
            ON CONFLICT DO NOTHING
            """,
            (
                lemma_id,
                form_diac,
                form_diac,
                mood, tense, voice, person, number, gender, case, degree,
                page_url,
            ),
        )


# --- main -------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--outdir",
        default=str(OUT_DIR),
        help="Directory of per-lemma CSVs (scrape_tables.py output)",
    )
    ap.add_argument(
        "--schema",
        default=str(BASE / "ops" / "init_db.sql"),
        help="Apply schema before loading (if present)",
    )
    ap.add_argument(
        "--truncate",
        action="store_true",
        help="TRUNCATE forms/lemmas before load",
    )
    args = ap.parse_args()

    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        raise SystemExit("Set DATABASE_URL to your Neon Postgres URI (DATABASE_URL)")

    outdir = Path(args.outdir)
    if not outdir.exists():
        raise SystemExit(f"Out dir not found: {outdir}")

    with psycopg.connect(dsn, autocommit=True) as conn:
        conn.execute("SET application_name = 'latin-etl';")

        # Apply schema if provided
        if args.schema and Path(args.schema).exists():
            sql = Path(args.schema).read_text(encoding="utf-8")
            conn.execute(sql)

        # Optional truncate: start fresh
        if args.truncate:
            conn.execute("TRUNCATE TABLE forms RESTART IDENTITY CASCADE;")
            conn.execute("TRUNCATE TABLE lemmas RESTART IDENTITY CASCADE;")

        # Load all per-lemma CSVs (skip aggregate lemmas/forms CSVs if present)
        csv_files = [
            p for p in outdir.glob("*.csv")
            if p.name not in ("lemmas.csv", "forms.csv")
        ]

        for p in sorted(csv_files):
            with p.open(newline="", encoding="utf-8") as f:
                rows = list(csv.DictReader(f))

            if not rows:
                continue

            head = rows[0]
            head_norm = normalize_morph(head)

            lemma_id = upsert_lemma(
                conn,
                lemma_text=head.get("lemma_text", ""),
                pos=head.get("pos", ""),
                gender_hint=head_norm.get("gender", ""),
                page_url=head.get("page_url", ""),
            )

            lemma_voice_hint = head_norm.get("voice", "") or ""
            lemma_gender_hint = head_norm.get("gender", "") or ""

            for r in rows:
                insert_form(conn, lemma_id, r, lemma_voice_hint, lemma_gender_hint)

            print(f"[loaded] {p.name}: {len(rows)} raw rows")

    print("Load complete.")


if __name__ == "__main__":
    main()
