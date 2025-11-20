import re
import unicodedata
from typing import Dict, Optional

# strip " – Active/Passive diathesis" from lemma headings (for lemma_nod / cleaned display)
_DIATHESIS_TAIL = re.compile(r"\s*[-–—]?\s*(active|passive)\s+diathesis\s*$", re.I)


def strip_accents(s: str) -> str:
    if not s:
        return ""
    nf = unicodedata.normalize("NFD", s)
    return "".join(ch for ch in nf if not unicodedata.combining(ch))


def clean_lemma_text(t: str) -> str:
    """
    Used when normalizing lemma_nod / lemma_diac for the DB.
    We *only* strip diathesis here, not in morph detection.
    """
    return _DIATHESIS_TAIL.sub("", (t or "").strip())


ROMAN_TO_PERSON = {"I": "first", "II": "second", "III": "third"}

ABBR_NUMBER = {
    "SING.": "singular",
    "PLUR.": "plural",
    "SING": "singular",
    "PLUR": "plural",
}

ABBR_CASE = {
    "NOM.": "nominative",
    "GEN.": "genitive",
    "DAT.": "dative",
    "ACC.": "accusative",
    "ABL.": "ablative",
    "VOC.": "vocative",
    "LOC.": "locative",
    "INSTR.": "instrumental",
}

ABBR_GENDER = {
    "MASC.": "masculine",
    "FEM.": "feminine",
    "NEUT.": "neuter",
    "MASCULINE": "masculine",
    "FEMININE": "feminine",
    "NEUTER": "neuter",
}

DEGREE_MAP = {
    "POS.": "positive",
    "COMP.": "comparative",
    "SUP.": "superlative",
    "POSITIVE": "positive",
    "COMPARATIVE": "comparative",
    "SUPERLATIVE": "superlative",
}

MOOD_MAP = {
    "INDICATIVE": "indicative",
    "SUBJUNCTIVE": "subjunctive",
    "IMPERATIVE": "imperative",
    "INFINITIVE": "infinitive",
    "PARTICIPLE": "participle",
    "GERUND": "gerund",
    "GERUNDIVE": "gerundive",
    "SUPINE": "supine",
}

TENSE_MAP = {
    "PRESENT": "present",
    "IMPERFECT": "imperfect",
    "FUTURE": "future",
    "PERFECT": "perfect",
    "PLUPERFECT": "pluperfect",
    "FUTURE PERFECT": "future perfect",
}

# Normalize all voice-y phrases to canonical lower-case values
VOICE_MAP = {
    "ACTIVE DIATHESIS": "active",
    "ACTIVEDIATHESIS": "active",
    "PASSIVE DIATHESIS": "passive",
    "PASSIVEDIATHESIS": "passive",
    "ACTIVE VOICE": "active",
    "PASSIVE VOICE": "passive",
    "ACTIVE": "active",
    "PASSIVE": "passive",
    "DEPONENT": "deponent",
    "MIDDLE": "middle",
}

_rx_roman = re.compile(r"\b(III|II|I)\b")
_rx_1st = re.compile(r"\b1(?:st)?\b", re.I)
_rx_2nd = re.compile(r"\b2(?:nd)?\b", re.I)
_rx_3rd = re.compile(r"\b3(?:rd)?\b", re.I)
_rx_sg = re.compile(r"\b(sg|sing|sing\.|singular)\b", re.I)
_rx_pl = re.compile(r"\b(pl|plur|pl\.|plural)\b", re.I)


def _pick(mapping: Dict[str, str], text: Optional[str]) -> Optional[str]:
    if not text:
        return None
    up = text.upper()
    # longest keys first so "ACTIVE DIATHESIS" beats plain "ACTIVE"
    for key in sorted(mapping, key=len, reverse=True):
        if key in up:
            return mapping[key]
    return None


def _first_hit(mapping: Dict[str, str], *fields: Optional[str]) -> Optional[str]:
    for fld in fields:
        v = _pick(mapping, fld)
        if v:
            return v
    return None


def _detect_person(*fields: Optional[str]) -> Optional[str]:
    for fld in fields:
