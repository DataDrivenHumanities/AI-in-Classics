# Aggregates per-lemma CSVs in ../out/ into lemmas.csv + forms.csv
from pathlib import Path
import csv, re, unicodedata, glob
from urllib.parse import urlparse, parse_qs

BASE = Path(__file__).resolve().parents[1]          # .../Lemmatizer-LTN
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

def lemma_code_from_url(u: str):
    try:
        q = parse_qs(urlparse(u or "").query)
        return (q.get("lemma") or [None])[0]
    except Exception:
        return None

CASE_MAP = {
    "nom.":"nominative","gen.":"genitive","dat.":"dative",
    "acc.":"accusative","abl.":"ablative","voc.":"vocative",
    "loc.":"locative","ins.":"instrumental"
}
NUM_SG = {"singular","sing.","sg","sg."}
NUM_PL = {"plural","plur.","pl","pl."}
MOODS  = {"indicative","subjunctive","imperative","infinitive","participle","gerund","gerundive","supine"}
VOICES = {"active","passive"}
TENSES = {"present","imperfect","future","perfect","pluperfect","future perfect","futureperfect"}
PERSON_MAP = {"1st":"first","2nd":"second","3rd":"third"}

def clean(s): return (s or "").strip()

def detect_number(*xs):
    j = " ".join(filter(None, xs)).lower()
    if any(t in j for t in NUM_SG): return "singular"
    if any(t in j for t in NUM_PL): return "plural"
    if re.search(r"\bsg\b\.?", j): return "singular"
    if re.search(r"\bpl\b\.?", j): return "plural"
    return ""

def detect_mood(*xs):
    j = " ".join(filter(None, xs)).lower()
    for m in MOODS:
        if m in j: return m
    return ""

def detect_voice(*xs):
    j = " ".join(filter(None, xs)).lower()
    for v in VOICES:
        if v in j: return v
    if "deponent" in j: return "passive"
    return ""

def detect_tense(*xs):
    j = " ".join(filter(None, xs)).lower()
    if "future perfect" in j or "futureperfect" in j: return "future perfect"
    for t in TENSES:
        if t in j: return t
    return ""

def person_num_from_label(label):
    ll = (label or "").lower()
    m = re.search(r"\b(1st|2nd|3rd)\b", ll)
    person = PERSON_MAP.get(m.group(1), "") if m else ""
    number = "singular" if re.search(r"\bsg\b\.?|\bsing(ular)?\b", ll) else \
             "plural"   if re.search(r"\bpl\b\.?|\bplur(al)?\b", ll) else ""
    return person, number

def case_from_label(lbl): return CASE_MAP.get((lbl or "").strip().lower(), "")

def split_forms(val):
    if not val: return []
    if val.strip() in {"-","–","—"}: return []
    parts = re.split(r"\s*[/;,]\s*|\s+or\s+|\s+vel\s+", val.strip(), flags=re.IGNORECASE)
    out, seen = [], set()
    for p in parts:
        if p and p not in {"-","–","—"} and p not in seen:
            out.append(p); seen.add(p)
    return out

def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    paths = [p for p in glob.glob(str(OUT_DIR / "*.csv"))
             if Path(p).name not in ("lemmas.csv","forms.csv")]

    lemmas = {}     # lemma_nod -> tuple(row)
    forms  = []

    for p in paths:
        with open(p, newline="", encoding="utf-8") as f:
            r = csv.DictReader(f); rows = list(r)
        if not rows: continue

        r0 = rows[0]
        lemma_text = clean(r0.get("lemma_text",""))
        pos_text   = clean(r0.get("pos",""))
        page_url   = clean(r0.get("page_url",""))
        lnod       = norm(lemma_text)
        lcode      = lemma_code_from_url(page_url)

        gender = ""
        pl = pos_text.lower()
        if   "masculine" in pl: gender = "masculine"
        elif "feminine"  in pl: gender = "feminine"
        elif "neuter"    in pl: gender = "neuter"

        lemmas.setdefault(lnod, (lcode, lnod, lemma_text, pos_text, gender, page_url))
        is_verb = "verb" in pl

        for rr in rows:
            ctx1, ctx2, ctx3 = clean(rr.get("context_1","")), clean(rr.get("context_2","")), clean(rr.get("context_3",""))
            label = clean(rr.get("label",""))
            value = clean(rr.get("value",""))

            for form in split_forms(value):
                form_diac = form
                form_nod  = norm(form_diac)
                if not form_nod: continue

                mood=tense=voice=person=number=case=degree=""

                if is_verb:
                    mood  = detect_mood(ctx1,ctx2,ctx3)
                    tense = detect_tense(ctx1,ctx2,ctx3)
                    voice = detect_voice(ctx1,ctx2,ctx3)
                    p_lbl, n_lbl = person_num_from_label(label)
                    person = p_lbl
                    number = n_lbl or detect_number(ctx1,ctx2,ctx3,label)
                else:
                    case   = case_from_label(label)
                    number = detect_number(ctx1,ctx2,ctx3,label)

                forms.append((lnod, form_nod, form_diac, label,
                              mood, tense, voice, person, number, gender, case, degree, page_url))

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
    print(f"Wrote {len(forms)}  forms  -> {FORM_CSV}")

if __name__ == "__main__":
    main()
