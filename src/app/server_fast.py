# src/app/server_fast.py
from __future__ import annotations

import os
import pathlib
import sys
from typing import Dict, Iterable, List, Literal, Optional, Any

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field


from app.routers.chat_router import make_default_router as make_chat_router  # type: ignore
from app.routers.chat_router import Message as ChatMessage  # type: ignore
from app.routers.sentiment_router import (  # type: ignore
    make_default_sentiment_router,
    SentimentResult,
)

app = FastAPI(
    title="Trojan Parse FastAPI Server",
    version="1.0.0",
    description="Unified chat and sentiment analysis endpoints",
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ALLOW_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Singletons
DEFAULT_OLLAMA_MODEL = os.getenv("DEFAULT_OLLAMA_MODEL", "llama3.1")
chat_router = make_chat_router(DEFAULT_OLLAMA_MODEL)
sent_router = make_default_sentiment_router()


Role = Literal["system", "user", "assistant"]

# ------------------------------------------------------------------------------
#  -----------   Route Debug Enable this if you need to   -----------
# ------------------------------------------------------------------------------


# @app.on_event("startup")
# async def _debug_list_routes():
#     print("=== ROUTES ===")
#     for r in app.router.routes:
#         methods = getattr(r, "methods", None) or []
#         print(
#             f"{sorted(methods)}  {getattr(r, 'path', getattr(r, 'path_format', '<?>'))}"
#         )
#     print("==============")
# ------------------------------------------------------------------------------


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

        # Non-streaming
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
        # Unknown pmodel binding
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"chat error: {e}")


# ------------------------------------------------------------------------------
#  -----------  Sentiment endpoints  -----------   -----------   -----------
# ------------------------------------------------------------------------------


@app.post("/api/analyze")
def analyze(req: AnalyzeRequest):
    try:
        if not req.text or not req.text.strip():
            raise HTTPException(status_code=400, detail="text must be non-empty")

        res: SentimentResult = sent_router.analyze(
            req.text, engine=req.engine, model_id=req.model_id
        )
        return JSONResponse(res)
    except HTTPException:
        raise
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"analyze error: {e}")


@app.post("/api/analyze/upload")
async def analyze_upload(
    file: UploadFile = File(...),
    engine: str = Form("builtin"),
    model_id: Optional[str] = Form(None),
):
    try:
        data = await file.read()
        text = data.decode("utf-8", errors="ignore")
        if not text.strip():
            raise HTTPException(
                status_code=400, detail="Uploaded file contains no readable text."
            )

        res: SentimentResult = sent_router.analyze(
            text, engine=engine, model_id=model_id
        )
        return JSONResponse(res)
    except HTTPException:
        raise
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"analyze_upload error: {e}")
