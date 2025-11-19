# Aggregate per-lemma CSVs in ../out/ → lemmas.csv & forms.csv
from pathlib import Path
import csv, re, unicodedata, glob
from urllib.parse import urlparse, parse_qs

BASE = Path(__file__).resolve().parents[1]  # .../Lemmatizer-LTN
OUT_DIR = BASE / "out"
LEMMA_CSV = OUT_DIR / "lemmas.csv"
FORM_CSV  = OUT_DIR / "forms.csv"

def strip_accents(s: str) -> str:
    if not s: return ""
    nf = unicodedata.normalize("NFD", s)
    return "".join(ch for ch in nf if not unicodedata.combining(ch))

def norm(s: str) -> str:
    s = strip_accents(s or "").lower()
    return re.sub(r"[^a-z0-9]+", "", s)

_DIATH_RE = re.compile(r"\s*[-–—]?\s*(active|passive)\s+diathesis\s*$", re.I)
def clean_lemma_text(t: str) -> str:
    return _DIATH_RE.sub("", (t or "").strip())

def lemma_code_from_url(u: str):
    try:
        q = parse_qs(urlparse(u or "").query)
        return (q.get("lemma") or [None])[0]
    except Exception:
        return None

# --- detectors: tolerant to abbreviations/variants (EN + some fallbacks) ---
CASE_PATTERNS = [
    (re.compile(r"\bnom(?:\.|in(?:ative)?)?\b", re.I), "nominative"),
    (re.compile(r"\bgen(?:\.|it(?:ive)?)?\b", re.I),   "genitive"),
    (re.compile(r"\bdat(?:\.|iv(?:e)?)?\b", re.I),     "dative"),
    (re.compile(r"\bacc(?:\.|us(?:ative)?)?\b", re.I), "accusative"),
    (re.compile(r"\babl(?:\.|at(?:ive)?)?\b", re.I),   "ablative"),
    (re.compile(r"\bvoc(?:\.|at(?:ive)?)?\b", re.I),   "vocative"),
    (re.compile(r"\bloc(?:\.|at(?:ive)?)?\b", re.I),   "locative"),
]
NUM_SG = re.compile(r"\b(sg|sing|singular|sing\.)\b", re.I)
NUM_PL = re.compile(r"\b(pl|plur|plural|pl\.)\b", re.I)

MOODS  = ["indicative","subjunctive","imperative","infinitive","participle","gerund","gerundive","supine"]
VOICES = ["active","passive"]
TENSES = ["present","imperfect","future","perfect","pluperfect","future perfect","futureperfect"]

def detect_case(text: str) -> str:
    t = text or ""
    for pat, name in CASE_PATTERNS:
        if pat.search(t):
            return name
    return ""

def detect_number(*xs) -> str:
    j = " ".join(filter(None, xs))
    if NUM_SG.search(j): return "singular"
    if NUM_PL.search(j): return "plural"
    return ""

def detect_mood(*xs) -> str:
    j = " ".join(filter(None, xs)).lower()
    for m in MOODS:
        if m in j: return m
    return ""

def detect_voice(*xs) -> str:
    j = " ".join(filter(None, xs)).lower()
    if "active diathesis" in j or "voice active" in j or " active " in f" {j} ":
        return "active"
    if "passive diathesis" in j or "voice passive" in j or " passive " in f" {j} ":
        return "passive"
    if "deponent" in j:
        return "passive"
    return ""

def detect_tense(*xs) -> str:
    j = " ".join(filter(None, xs)).lower()
    if "future perfect" in j or "futureperfect" in j: return "future perfect"
    for t in TENSES:
        if t in j: return t
    return ""

def person_num_from_label(lbl: str):
    l = (lbl or "").lower()
    person = ""
    if re.search(r"\b(1st|first|i)\b", l):   person = "first"
    elif re.search(r"\b(2nd|second|ii)\b", l): person = "second"
    elif re.search(r"\b(3rd|third|iii)\b", l): person = "third"
    number = ""
    if re.search(r"\b(sg|sing|singular|sing\.)\b", l): number = "singular"
    if re.search(r"\b(pl|plur|plural|pl\.)\b", l):     number = "plural"
    return person, number

