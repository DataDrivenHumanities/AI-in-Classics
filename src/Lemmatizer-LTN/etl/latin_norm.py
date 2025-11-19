import re, unicodedata
from typing import Dict, Optional

# strip “ – Active/Passive diathesis” from verb lemma headings
_DIATHESIS_TAIL = re.compile(r"\s*[-–—]?\s*(active|passive)\s+diathesis\s*$", re.I)

def strip_accents(s: str) -> str:
    if not s: return ""
    nf = unicodedata.normalize("NFD", s)
    return "".join(ch for ch in nf if not unicodedata.combining(ch))

def norm(s: str) -> str:
    import re as _re
    return _re.sub(r"[^a-z0-9]+", "", strip_accents((s or "").lower()))

def clean_lemma_text(t: str) -> str:
    return _DIATHESIS_TAIL.sub("", (t or "").strip())

# --------- mappings ---------
ROMAN_TO_PERSON = {"I": "first", "II": "second", "III": "third"}
ABBR_NUMBER = {"SING.":"singular","PLUR.":"plural","SING":"singular","PLUR":"plural"}
ABBR_CASE = {
    "NOM.":"nominative","GEN.":"genitive","DAT.":"dative","ACC.":"accusative",
    "ABL.":"ablative","VOC.":"vocative","LOC.":"locative","INSTR.":"instrumental"
}
ABBR_GENDER = {"MASC.":"masculine","FEM.":"feminine","NEUT.":"neuter",
               "MASCULINE":"masculine","FEMININE":"feminine","NEUTER":"neuter"}
DEGREE_MAP = {"POS.":"positive","COMP.":"comparative","SUP.":"superlative",
              "POSITIVE":"positive","COMPARATIVE":"comparative","SUPERLATIVE":"superlative"}
MOOD_MAP = {"INDICATIVE":"indicative","SUBJUNCTIVE":"subjunctive","IMPERATIVE":"imperative",
            "INFINITIVE":"infinitive","PARTICIPLE":"participle","GERUND":"gerund",
            "GERUNDIVE":"gerundive","SUPINE":"supine"}
TENSE_MAP = {"PRESENT":"present","IMPERFECT":"imperfect","FUTURE":"future",
             "PERFECT":"perfect","PLUPERFECT":"pluperfect","FUTURE PERFECT":"future perfect"}
VOICE_MAP = {"ACTIVE":"active","PASSIVE":"passive",
             "ACTIVE DIATHESIS":"active","PASSIVE DIATHESIS":"passive",
             "DEPONENT":"deponent","MIDDLE":"middle"}

# --------- detectors ---------
_rx_roman = re.compile(r"\b(III|II|I)\b")
_rx_1st   = re.compile(r"\b1(?:st)?\b", re.I)
_rx_2nd   = re.compile(r"\b2(?:nd)?\b", re.I)
_rx_3rd   = re.compile(r"\b3(?:rd)?\b", re.I)
_rx_sg    = re.compile(r"\b(sg|sing|sing\.|singular)\b", re.I)
_rx_pl    = re.compile(r"\b(pl|plur|pl\.|plural)\b", re.I)
_rx_case_tokens = [
    (re.compile(r"\bnom(?:\.|in(?:ative)?)?\b", re.I), "nominative"),
    (re.compile(r"\bgen(?:\.|it(?:ive)?)?\b", re.I),   "genitive"),
    (re.compile(r"\bdat(?:\.|iv(?:e)?)?\b", re.I),     "dative"),
    (re.compile(r"\bacc(?:\.|us(?:ative)?)?\b", re.I), "accusative"),
    (re.compile(r"\babl(?:\.|at(?:ive)?)?\b", re.I),   "ablative"),
    (re.compile(r"\bvoc(?:\.|at(?:ive)?)?\b", re.I),   "vocative"),
    (re.compile(r"\bloc(?:\.|at(?:ive)?)?\b", re.I),   "locative"),
]

def _pick(mapping: Dict[str,str], text: str) -> Optional[str]:
    up = (text or "").toUpperCase() if hasattr(text, "toUpperCase") else (text or "").upper()
    for key in sorted(mapping, key=len, reverse=True):
        if key in up:
            return mapping[key]
    return None

def _detect_person(label_up: str) -> Optional[str]:
    m = _rx_roman.search(label_up)
    if m: return ROMAN_TO_PERSON[m.group(1)]
    if _rx_1st.search(label_up): return "first"
    if _rx_2nd.search(label_up): return "second"
    if _rx_3rd.search(label_up): return "third"
    return None

def _detect_number(text_up: str) -> Optional[str]:
    if _rx_sg.search(text_up): return "singular"
    if _rx_pl.search(text_up): return "plural"
    return None

def _detect_case(label: str) -> str:
    for rx, name in _rx_case_tokens:
        if rx.search(label or ""): return name
    return ""

def normalize_morph(row: dict) -> dict:
    """
    Input: one per-lemma CSV row with keys:
      label, context_1, context_2, context_3, value, [number_hint], [gender_hint], [voice_hint]
    Output: dict with mood/tense/voice/person/number/gender/case/degree (lowercased words).
    """
    ctx = " | ".join([row.get("context_1") or "", row.get("context_2") or "", row.get("context_3") or ""])
    label = (row.get("label") or "").strip()
    up_ctx = ctx.upper(); up_lab = label.upper()

    mood   = _pick(MOOD_MAP,   up_ctx) or _pick(MOOD_MAP,   up_lab) or ""
    tense  = _pick(TENSE_MAP,  up_ctx) or _pick(TENSE_MAP,  up_lab) or ""
    voice  = _pick(VOICE_MAP,  up_ctx) or _pick(VOICE_MAP,  up_lab) or ""
    gender = _pick(ABBR_GENDER,up_ctx) or _pick(ABBR_GENDER,up_lab) or ""

    number = _detect_number(up_lab) or _pick(ABBR_NUMBER, up_ctx) or _pick(ABBR_NUMBER, up_lab) or ""
    degree = _pick(DEGREE_MAP, up_ctx) or _pick(DEGREE_MAP, up_lab) or ""
    case   = _detect_case(label)

    person = _detect_person(up_lab) or ""

    # Prefer scraper hints if present
    if "number_hint" in row and not number:
        number = (row.get("number_hint") or "").lower()
    if "gender_hint" in row and not gender:
        gender = (row.get("gender_hint") or "").lower()
    if "voice_hint" in row and not voice:
        voice = (row.get("voice_hint")  or "").lower()

    return {
        "mood": mood, "tense": tense, "voice": voice, "person": person,
        "number": number, "gender": gender, "case": case, "degree": degree
    }
