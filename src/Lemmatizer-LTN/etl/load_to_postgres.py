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
# patterns like stems + endings (e.g. "abalienatur" + "os", "as", "a").
LATIN_ENDINGS = [
    "ibus", "arum", "orum", "ium",
    "ntur", "mini", "mur",
    "beris", "bitur", "bor",
    "ior", "ius",
    "ans", "ens",
    "ius",
    "orum", "arum", "ium",
    "nt",
    "us", "um", "os", "is", "ae", "am", "as", "es", "im", "em",
    "is", "e", "o", "u", "i",
]
LATIN_ENDINGS = sorted(set(LATIN_ENDINGS), key=len, reverse=True)

# --- helpers ----------------------------------------------------------------


def lemma_code_from_url(u: str) -> str:
    """Extract lemma=XYZ from the page_url querystring."""
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
    if not s or " " in s or "," in s:
        return s

    m = re.match(r"^(.+?)([^\W\d_]{1,4})\2$", s, flags=re.UNICODE)
    if m:
        return m.group(1) + m.group(2)
    return s


def split_tail_esse(s: str) -> tuple[str, str]:
    """
    Split trailing ' esse...' tail from a periphrastic form, if present.
    e.g. 'abalienaturos esse' -> ('abalienaturos', ' esse')
    """
    s = (s or "").strip()
    m = re.search(r"\s+esse\b.*$", s)
    if m:
        return s[:m.start()].rstrip(), s[m.start():]
    return s, ""


def stem_from_base(base_head: str) -> tuple[str, str]:
    """
    Given a base head like 'abalienaturos', try to split into (stem, ending),
    using common Latin endings. If we can't, return (base_head, '').
    """
    head = base_head or ""
    lower = head.lower()
    for cand in LATIN_ENDINGS:
        if lower.endswith(cand):
            return head[:-len(cand)], head[-len(cand):]
    return head, ""


def expand_suffix_row(raw: str, base_full: str) -> list[str]:
    """
    Expand a row whose value starts with '-' using the last base form.

    Example:
      base_full   = 'abalienaturos esse'
      raw         = '-as esse'
      -> ['abalienaturas esse']
    """
    if not base_full:
        return []

    s = (raw or "").strip()
    if not s.startswith("-"):
        return []

    # Split suffix-row into head (like '-as') and tail (' esse')
    head2, tail2 = split_tail_esse(s)
    suf = head2.lstrip("-").strip()
    if not suf:
        return []

    # Base: e.g. 'abalienaturos esse'
    base_head, base_tail = split_tail_esse(base_full)
    # If suffix row has a tail, that should match the base or override it.
    tail = tail2 or base_tail

    stem, _ending = stem_from_base(base_head)
    if not stem:
        # Fallback if we can't derive stem: just glom
        new_form = base_head + suf + (tail or "")
        return [dedupe_tail(new_form)]

    new_head = stem + suf
    new_form = dedupe_tail(new_head) + (tail or "")
    return [new_form]


def expand_value_to_forms(raw: str, base_hint: str | None) -> tuple[list[str], str | None]:
    """
    Expand a CSV 'value' into one or more surface forms, with optional
    base_hint from the previous row (for rows that start with '-').

    Returns (forms_list, new_base_hint).

    Cases:
      1) raw starts with '-' and we have base_hint:
           -> use expand_suffix_row(raw, base_hint)
           -> keep base_hint unchanged

      2) raw has commas and inline hyphen shorthand:
           e.g. "abalienaturos, -as, -auros, -as, -a esse"
           -> multiple forms from a single row, new base_hint = base form

      3) raw is a simple one-form row (no comma, doesn't start with '-'):
           -> one form, and becomes the new base_hint for subsequent '-' rows.
    """
    raw = (raw or "").strip()
    if not raw:
        return [], base_hint

    # Case 1: suffix-only row, use previous base if we have it
    if raw.startswith("-"):
        if base_hint:
            forms = expand_suffix_row(raw, base_hint)
            return forms, base_hint
        # No base: treat as standalone (strip leading '-')
        stripped = raw.lstrip("-").strip()
        if not stripped:
            return [], base_hint
        return [dedupe_tail(stripped)], base_hint

    # Case 3: simple one-form row, no comma => becomes new base
    if "," not in raw:
        return [dedupe_tail(raw)], raw

    # Case 2: inline pattern with commas and maybe hyphens:
    # e.g. "abalienaturos, -as, -auros, -as, -a esse"
    head, tail = split_tail_esse(raw)
    parts = [p.strip() for p in head.split(",") if p.strip()]
    if not parts:
        return [dedupe_tail(raw)], raw

    base = dedupe_tail(parts[0])
    stem, _ending = stem_from_base(base)

    forms: list[str] = []
    # Always include the base itself
    forms.append(base + (tail or ""))

    for part in parts[1:]:
        if part.startswith("-"):
            suf = part.lstrip("-").strip()
            if not suf:
                continue
            if stem:
                fhead = stem + suf
            else:
                fhead = base + suf
            forms.append(dedupe_tail(fhead) + (tail or ""))
        else:
            forms.append(dedupe_tail(part) + (tail or ""))

    new_base_hint = base + (tail or "")
    # De-dup for safety
    seen = set()
    uniq: list[str] = []
    for f in forms:
        if f not in seen:
            uniq.append(f)
            seen.add(f)

    return uniq, new_base_hint


