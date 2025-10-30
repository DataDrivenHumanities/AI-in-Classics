# src/api/server_fast.py
from __future__ import annotations
from typing import Any, Optional, List, Dict

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel


import app_functions as app_func
import model_registry as model_cfg

app = FastAPI(title="Trojan Parse API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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

try:
    registry = model_cfg.get_registry()
except Exception as e:
    registry = None
    print(f"[api] Model registry init failed: {e}")

@app.get("/api/health")
def health():
    return {"ok": True}

@app.post("/api/analyze", response_model=AnalyzeResponse)
def analyze(payload: AnalyzeRequest):
    model = (payload.model or "").strip()
    text  = (payload.text  or "").strip()

    if not model or not text:
        raise HTTPException(status_code=400, detail="model and text required")

    if registry:
        ids = [m.model_id for m in registry.available_models()]
        # if you need mapping, add it here


    try:
        raw = app_func.llm_sentiment(text, model)
        parsed = app_func.parse_llm_json(raw) or {}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"sentiment error: {e}")

    label = (parsed.get("label") or "unknown").lower()
    score = parsed.get("confidence")
    details = parsed.get("details")

    # ---- Optional translation ----
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
