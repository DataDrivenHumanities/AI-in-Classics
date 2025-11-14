# aggregate_out_to_csvs.py
import csv, os, re, unicodedata, glob
from urllib.parse import urlparse, parse_qs

ROOT = os.getenv("BUILD_SOURCESDIRECTORY") or os.getcwd()
OUT_DIR   = os.path.join(ROOT, r"src\Lemmatizer-LTN\out")
LEMMA_CSV = os.path.join(OUT_DIR, "lemmas.csv")
FORM_CSV  = os.path.join(OUT_DIR, "forms.csv")

# ---------- utils ----------
def strip_accents(s):
    if not s: return ""
    nf = unicodedata.normalize("NFD", s)
    return "".join(ch for ch in nf if not unicodedata.combining(ch))

def norm(s):
    s = strip_accents(s or "").lower()
    s = re.sub(r"[^a-z0-9]+", "", s)
    return s

def lemma_code_from_url(u):
    try:
        q = parse_qs(urlparse(u or "").query)
        return (q.get("lemma") or [None])[0]
    except Exception:
        return None

# ---------- morphology maps ----------
CASE_MAP = {
    "nom.": "nominative", "gen.":"genitive", "dat.":"dative",
    "acc.":"accusative", "abl.":"ablative", "voc.":"vocative",
    "loc.":"locative", "ins.":"instrumental"
}
NUM_TOKS_SG = {"singular", "sing.", "sg", "sg."}
NUM_TOKS_PL = {"plural", "plur.", "pl", "pl."}

MOODS = {"indicative","subjunctive","imperative","infinitive","participle","gerund","gerundive","supine"}
VOICES = {"active","passive"}
TENSES = {
    "present","imperfect","future","perfect","pluperfect","future perfect","futureperfect"
}
PERSON_MAP = {"1st":"first","2nd":"second","3rd":"third"}

def clean_text(s):
    return (s or "").strip()

def detect_number(*contexts_and_label):
    joined = " ".join(filter(None, contexts_and_label)).lower()
    # prefer explicit tokens
    for tok in NUM_TOKS_SG:
        if tok in joined: return "singular"
    for tok in NUM_TOKS_PL:
        if tok in joined: return "plural"
    # sometimes labels use 'sg.'/'pl.'
    if re.search(r"\bsg\b\.?", joined): return "singular"
    if re.search(r"\bpl\b\.?", joined): return "plural"
    return ""

def detect_mood(*ctxs):
    joined = " ".join(filter(None, ctxs)).lower()
    for m in MOODS:
        if m in joined: return m
    return ""

def detect_voice(*ctxs):
    joined = " ".join(filter(None, ctxs)).lower()
    for v in VOICES:
        if v in joined: return v
    # deponent layouts often only show Passive forms; treat as passive for inflection selection
    if "deponent" in joined: return "passive"
    return ""

def detect_tense(*ctxs):
    joined = " ".join(filter(None, ctxs)).lower()
    # check multi-word first
    if "future perfect" in joined or "futureperfect" in joined: return "future perfect"
    for t in TENSES:
        if t in joined: return t
    return ""

def parse_person_and_number_from_label(label):
    # e.g. "1st sg.", "2nd pl.", "3rd singular"
    label_l = (label or "").lower()
    m = re.search(r"\b(1st|2nd|3rd)\b", label_l)
    person = PERSON_MAP.get(m.group(1), "") if m else ""
    # prefer explicit in label
    number = ""
    if re.search(r"\bsg\b\.?|\bsing(ular)?\b", label_l): number = "singular"
    if re.search(r"\bpl\b\.?|\bplur(al)?\b", label_l):   number = "plural"
    return person, number

def case_from_label(lbl):
    k = (lbl or "").strip().lower()
    return CASE_MAP.get(k, "")

def split_forms(val):
    """Split a cell into individual forms; filter blanks and dashes."""
    if not val: return []
    # filter "—" "–" "-" etc
    if val.strip() in {"-", "–", "—"}: return []
    # split on common separators
    parts = re.split(r"\s*[/;,]\s*|\s+or\s+|\s+vel\s+", val.strip(), flags=re.IGNORECASE)
    parts = [p for p in parts if p and p not in {"-", "–", "—"}]
    # some cells repeat the same token; dedupe keeping order
    seen, out = set(), []
    for p in parts:
        if p not in seen:
            out.append(p)
            seen.add(p)
    return out

# ---------- aggregate ----------
paths = sorted(glob.glob(os.path.join(OUT_DIR, "*.csv")))
paths = [p for p in paths if os.path.basename(p) not in ("lemmas.csv","forms.csv")]

lemmas = {}   # lemma_nod -> (lemma_code, lemma_nod, lemma_diac, pos, gender, page_url)
forms  = []   # rows for forms.csv

for p in paths:
    with open(p, newline="", encoding="utf-8") as f:
        r = csv.DictReader(f)
        rows = list(r)
        if not rows:
            continue

        r0 = rows[0]
        lemma_text = clean_text(r0.get("lemma_text",""))
        pos_text   = clean_text(r0.get("pos",""))
        page_url   = clean_text(r0.get("page_url",""))
        lnod       = norm(lemma_text)
        lcode      = lemma_code_from_url(page_url)

        # try to pull gender from pos (e.g., "masculine noun II declension")
        gender = ""
        pos_l = pos_text.lower()
        if "masculine" in pos_l: gender = "masculine"
        elif "feminine" in pos_l: gender = "feminine"
        elif "neuter" in pos_l:   gender = "neuter"

        if lnod not in lemmas:
            lemmas[lnod] = (lcode, lnod, lemma_text, pos_text, gender, page_url)

        is_verb = "verb" in pos_l  # heuristic; OK for main verbs

        for rr in rows:
            ctx1 = clean_text(rr.get("context_1",""))
            ctx2 = clean_text(rr.get("context_2",""))
            ctx3 = clean_text(rr.get("context_3",""))
            label = clean_text(rr.get("label",""))
            value = clean_text(rr.get("value",""))

            for form in split_forms(value):
                form_diac = form
                form_nod  = norm(form_diac)

                # default blanks
                mood = tense = voice = person = number = case = degree = ""

                if is_verb:
                    mood  = detect_mood(ctx1, ctx2, ctx3)
                    tense = detect_tense(ctx1, ctx2, ctx3)
                    voice = detect_voice(ctx1, ctx2, ctx3)

                    p_from_lbl, n_from_lbl = parse_person_and_number_from_label(label)
                    person = p_from_lbl or ""
                    # number priority: label first, then contexts
                    number = n_from_lbl or detect_number(ctx1, ctx2, ctx3, label)

                else:
                    # nouns/adjectives/pronouns-style tables
                    case = case_from_label(label)
                    number = detect_number(ctx1, ctx2, ctx3, label)

                if not form_nod:  # ignore pathological empties
                    continue

                forms.append((
                    lnod, form_nod, form_diac, label,
                    mood, tense, voice, person, number, gender, case, degree, page_url
                ))

# write outputs
os.makedirs(OUT_DIR, exist_ok=True)

with open(LEMMA_CSV, "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["lemma_code","lemma_nod","lemma_diac","pos","gender","page_url"])
    for tup in lemmas.values():
        w.writerow(tup)

with open(FORM_CSV, "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["lemma_nod","form_nod","form_diac","label",
                "mood","tense","voice","person","number","gender","case","degree","page_url"])
    w.writerows(forms)

print(f"Wrote {len(lemmas)} lemmas -> {LEMMA_CSV}")
print(f"Wrote {len(forms)}  forms  -> {FORM_CSV}")