def detect_lemma_voice_from_heading(row: dict) -> str:
    """
    Fallback: infer voice (active/passive/deponent/middle) from lemma heading
    and nearby text. Handles 'Active diathesis' / 'Passive diathesis' from
    the lemma heading if voice_hint is missing.
    """
    lemma_text = (row.get("lemma_text") or "")
    pos = (row.get("pos") or "")
    c1 = (row.get("context_1") or "")
    c2 = (row.get("context_2") or "")
    c3 = (row.get("context_3") or "")
    label = (row.get("label") or "")

    combined = " ".join(x for x in [lemma_text, pos, c1, c2, c3, label] if x)
    up = combined.upper()

    if "ACTIVE DIATHESIS" in up:
        return "active"
    if "PASSIVE DIATHESIS" in up:
        return "passive"
    if "DEPONENT" in up:
        return "deponent"
    if "MIDDLE DIATHESIS" in up or "MIDDLE VOICE" in up:
        return "middle"
    return ""


# --- DB helpers -------------------------------------------------------------


def upsert_lemma(
    conn,
    *,
    lemma_text: str,
    pos: str,
    gender_hint: str,
    page_url: str,
) -> int:
    """
    Insert or update a lemma row, returning lemmas.id.
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
            (gender_hint or None),
            page_url or None,
        ),
    ).fetchone()
    return row[0]


def insert_form(
    conn,
    lemma_id: int,
    r: dict,
    lemma_voice_hint: str | None,
    lemma_gender_hint: str | None,
    base_hint: str | None,
) -> str | None:
    """
    Insert one or more forms for a given lemma_id.

    Returns updated base_hint for this lemma so we can expand later '-' rows.
    """
    n = normalize_morph(r)

    mood = n.get("mood") or None
    tense = n.get("tense") or None

    # Voice: ALL forms of a lemma inherit lemma_voice_hint
    # (normalize_morph's voice is noisy for rows; we trust lemma-level voice)
    voice = lemma_voice_hint or None

    person = n.get("person") or None
    number = n.get("number") or None
    gender = n.get("gender") or lemma_gender_hint or None
    case = n.get("case") or None
    degree = n.get("degree") or None

    raw_val = (r.get("value") or "").strip()
    if not raw_val:
        return base_hint

    forms, new_base_hint = expand_value_to_forms(raw_val, base_hint)

    page_url = (r.get("page_url") or None)
    updated_base_hint = new_base_hint

    for form_diac in forms:
        form_diac = form_diac.strip()
        if not form_diac:
            continue
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
                mood,
                tense,
                voice,
                person,
                number,
                gender,
                case,
                degree,
                page_url,
            ),
        )

    return updated_base_hint


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
            p
            for p in outdir.glob("*.csv")
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

            # ---- VOICE + GENDER HINTS --------------------------------------
            # Gender: from normalized morph if present
            lemma_gender_hint = (head_norm.get("gender") or "").strip().lower() or None

            # Voice: FIRST from CSV voice_hint, since the scraper can set it
            lemma_voice_hint = (head.get("voice_hint") or "").strip().lower()

            # If CSV doesn't have it, fall back to normalized morph:
            if not lemma_voice_hint:
                lemma_voice_hint = (head_norm.get("voice") or "").strip().lower()

            # If still missing, fall back to heading text (Active/Passive diathesis)
            if not lemma_voice_hint:
                lemma_voice_hint = detect_lemma_voice_from_heading(head) or ""

            lemma_voice_hint = lemma_voice_hint or None
            # -----------------------------------------------------------------

            base_hint: str | None = None
            for r in rows:
                base_hint = insert_form(
                    conn,
                    lemma_id,
                    r,
                    lemma_voice_hint,
                    lemma_gender_hint,
                    base_hint,
                )

            print(f"[loaded] {p.name}: {len(rows)} raw rows")

    print("Load complete.")


if __name__ == "__main__":
    main()
