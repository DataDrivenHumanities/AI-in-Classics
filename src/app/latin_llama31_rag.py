from __future__ import annotations

import os
import re
from typing import Any, Dict, List, Optional

import httpx
import psycopg
from cltk import NLP

# OLLAMA_API_URL = os.getenv("OLLAMA_API_URL", "http://localhost:11434/api/generate")
# OLLAMA_RAG_MODEL = os.getenv("OLLAMA_RAG_MODEL", "latin-sentiment-llama31-5class")
# CONTEXT_MODE = os.getenv("LATIN_SENTIMENT_CONTEXT_MODE", "POLAR_ONLY").upper()
# MAX_CONTEXT_ITEMS = int(os.getenv("LATIN_SENTIMENT_MAX_CONTEXT_ITEMS", "30"))

OLLAMA_API_URL = "http://localhost:11434/api/generate"
OLLAMA_RAG_MODEL = "latin-sentiment-llama31-5class"
CONTEXT_MODE = "POLAR_ONLY"
MAX_CONTEXT_ITEMS = 30

db_url = os.environ.get("DATABASE_URL")

LABELS_5 = [
    "VERY POSITIVE",
    "SOMEWHAT POSITIVE",
    "NEUTRAL",
    "SOMEWHAT NEGATIVE",
    "VERY NEGATIVE",
]
LABEL_SET_5 = set(LABELS_5)
LABEL_SET_3 = {"POSITIVE", "NEUTRAL", "NEGATIVE"}

_LEMMATIZER: Optional[NLP] = None


def get_lemmatizer() -> NLP:
    global _LEMMATIZER
    if _LEMMATIZER is None:
        _LEMMATIZER = NLP("lat")
    return _LEMMATIZER


def resolve_database_url() -> str:
    db_url = os.getenv("DATABASE_URL", "").strip()
    if not db_url:
        raise RuntimeError("DATABASE_URL not found in environment")
    return db_url


def normalize_lemma(s: str) -> str:
    s = (s or "").strip().lower()
    s = re.sub(r"\d+$", "", s)
    return s


def extract_lemmata(doc: Any) -> List[str]:
    out: List[str] = []
    if hasattr(doc, "lemmata") and getattr(doc, "lemmata", None):
        for lemma in doc.lemmata:
            if lemma:
                out.append(normalize_lemma(lemma))
        return out
    if hasattr(doc, "words") and getattr(doc, "words", None):
        for w in doc.words:
            lemma = getattr(w, "lemma", None)
            if lemma:
                out.append(normalize_lemma(lemma))
        return out
    return out


