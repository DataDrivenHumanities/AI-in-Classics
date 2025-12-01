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
    """Detect mood from context fields and label."""
    j = " ".join(filter(None, xs)).lower()
    for m in MOODS:
        if m in j: return m
    return ""

def detect_voice(*xs) -> str:
    """Detect voice from context fields. Also checks for abbreviations and deponent verbs."""
    j = " ".join(filter(None, xs)).lower()
    
    # Look for explicit voice indicators
    if "active diathesis" in j or "voice active" in j or " active " in f" {j} ":
        return "active"
    if "passive diathesis" in j or "voice passive" in j or " passive " in f" {j} ":
        return "passive"
    if "deponent" in j:
        return "passive"
    
    # Check for voice abbreviations in labels/contexts (e.g., "act.", "pass.")
    if re.search(r"\bact\.?\b", j, re.IGNORECASE): return "active"
    if re.search(r"\bpass\.?\b", j, re.IGNORECASE): return "passive"
    
    # Check for voice in parentheses or brackets
    if re.search(r"\(.*?active.*?\)", j, re.IGNORECASE): return "active"
    if re.search(r"\(.*?passive.*?\)", j, re.IGNORECASE): return "passive"
    
    return ""

def infer_voice_from_form(form_text: str, pos_text: str = "") -> str:
    """Infer voice from form patterns when context doesn't provide it.
    This is a fallback for cases where voice isn't explicitly stated.
    Only infers passive voice from clear patterns to avoid false positives."""
    if not form_text: return ""
    form_lower = form_text.lower().strip()
    pos_lower = (pos_text or "").lower()
    
    # Skip if it's just an ending
    if form_lower.startswith(("-", "–", "—")): return ""
    
    # Perfect passive participles are the most reliable indicator
    # Pattern: stem + atus/itus/utus/etc - match at end of word
    participle_pattern = r"(?:atus|ita|itum|ati|atae|ata|itus|ita|itum|iti|itae|ita|utus|uta|utum|uti|utae|uta)$"
    if re.search(participle_pattern, form_lower):
        # If it looks like a perfect passive participle, it's passive
        # (these are very distinctive endings)
        return "passive"
    
    # Periphrastic passive forms: "perfect participle + est/esse"
    if ("est" in form_lower or "esse" in form_lower) and re.search(participle_pattern, form_lower.split()[0] if " " in form_lower else form_lower):
        return "passive"
    
    # Note: We don't infer from present/imperfect/future passive endings here
    # because they could be ambiguous. Voice should ideally come from context.
    # If context truly doesn't have it, these patterns might be added later.
    
    return ""

def detect_tense(*xs) -> str:
    """Detect tense from context fields and label."""
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

# A small set of common Latin endings so we can rebuild forms from
# patterns like stems + endings (e.g. "abalienatur" + "os", "as", "a").
LATIN_ENDINGS = [
    "ibus", "arum", "orum", "ium", "ntur", "mini", "mur", "beris", "bitur", "bor",
    "ior", "ius", "ans", "ens", "ius", "orum", "arum", "ium", "nt", "us", "um",
    "os", "is", "ae", "am", "as", "es", "im", "em", "is", "e", "o", "u", "i",
    "umurum",  # Special case like in user's example
]
LATIN_ENDINGS = sorted(set(LATIN_ENDINGS), key=len, reverse=True)

def extract_stem_and_ending(form: str) -> tuple[str, str]:
    """Extract the stem and ending from a form by matching against known Latin endings.
    Returns (stem, ending) or (form, "") if no known ending found."""
    form_lower = form.lower()
    # Try longest endings first
    for ending in LATIN_ENDINGS:
        if form_lower.endswith(ending):
            # Check if it's a word boundary (ending should be at word end)
            stem = form[:len(form) - len(ending)]
            return stem, ending
    return form, ""

def combine_ending_with_base(base_full: str, ending_form: str) -> str:
    """Combine an ending form (like '-as esse') with a base form (like 'abalienaturos esse').
    Example: base_full = 'abalienaturos esse', raw = '-as esse' -> 'abalienaturas esse'"""
    if not ending_form.startswith(("-", "–", "—")):
        return ending_form  # Not an ending form
    
    # Extract the ending and any suffix (like "esse")
    ending_part = ending_form.lstrip("-–—").strip()
    
    # Split into first word (the ending) and rest (suffix like "esse")
    parts = ending_part.split(None, 1)
    new_ending = parts[0] if parts else ""
    suffix = parts[1] if len(parts) > 1 else ""
    
    # Split base form into first word and rest
    base_parts = base_full.split(None, 1)
    base_word = base_parts[0] if base_parts else ""
    base_suffix = base_parts[1] if len(base_parts) > 1 else ""
    
    # Use suffix from ending form if provided, otherwise from base
    final_suffix = suffix if suffix else base_suffix
    
    # Extract stem from base word by removing its ending
    stem, _ = extract_stem_and_ending(base_word)
    
    # Combine stem + new ending
    new_word = stem + new_ending
    
    # Combine word + suffix
    if final_suffix:
        return f"{new_word} {final_suffix}".strip()
    return new_word

def split_forms_with_context(val, last_full_form_context=None):
    """Split form values, expanding ending-only entries by combining with previous full forms.
    Can use a last_full_form from context (across rows) as well as within the same value.
    Returns (forms_list, new_last_full_form) where new_last_full_form is only updated by
    original full forms (not ending-derived combinations)."""
    if not val: return [], last_full_form_context
    if val.strip() in {"-","–","—"}: return [], last_full_form_context
    parts = re.split(r"\s*[/;,]\s*|\s+or\s+|\s+vel\s+", val.strip(), flags=re.IGNORECASE)
    out, seen = [], set()
    base_form = last_full_form_context  # The base form that endings combine with
    new_base = last_full_form_context  # Track new base (only updated by original full forms)
    
    for p in parts:
        p = p.strip()
        if not p or p in {"-","–","—"}: continue
        
        # If it's an ending form (starts with dash), combine with base form
        if p.startswith(("-", "–", "—")):
            if base_form:
                combined = combine_ending_with_base(base_form, p)
                if combined and combined not in seen:
                    out.append(combined)
                    seen.add(combined)
                # Note: base_form stays the same - all endings combine with the original base
            # Note: if no base_form, we skip the ending-only form
        else:
            # Full form (original, not ending-derived) - keep it and update base
            if p not in seen:
                out.append(p)
                seen.add(p)
                base_form = p  # Update base form for subsequent endings
                new_base = p  # Update new_base (only original full forms update the base)
    
    return out, new_base

def split_forms(val):
    """Split form values, expanding ending-only entries by combining with previous full forms."""
    return split_forms_with_context(val, None)

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

        # Track last full form per context (to handle ending forms across rows)
        last_full_form_by_context = {}

        for rr in rows:
            ctx1, ctx2, ctx3 = clean(rr.get("context_1","")), clean(rr.get("context_2","")), clean(rr.get("context_3",""))
            label = clean(rr.get("label",""))
            value = clean(rr.get("value",""))
            
            if not value:
                continue
            
            # Create context key for tracking last full form
            context_key = (ctx1, ctx2, ctx3, label)
            
            # Get forms, passing in last full form for this context
            forms_from_value, new_base = split_forms_with_context(value, last_full_form_by_context.get(context_key))
            
            # Update last full form for this context (only updated by original full forms, not ending-derived)
            if new_base:
                last_full_form_by_context[context_key] = new_base

            for form in forms_from_value:
                form_diac = form
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
                    # If voice not found in context, try to infer from form pattern
                    if not voice:
                        voice = infer_voice_from_form(form_diac, pos_text)

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
