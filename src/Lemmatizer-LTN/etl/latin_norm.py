import re, unicodedata
from typing import Dict, Optional

# strip “ – Active/Passive diathesis” from lemma headings
_DIATHESIS_TAIL = re.compile(r"\s*[-–—]?\s*(active|passive)\s+diathesis\s*$", re.I)

def strip_accents(s: str) -> str:
    if not s: return ""
    nf = unicodedata.normalize("NFD", s)
    return "".join(ch for ch in nf if not unicodedata.combining(ch))

def clean_lemma_text(t: str) -> str:
    return _DIATHESIS_TAIL.sub("", (t or "").strip())

ROMAN_TO_PERSON = {"I":"first","II":"second","III":"third"}
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
             "PERFECT":"perfect","PLUPERFECT":"pluperf." , "FUTURE PERFECT":"future perfect"}
VOICE_MAP = {"ACTIVE":"active","PASSIVE":"passive",
             "ACTIVE DIATHESIS":"active","PASSIVE DIATHESIS":"passive",
             "DEPONENT":"deponent","MIDDLE":"middle"}

_rx_roman = re.compile(r"\b(III|II|I)\b")
_rx_1st   = re.compile(r"\b1(?:st)?\b", re.I)
_rx_2nd   = re.compile(r"\b2(?:nd)?\b", re.I)
_rx_3rd   = re.compile(r"\b3(?:rd)?\b", re.I)
_rx_sg    = re.compile(r"\b(sg|sing|sing\.|singular)\b", re.I)
_rx_pl    = re.compile(r"\b(pl|plur|pl\.|plural)\b", re.I)

def _pick(mapping: Dict[str,str], text: Optional[str]) -> Optional[str]:
    if not text: return None
    up = text.upper()
    for key in sorted(mapping, key=len, reverse=True):
        if key in up:
            return mapping[key]
    return None

def _first_hit(mapping: Dict[str,str], *fields: Optional[str]) -> Optional[str]:
    for fld in fields:
        v = _pick(mapping, fld)
        if v: return v
    return None

def _detect_person(*fields: Optional[str]) -> Optional[str]:
    for fld in fields:
        if not fld: continue
        if (m := _rx_roman.search(fld)): return ROMAN_TO_PERSON[m.group(1)]
        if _rx_1st.search(fld): return "first"
        if _rx_2nd.search(fld): return "second"
        if _rx_3rd.search(fld): return "third"
    return None

def _detect_number(*fields: Optional[str]) -> Optional[str]:
    for fld in fields:
        if not fld: continue
        if _rx_pl.search(fld):  return "plural"    # prefer explicit "plural"
        if _rx_sg.search(fld):  return "singular"
        v = _pick(ABBR_NUMBER, fld)
        if v: return v
    return None

def _detect_case(*fields: Optional[str]) -> str:
    # case almost always lives in the label like "Nom.", "Gen.", …
    label = fields[0] if fields else ""
    if not label: return ""
    up = label.upper()
    for k, name in ABBR_CASE.items():
        if k in up: return name
    return ""

def normalize_morph(row: dict) -> dict:
    # check fields in priority: label, then closest titles (context_3->2->1), then pos
    label = (row.get("label") or "")
    c1 = row.get("context_1") or ""
    c2 = row.get("context_2") or ""
    c3 = row.get("context_3") or ""
    pos = row.get("pos") or ""

    mood   = _first_hit(MOOD_MAP,   label, c3, c2, c1)
    tense  = _first_hit(TENSE_MAP,  label, c3, c2, c1)
    voice  = _first_hit(VOICE_MAP,  label, c3, c2, c1)
    gender = _first_hit(ABBR_GENDER,label, c3, c2, c1, pos)

    number = _detect_number(label, c3, c2, c1)
    case   = _detect_case(label, c3, c2, c1)
    person = _detect_person(label, c3, c2, c1)

    degree = _first_hit(DEGREE_MAP, label, c3, c2, c1)

    return {
        "mood":   mood   or "",
        "tense":  tense  or "",
        "voice":  voice  or "",
        "person": person or "",
        "number": number or "",
        "gender": gender or "",
        "case":   case   or "",
        "degree": degree or "",
    }
