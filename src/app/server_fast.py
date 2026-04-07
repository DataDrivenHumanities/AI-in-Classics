from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field
from typing import Dict, Iterable, List, Literal, Optional, Any
from pathlib import Path
import json
import os
import httpx

from .routers.probing_router import ProbingRouter
from .routers.chat_router import make_default_router as make_chat_router  # type: ignore
from .routers.chat_router import Message as ChatMessage
from .routers.sentiment_router import make_default_sentiment_router
from .routers import presets_router
from .routers import feedback_router
from .routers import train_router
from .routers.latin_workspace_router import router as latin_workspace_router

from .model_registry import get_registry, available_model_ids
from .ollama_client import (
    generate_json_with_analysis,
    translate_en,
    resolve_available_model_tag,
)

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
app.include_router(presets_router.router)
app.include_router(feedback_router.router)
app.include_router(train_router.router)
app.include_router(latin_workspace_router, prefix="/api")

DEFAULT_OLLAMA_MODEL = os.getenv("DEFAULT_OLLAMA_MODEL", "llama3.1")
chat_router = make_chat_router(DEFAULT_OLLAMA_MODEL)
sent_router = make_default_sentiment_router()


class AnalyzeBody(BaseModel):
    text: str
    model_id: Optional[str] = None
    options: Optional[Dict[str, Any]] = None
    raw: Optional[bool] = None
    format: Optional[str] = None
    provider: Optional[str] = None
    openrouter_model: Optional[str] = None


def resolve_model(model_id: Optional[str]):
    if model_id:
        return model_id
    reg_paths = [
        Path(__file__).with_name("model_registry.json"),
        Path(__file__).parent.with_name("app").joinpath("model_registry.json"),
        Path.cwd().joinpath("model_registry.json"),
    ]
    for p in reg_paths:
        if p.exists():
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
                d = data.get("default")
                if isinstance(d, str) and d:
                    return d
            except Exception:
                pass
    return "latin_ollama_model:1.0.0"

def resolve_engine(model_id: str) -> str:
    try:
        registry = get_registry()
        model = registry.get(model_id)
        return model.provider
    except Exception as e:
        print(f"Model with id {model_id} not found in registry: {e}")
        return ""

def resolve_hf_params(model_id: str):
    try:
        registry = get_registry()
        model = registry.get(model_id)
        return model.hf_classifier_params
    except Exception as e:
        print(f"Model with id {model_id} not found in registry: {e}")
        return {}

def _hf_sentiment(text: str, hf_classifier_params: Optional[Dict[str, Any]] | None):
    """
    Lightweight Hugging Face sentiment runner, intentionally Streamlit-free.
    """
    try:
        from transformers import pipeline  # type: ignore
    except Exception as e:
        raise RuntimeError(
            f"transformers is not installed; cannot run Hugging Face sentiment: {e}"
        )
    import re

    params = hf_classifier_params or {}
    model = params.get("model")
    task = params.get("task")
    if not model or not task:
        raise RuntimeError(
            "Invalid Hugging Face model registry entry: missing hf_classifier_params.model/task"
        )

    classifier = pipeline(task=task, model=model)
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text or "") if s.strip()]
    out = []
    for s in sentences:
        r = classifier(s)
        try:
            r[0]["sentence"] = s
        except Exception:
            pass
        out.append(r)
    return out


def _safe_parse_json_text(s: str) -> Dict[str, Any]:
    """
    Parse a model output that is supposed to be JSON. Be forgiving if it contains noise.
    """
    try:
        return json.loads(s)
    except Exception:
        pass
    import re

    m = re.search(r"\{.*\}", s, flags=re.DOTALL)
    if m:
        try:
            return json.loads(m.group(0))
        except Exception:
            pass
    return {}

# ------------------------------------------------------------------------------
#  -----------   Chat endpoint  -----------   -----------   -----------
# ------------------------------------------------------------------------------

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


@app.post("/api/chat", response_model=ChatResponse)
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