def fetch_lemma_context(conn: psycopg.Connection, lemmas: List[str]) -> List[Dict[str, Any]]:
    lemmas = [normalize_lemma(x) for x in lemmas if x]
    lemmas = sorted(set(lemmas))
    if not lemmas:
        return []

    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT lemma, pos, polarity_score, has_polarity, provenance
            FROM lila.sentiment
            WHERE lemma = ANY(%s)
            """,
            (lemmas,),
        )
        rows = cur.fetchall()

    out: List[Dict[str, Any]] = []
    for lemma, pos, polarity_score, has_polarity, provenance in rows:
        rec = {
            "lemma": normalize_lemma(lemma),
            "pos": pos,
            "polarity_score": float(polarity_score) if polarity_score is not None else None,
            "has_polarity": has_polarity,
            "provenance": provenance,
        }
        if CONTEXT_MODE == "POLAR_ONLY" and rec["polarity_score"] is None:
            continue
        out.append(rec)

    def keyfn(r: Dict[str, Any]):
        ps = r.get("polarity_score")
        try:
            return (0, -abs(float(ps)), r["lemma"])
        except Exception:
            return (1, 0, r["lemma"])

    out.sort(key=keyfn)
    return out[:MAX_CONTEXT_ITEMS]


def format_context_rows(rows: List[Dict[str, Any]]) -> str:
    header = (
        "Lexicon evidence (lila.sentiment; word-level polarity hints only).\n"
        "These hints may be misleading and MUST NOT override the overall meaning "
        "of the full Latin sentence.\n"
    )
    if not rows:
        return (
            header
            + "\n(no lemma matches found)\n\n"
            + "Return exactly one label from this set:\n"
            "VERY POSITIVE\n"
            "SOMEWHAT POSITIVE\n"
            "NEUTRAL\n"
            "SOMEWHAT NEGATIVE\n"
            "VERY NEGATIVE\n"
        )

    lines = [header.rstrip(), "Lexicon entries:"]
    for r in rows:
        lines.append(
            f"- lemma={r['lemma']} pos={r.get('pos')} polarity_score={r.get('polarity_score')} "
            f"has_polarity={r.get('has_polarity')} provenance={r.get('provenance')}"
        )
    lines.extend(
        [
            "",
            "Return exactly one label from this set:",
            "VERY POSITIVE",
            "SOMEWHAT POSITIVE",
            "NEUTRAL",
            "SOMEWHAT NEGATIVE",
            "VERY NEGATIVE",
        ]
    )
    return "\n".join(lines) + "\n"


def build_prompt(sentence: str, context_rows: List[Dict[str, Any]]) -> str:
    ctx = format_context_rows(context_rows)
    return (
        f"{ctx}\n"
        f"Latin text: {sentence}\n\n"
        "Classify the overall sentiment of the Latin text. "
        "Output only one label and no explanation.\n"
    )


def normalize_prediction_5(text: str) -> str:
    s = (text or "").strip()
    up = s.upper()
    for lab in LABELS_5:
        if lab in up:
            return lab
    if s:
        s = s.splitlines()[0].strip()
        s = s.strip(" \t\r\n\"'`.,:;!")
        return s.upper()
    return "UNKNOWN"


def collapse_to_3(label_5: str) -> str:
    up = (label_5 or "").upper()
    if up == "NEUTRAL":
        return "neutral"
    if "POSITIVE" in up:
        return "positive"
    if "NEGATIVE" in up:
        return "negative"
    return "neutral"


async def ollama_generate(prompt: str, model: Optional[str] = None, timeout_s: int = 180) -> str:
    payload = {
        "model": model or OLLAMA_RAG_MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {"num_predict": 40, "temperature": 0, "top_p": 0.9},
    }
    async with httpx.AsyncClient(timeout=timeout_s) as client:
        r = await client.post(OLLAMA_API_URL, json=payload)
        r.raise_for_status()
        return (r.json().get("response") or "").strip()


async def analyze_latin_sentiment_with_rag(text: str, model_name: Optional[str] = None) -> Dict[str, Any]:
    text = (text or "").strip()
    if not text:
        raise ValueError("text must be non-empty")

    print("RAG: starting")
    lemmatizer = get_lemmatizer()
    print("RAG: got lemmatizer")

    doc = lemmatizer.analyze(text)
    print("RAG: analyzed text")

    lemmas = extract_lemmata(doc)
    print("RAG: lemmas =", lemmas)

    dbu = resolve_database_url()
    print("RAG: db url present =", bool(dbu))

    with psycopg.connect(dbu) as conn:
        print("RAG: connected to postgres")
        context_rows = fetch_lemma_context(conn, lemmas)
        print("RAG: context rows =", len(context_rows))

    prompt = build_prompt(text, context_rows)
    chosen_model = model_name or OLLAMA_RAG_MODEL
    print("RAG: model =", chosen_model)
    raw = await ollama_generate(prompt, model=chosen_model)
    print("RAG: ollama raw =", raw)

    pred5 = normalize_prediction_5(raw)
    label3 = collapse_to_3(pred5)
    print("RAG: pred5 =", pred5, "label3 =", label3)

    pos_score = 1.0 if label3 == "positive" else 0.0
    neg_score = 1.0 if label3 == "negative" else 0.0
    neu_score = 1.0 if label3 == "neutral" else 0.0

    return {
        "engine": "ollama-rag",
        "label": label3,
        "confidence": 0.9 if pred5 in LABEL_SET_5 else 0.5,
        "scores": {
            "positive": pos_score,
            "negative": neg_score,
            "neutral": neu_score,
        },
        "raw_model_output": raw,
        "translation": None,
        "analysis": {
            "predicted_5": pred5,
            "lemmas": sorted(set(lemmas)),
            "context_hits": len(context_rows),
            "context_rows": context_rows,
            "prompt": prompt,
        },
    }