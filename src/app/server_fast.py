from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
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

from src.app.app_functions import hf_sentiment
from src.app.model_registry import get_registry, available_model_ids

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

DEFAULT_OLLAMA_MODEL = os.getenv("DEFAULT_OLLAMA_MODEL", "llama3.1")
chat_router = make_chat_router(DEFAULT_OLLAMA_MODEL)
sent_router = make_default_sentiment_router()


class AnalyzeBody(BaseModel):
    text: str
    model_id: Optional[str] = None
    options: Optional[Dict[str, Any]] = None
    raw: Optional[bool] = None
    format: Optional[str] = None


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
    return "latin_model:1.0.0"

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
        res = hf_sentiment(text, hf_classifier_params)
        print(res)
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

    parsed, raw_text = await generate_json_with_analysis(
        model_id,
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


@app.post("/api/analyze")
async def analyze(body: AnalyzeBody):
    text = body.text
    try:
        engine = (resolve_engine(body.model_id) or "builtin").lower()
        print(engine)
        if engine == "ollama" or engine == "hugging face":
            model_id = resolve_model(body.model_id)
            hf_classifier_params = resolve_hf_params(body.model_id)
            print(model_id, hf_classifier_params)
            res = await _analyze_with_model(text, model_id, engine, options=body.options, raw=body.raw, fmt=body.format, hf_classifier_params=hf_classifier_params)
            return JSONResponse(res)
        return JSONResponse({"engine": "builtin", "label": "neutral", "confidence": 0.5, "scores": {"positive": 0.25, "negative": 0.25, "neutral": 0.5}, "raw_model_output": "", "translation": None, "analysis": None})
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
    try:
        if (engine or "model").lower() == "model":
            mid = resolve_model(model_id)
            res = await _analyze_with_model(text, mid, options=opts, raw=force_raw, fmt=fmt)
            res["text"] = text
            return JSONResponse(res)
        return JSONResponse({"engine": "builtin", "label": "neutral", "confidence": 0.5, "scores": {"positive": 0.25, "negative": 0.25, "neutral": 0.5}, "raw_model_output": "", "translation": None, "analysis": None, "text": text})
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