async def _analyze_with_model(
    text: str,
    model_id: str,
    engine: str,
    options: Optional[Dict[str, Any]] = None,
    raw: Optional[bool] = None,
    fmt: Optional[str] = None,
    hf_classifier_params: Optional[Dict[str, Any]] | None = None
) -> Dict[str, Any]:

    if engine == "hugging face":
        res = _hf_sentiment(text, hf_classifier_params)
        return {
            "engine": "hugging face",
            "labels and scores by sentence": res
        }
    from .ollama_client import generate_json_with_analysis
    prompt = (
        "Return ONLY a JSON object with these exact keys and types; no extra keys and no prose. "
        'label: one of ["positive","negative","neutral"]; confidence: number in [0,1]; '
        'scores: {"positive":number,"negative":number,"neutral":number}; translation: string|null; analysis: object|null. '
        f"Text: {text}"
    )

    # extract options safely
    np = int(options.get("num_predict", 1024)) if options else 1024
    temp = float(options.get("temperature", 0.0)) if options else 0.0
    top_p = float(options.get("top_p", 0.9)) if options else 0.9

    runtime_model = resolve_available_model_tag(model_id)
    parsed, raw_text = await generate_json_with_analysis(
        runtime_model,
        prompt,
        num_predict=np,
        temperature=temp,
        top_p=top_p,
        extra_options=options,
        timeout_s=75.0,
        retries=1,
        force_raw=raw,
        out_format=fmt or "json",
    )

    label = str(parsed.get("label") or "neutral").lower()
    if label not in {"positive", "negative", "neutral"}:
        label = "neutral"

    confidence = float(parsed.get("confidence") or 0.5)
    scores = parsed.get("scores") or {}
    scores = {
        "positive": float(scores.get("positive") or (1.0 if label == "positive" else 0.0)),
        "negative": float(scores.get("negative") or (1.0 if label == "negative" else 0.0)),
        "neutral": float(scores.get("neutral") or (1.0 if label == "neutral" else 0.0)),
    }

    translation = parsed.get("translation", None)
    if not translation:
        try:
            translation = await translate_en(runtime_model, text)
        except Exception:
            translation = None
    analysis = parsed.get("analysis", None)

    return {
        "engine": "ollama",
        "label": label,
        "confidence": confidence,
        "scores": scores,
        "raw_model_output": raw_text,
        "translation": translation,
        "analysis": analysis,
    }