def clean(s): return (s or "").strip()

def aggregate():
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # discover all per-lemma csvs (ignore previous aggregates)
    paths = [p for p in glob.glob(str(OUT_DIR / "*.csv"))
             if Path(p).name not in ("lemmas.csv","forms.csv")]

    lemmas = {}   # lemma_nod -> (lemma_code, lemma_nod, lemma_diac, pos, gender, page_url)
    forms  = []   # (lemma_nod, form_nod, form_diac, label, mood, tense, voice, person, number, gender, case, degree, page_url)

    for p in paths:
        with open(p, newline="", encoding="utf-8") as f:
            r = csv.DictReader(f); rows = list(r)
        if not rows: 
            continue

        r0 = rows[0]
        lemma_text = clean_lemma_text(clean(r0.get("lemma_text","")))
        pos_text   = clean(r0.get("pos",""))
        page_url   = clean(r0.get("page_url",""))
        lnod       = norm(lemma_text)
        lcode      = lemma_code_from_url(page_url)

        gender_from_pos = ""
        pl = pos_text.lower()
        if   "masculine" in pl: gender_from_pos = "masculine"
        elif "feminine"  in pl: gender_from_pos = "feminine"
        elif "neuter"    in pl: gender_from_pos = "neuter"

        # store lemma once
        lemmas.setdefault(lnod, (lcode, lnod, lemma_text, pos_text, gender_from_pos, page_url))
        is_verb = "verb" in pl

        for rr in rows:
            ctx1 = clean(rr.get("context_1",""))
            ctx2 = clean(rr.get("context_2",""))
            ctx3 = clean(rr.get("context_3",""))
            label= clean(rr.get("label",""))
            value= clean(rr.get("value",""))
            if not value:
                continue

            form_diac = value
            form_nod  = norm(form_diac)
            if not form_nod:
                continue

            # Hints from scraper (if present)
            number_hint = (rr.get("number_hint") or "").lower()
            gender_hint = (rr.get("gender_hint") or "").lower()
            voice_hint  = (rr.get("voice_hint")  or "").lower()

            # defaults
            mood=tense=voice=person=number=case=degree=""

            if is_verb:
                # voice: prefer explicit hint from diathesis, else detect from titles
                voice = voice_hint or detect_voice(ctx1,ctx2,ctx3,label)

                # mood/tense from titles
                mood  = detect_mood(ctx1,ctx2,ctx3,label)
                tense = detect_tense(ctx1,ctx2,ctx3,label)

                # person/number from label (e.g., "3rd sg.")
                p_lbl, n_lbl = person_num_from_label(label)
                person = p_lbl
                number = n_lbl or number_hint or detect_number(ctx1,ctx2,ctx3,label)

            else:
                # nouns/adjectives: case from label, number from hint or tokens
                case   = detect_case(label)
                number = number_hint or detect_number(label, ctx1, ctx2, ctx3)

            gender = gender_hint or gender_from_pos

            forms.append((lnod, form_nod, form_diac, label,
                          mood, tense, voice, person, number, gender, case, degree, page_url))

    # write aggregates
    with open(LEMMA_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["lemma_code","lemma_nod","lemma_diac","pos","gender","page_url"])
        for v in lemmas.values():
            w.writerow(v)

    with open(FORM_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["lemma_nod","form_nod","form_diac","label",
                    "mood","tense","voice","person","number","gender","case","degree","page_url"])
        w.writerows(forms)

    print(f"Wrote {len(lemmas)} lemmas -> {LEMMA_CSV}")
    print(f"Wrote {len(forms)} forms  -> {FORM_CSV}")

if __name__ == "__main__":
    aggregate()
