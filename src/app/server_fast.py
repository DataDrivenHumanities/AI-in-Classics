from __future__ import annotations
from typing import Any, Dict, List, Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import logging


logging.basicConfig(level=logging.INFO)
app = FastAPI(title="Trojan Parse API")


class AnalyzeRequest(BaseModel):
    model: str
    text: str


class ResultSchema(BaseModel):
    label: str
    score: Optional[float] = None
    details: Optional[List[Any]] = None


class AnalyzeResponse(BaseModel):
    result: ResultSchema
    translation: str = ""
    analysis: Dict[str, Any] = {}


@app.get("/api/health")
def health():
    return {"ok": True}


@app.post("/api/analyze", response_model=AnalyzeResponse)
def analyze(payload: AnalyzeRequest):
    import sys
    import importlib

    if "globals" not in sys.modules:
        sys.modules["globals"] = importlib.import_module("app.globals")

    from app import app_functions as app_func

    FRIENDLY_TO_OLLAMA = {
        "latin-ollama": "latin_model:1.0.0",
        "greek-ollama": "greek_model:1.0.0",
    }

    model_friendly = (payload.model or "").strip()
    text = (payload.text or "").strip()

    if not model_friendly or not text:
        raise HTTPException(status_code=400, detail="model and text required")

    # Translate friendly name to actual Ollama tag
    model = FRIENDLY_TO_OLLAMA.get(model_friendly, model_friendly)

    # === Call your existing sentiment logic ===
    try:
        raw = app_func.llm_sentiment(text, model)
        parsed = app_func.parse_llm_json(raw) or {}
    except Exception as e:
        msg = str(e)
        if "not found" in msg:
            raise HTTPException(
                status_code=400,
                detail=f"Ollama model '{model}' not found. "
                       f"Run `ollama serve` and ensure the tag exists (`ollama list`).",
            )
        raise HTTPException(status_code=500, detail=f"sentiment error: {e}")

    label   = (parsed.get("label") or "unknown").lower()
    score   = parsed.get("confidence")
    details = parsed.get("details")

    translation = ""
    if hasattr(app_func, "llm_translate"):
        try:
            translation = app_func.llm_translate(text, model) or ""
        except Exception:
            translation = ""

    analysis: Dict[str, Any] = {"model": model}
    if "tokens" in parsed:
        analysis["tokens"] = parsed["tokens"]

    return AnalyzeResponse(
        result=ResultSchema(label=label, score=score, details=details),
        translation=translation,
        analysis=analysis,
    )