async def _analyze_with_openrouter(
    text: str,
    *,
    openrouter_model: str,
    auth_header: str,
    options: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    endpoint = os.getenv(
        "OPENROUTER_API_URL", "https://openrouter.ai/api/v1/chat/completions"
    )
    prompt = (
        "Return ONLY a JSON object with these exact keys and types; no extra keys and no prose. "
        'label: one of ["positive","negative","neutral"]; confidence: number in [0,1]; '
        'scores: {"positive":number,"negative":number,"neutral":number}; translation: string|null; analysis: object|null. '
        f"Text: {text}"
    )

    # best-effort option mapping
    temp = float((options or {}).get("temperature", 0.0) or 0.0)
    top_p = float((options or {}).get("top_p", 0.9) or 0.9)
    max_tokens = int((options or {}).get("num_predict", 1024) or 1024)

    headers = {
        "Authorization": auth_header,
        "Content-Type": "application/json",
    }
    # Optional attribution headers; safe defaults for local dev.
    if os.getenv("OPENROUTER_REFERER"):
        headers["HTTP-Referer"] = os.getenv("OPENROUTER_REFERER", "")
    if os.getenv("OPENROUTER_TITLE"):
        headers["X-Title"] = os.getenv("OPENROUTER_TITLE", "")

    payload = {
        "model": openrouter_model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": temp,
        "top_p": top_p,
        "max_tokens": max_tokens,
    }

    async with httpx.AsyncClient(timeout=75.0) as client:
        try:
            rr = await client.post(endpoint, headers=headers, json=payload)
            rr.raise_for_status()
            data = rr.json()
        except httpx.HTTPStatusError as e:
            detail = ""
            try:
                j = e.response.json()
                detail = str(j.get("error") or j.get("message") or j)
            except Exception:
                detail = (e.response.text or "").strip()
            raise HTTPException(
                status_code=int(e.response.status_code),
                detail=detail or f"OpenRouter request failed: {e.response.status_code}",
            )

    raw_content = (
        (((data or {}).get("choices") or [{}])[0].get("message") or {}).get("content")
        or ""
    )
    parsed = _safe_parse_json_text(str(raw_content))

    label = str(parsed.get("label") or "neutral").lower()
    if label not in {"positive", "negative", "neutral"}:
        label = "neutral"

    confidence = parsed.get("confidence")
    try:
        confidence = float(confidence)
    except Exception:
        confidence = 0.5

    scores = parsed.get("scores") or {}
    try:
        scores = {
            "positive": float(scores.get("positive") or (1.0 if label == "positive" else 0.0)),
            "negative": float(scores.get("negative") or (1.0 if label == "negative" else 0.0)),
            "neutral": float(scores.get("neutral") or (1.0 if label == "neutral" else 0.0)),
        }
    except Exception:
        scores = {
            "positive": 0.0,
            "negative": 0.0,
            "neutral": 1.0,
        }

    return {
        "engine": "openrouter",
        "label": label,
        "confidence": confidence,
        "scores": scores,
        "raw_model_output": str(raw_content),
        "translation": parsed.get("translation", None),
        "analysis": parsed.get("analysis", None),
    }


@app.post("/api/analyze")
async def analyze(body: AnalyzeBody, request: Request):
    text = body.text
    try:
        provider = (body.provider or resolve_engine(body.model_id) or "builtin").lower()
        if provider in {"ollama", "hugging face"}:
            model_id = resolve_model(body.model_id)
            hf_classifier_params = resolve_hf_params(body.model_id)
            res = await _analyze_with_model(
                text,
                model_id,
                provider,
                options=body.options,
                raw=body.raw,
                fmt=body.format,
                hf_classifier_params=hf_classifier_params,
            )
            return JSONResponse(res)
        if provider == "openrouter":
            openrouter_model = (body.openrouter_model or "").strip()
            if not openrouter_model:
                raise HTTPException(
                    status_code=400, detail="openrouter_model is required for provider=openrouter"
                )
            auth_header = request.headers.get("authorization") or ""
            if not auth_header.lower().startswith("bearer "):
                raise HTTPException(
                    status_code=401,
                    detail="Missing Authorization: Bearer <OPENROUTER_API_KEY>",
                )
            res = await _analyze_with_openrouter(
                text,
                openrouter_model=openrouter_model,
                auth_header=auth_header,
                options=body.options,
            )
            return JSONResponse(res)
        return JSONResponse(
            {
                "engine": "builtin",
                "label": "neutral",
                "confidence": 0.5,
                "scores": {"positive": 0.25, "negative": 0.25, "neutral": 0.5},
                "raw_model_output": "",
                "translation": None,
                "analysis": None,
            }
        )
    except HTTPException:
        raise
    except (httpx.ReadTimeout, httpx.ConnectTimeout):
        raise HTTPException(status_code=504, detail="Model backend timeout")
    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail=f"Model backend error: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unhandled error: {e}")


@app.post("/api/analyze/upload")
async def analyze_upload(
    file: UploadFile = File(...),
    engine: str = Form("model"),
    model_id: Optional[str] = Form(None),
    options: Optional[str] = Form(None),
    raw: Optional[str] = Form(None),
    format: Optional[str] = Form(None),
):
    try:
        text_bytes = await file.read()
        text = text_bytes.decode(errors="ignore")
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid file")
    opts = None
    try:
        if options:
            opts = json.loads(options)
    except Exception:
        opts = None
    force_raw = (raw or "").lower() == "true" if raw is not None else None
    fmt = format if format in ("json", "text") else None
    chosen_engine = (engine or "model").lower()
    try:
        if chosen_engine == "model":
            mid = resolve_model(model_id)
            res = await _analyze_with_model(
                text, mid, chosen_engine, options=opts, raw=force_raw, fmt=fmt
            )
            res["text"] = text
            return JSONResponse(res)
        return JSONResponse({"engine": "builtin", "label": "neutral", "confidence": 0.5, "scores": {"positive": 0.25, "negative": 0.25, "neutral": 0.5}, "raw_model_output": "", "translation": None, "analysis": None, "text": text})
    except HTTPException:
        raise
    except (httpx.ReadTimeout, httpx.ConnectTimeout):
        raise HTTPException(status_code=504, detail="Model backend timeout")
    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail=f"Model backend error: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unhandled error: {e}")


# ------------------------------------------------------------------------------
# -----------   Health Endpoint  -----------   -----------   -----------
# ------------------------------------------------------------------------------


@app.get("/api/health")
def api_health():
    return {"ok": True, "service": "trojan-parse-api"}

@app.get("/api/model_registry")
def api_model_registry():
    registry = get_registry()
    return registry.available_models()
