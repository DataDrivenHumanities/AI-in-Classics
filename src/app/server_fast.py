# src/app/server_fast.py
from __future__ import annotations

import os
import httpx
import pathlib
import sys
from typing import Dict, Iterable, List, Literal, Optional, Any

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi import HTTPException
from pydantic import BaseModel, Field


from app.routers.probing_router import ProbingRouter
from app.routers.chat_router import make_default_router as make_chat_router  # type: ignore
from app.routers.chat_router import Message as ChatMessage  # type: ignore
from app.routers.sentiment_router import (  # type: ignore
    make_default_sentiment_router,
    SentimentResult,
)
from app.ollama_client import translate_en
from app.model_registry import resolve_model

_VALID_LABELS = {"positive", "negative", "neutral"}
_VALID = {"positive", "negative", "neutral"}

app = FastAPI(
    title="Trojan Parse FastAPI Server",
    version="1.0.0",
    description="Unified chat and sentiment analysis endpoints",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


probing = ProbingRouter()
app.include_router(probing.router, prefix="/api")


class AnalyzeBody(BaseModel):
    text: str
    engine: str = "model"
    model_id: Optional[str] = None


def _builtin_sentiment(text: str) -> Dict[str, Any]:
    from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

    sia = SentimentIntensityAnalyzer()
    vs = sia.polarity_scores(text)
    compound = float(vs.get("compound", 0.0))
    label = (
        "positive"
        if compound >= 0.05
        else "negative" if compound <= -0.05 else "neutral"
    )

    return {
        "engine": "builtin",
        "label": label,
        "confidence": abs(compound),
        "scores": {
            "compound": compound,
            "pos": float(vs.get("pos", 0.0)),
            "neu": float(vs.get("neu", 0.0)),
            "neg": float(vs.get("neg", 0.0)),
        },
        "raw_model_output": "",
        "translation": None,
        "analysis": {"heuristic": "vader", "thresholds": {"pos": 0.05, "neg": -0.05}},
    }


def _clamp01(x):
    try:
        v = float(x)
    except Exception:
        return 0.0
    if v < 0:
        return 0.0
    if v > 1:
        return 1.0
    return v


def _norm_scores(label, scores, confidence):
    if isinstance(scores, dict) and all(
        k in scores for k in ("positive", "negative", "neutral")
    ):
        p = _clamp01(scores.get("positive", 0.0))
        n = _clamp01(scores.get("negative", 0.0))
        z = _clamp01(scores.get("neutral", 0.0))
        s = p + n + z
        if s > 0:
            return {"positive": p / s, "negative": n / s, "neutral": z / s}
    c = confidence if isinstance(confidence, (int, float)) else 0.7
    c = _clamp01(c)
    if label == "positive":
        return {"positive": c, "negative": 1 - c, "neutral": 0.0}
    if label == "negative":
        return {"positive": 1 - c, "negative": c, "neutral": 0.0}
    return {"positive": 0.15, "negative": 0.15, "neutral": 0.70}


def _pick_translation(val):
    if val is None:
        return None
    if isinstance(val, str):
        s = val.strip()
        return s or None
    if isinstance(val, dict):
        for k in ("en-US", "en", "english", "translation", "value"):
            v = val.get(k)
            if isinstance(v, str) and v.strip():
                return v.strip()
        for v in val.values():
            if isinstance(v, str) and v.strip():
                return v.strip()
    return None


async def _classify_one_word(model_id: str, text: str) -> str:
    from .ollama_client import generate_text

    out = await generate_text(
        model_id,
        f"Classify the sentiment of the text as exactly one lowercase word from this set: positive, negative, neutral.\nText: {text}\nAnswer with one word only:",
        num_predict=3,
    )
    w = out.strip().split()[0].lower() if out else ""
    return w if w in _VALID else "neutral"


async def _analyze_with_model(text: str, model_id: str):
    from .ollama_client import generate_json, translate_en

    prompt = (
        "Return ONLY a JSON object with these exact keys and types; do not include any other keys or text. "
        'label: one of ["positive","negative","neutral"]; '
        "confidence: number in [0,1]; "
        'scores: object with keys {"positive","negative","neutral"} and numeric values in [0,1]; '
        "translation: string or null; "
        "analysis: object or null. "
        f"Text: {text}"
    )

    parsed, raw = await generate_json(
        model_id, prompt, num_predict=768, temperature=0.0
    )

    label = str(parsed.get("label") or "").strip().lower()
    if ("|" in label) or (label not in _VALID):
        label = await _classify_one_word(model_id, text)

    conf = parsed.get("confidence")
    try:
        confidence = float(conf)
    except Exception:
        confidence = 0.7 if label != "neutral" else 0.5
    confidence = _clamp01(confidence)

    scores = _norm_scores(label, parsed.get("scores"), confidence)

    translation = _pick_translation(parsed.get("translation"))
    if not translation:
        try:
            translation = await translate_en(model_id, text)
        except Exception:
            translation = None

    analysis = (
        parsed.get("analysis") if isinstance(parsed.get("analysis"), dict) else None
    )

    return {
        "engine": "model",
        "label": label,
        "confidence": confidence,
        "scores": scores,
        "raw_model_output": raw,
        "translation": translation,
        "analysis": analysis,
    }


def _normalize_model_payload(parsed: Dict[str, Any], raw: str) -> Dict[str, Any]:
    label = str(parsed.get("label") or "").strip().lower()
    if label not in _VALID_LABELS:
        # try to infer from obvious words; fallback neutral
        lex_pos = {"pulcher", "pulchrum", "laetus", "bonus"}
        lex_neg = {"malus", "tristis", "ira"}
        src = raw.lower()
        if any(w in src for w in lex_pos):
            label = "positive"
        elif any(w in src for w in lex_neg):
            label = "negative"
        else:
            label = "neutral"

    # confidence
    conf = parsed.get("confidence")
    try:
        confidence = float(conf)
    except Exception:
        confidence = 0.7 if label != "neutral" else 0.5

    # scores
    scores = _coerce_scores(label, confidence, parsed.get("scores"))

    # translation
    translation = _pick_translation(parsed.get("translation"))

    # analysis: object or None
    analysis = parsed.get("analysis")
    if not isinstance(analysis, dict):
        analysis = None

    return {
        "label": label,
        "confidence": float(confidence),
        "scores": scores,
        "translation": translation,
        "analysis": analysis,
    }


# Singletons
DEFAULT_OLLAMA_MODEL = os.getenv("DEFAULT_OLLAMA_MODEL", "llama3.1")
chat_router = make_chat_router(DEFAULT_OLLAMA_MODEL)
sent_router = make_default_sentiment_router()


Role = Literal["system", "user", "assistant"]


class ChatRequest(BaseModel):
    model_id: str = Field(..., description="e.g., 'llama3.1' or 'ollama/llama3.1'")
    messages: List[ChatMessage] = Field(
        ..., description='List of {"role","content"} messages'
    )
    temperature: float = 0.2
    max_tokens: Optional[int] = None
    stream: bool = False
    extra: Dict[str, Any] = Field(
        default_factory=dict, description="Additional provider kwargs"
    )


class ChatResponse(BaseModel):
    model_id: str
    content: str


class AnalyzeRequest(BaseModel):
    text: str = Field(..., description="Text to analyze")
    engine: str = Field(
        "builtin", description="Either 'builtin' (VADER) or 'model' (LLM)"
    )
    model_id: Optional[str] = Field(
        None, description="Model to use when engine='model'"
    )
    extra: Dict[str, Any] = Field(default_factory=dict)


# ------------------------------------------------------------------------------
# -----------   Health Endpoint  -----------   -----------   -----------
# ------------------------------------------------------------------------------


@app.get("/api/health")
def api_health():
    return {"ok": True, "service": "trojan-parse-api"}


# ------------------------------------------------------------------------------
#  -----------   Chat endpoint  -----------   -----------   -----------
# ------------------------------------------------------------------------------


@app.post("api/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    try:
        if not req.messages:
            raise HTTPException(status_code=400, detail="messages must be non-empty")

        if req.stream:

            def gen() -> Iterable[bytes]:
                for chunk in chat_router.respond_once(
                    req.model_id,
                    req.messages,
                    temperature=req.temperature,
                    max_tokens=req.max_tokens,
                    stream=True,
                    **req.extra,
                ):
                    yield chunk.encode("utf-8")

            return StreamingResponse(gen(), media_type="text/plain; charset=utf-8")

        text = chat_router.respond_once(
            req.model_id,
            req.messages,
            temperature=req.temperature,
            max_tokens=req.max_tokens,
            stream=False,
            **req.extra,
        )
        if not isinstance(text, str):
            text = "".join(list(text))
        return ChatResponse(model_id=req.model_id, content=text)

    except HTTPException:
        raise
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"chat error: {e}")


# ------------------------------------------------------------------------------
#  -----------  Sentiment endpoints  -----------   -----------   -----------
# ------------------------------------------------------------------------------


@app.post("/api/analyze")
async def analyze(body: AnalyzeBody):
    text = body.text
    engine = (body.engine or "model").lower()
    try:
        if engine == "model":
            model_id = resolve_model(body.model_id)
            res = await _analyze_with_model(text, model_id)
            return JSONResponse(res)
        res = _builtin_sentiment(text)
        return JSONResponse(res)
    except (httpx.ReadTimeout, httpx.ConnectTimeout):
        raise HTTPException(status_code=504, detail="Model backend timeout")
    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail=f"Model backend error: {str(e)}")


@app.post("/api/analyze/upload")
async def analyze_upload(
    file: UploadFile = File(...),
    engine: str = Form("model"),
    model_id: Optional[str] = Form(None),
):
    text = (await file.read()).decode(errors="ignore")
    if (engine or "model").lower() == "model":
        mid = resolve_model(model_id)
        res = await _analyze_with_model(text, mid)
        return JSONResponse(res)
    res = _builtin_sentiment(text)
    if res.get("translation") in (None, ""):
        mid = resolve_model(model_id)
        try:
            tr = await translate_en(mid, text)
            if tr:
                res["translation"] = tr
                res.setdefault("analysis", {}).update({"translator": "ollama"})
        except Exception:
            pass
    return JSONResponse(res)
