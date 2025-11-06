from __future__ import annotations
import os
import json
import uuid
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional
from datetime import datetime


router = APIRouter(prefix="/api", tags=["feedback"])

FEEDBACK_DIR = os.path.join(os.getcwd(), "data", "feedback")
TRAIN_DIR = os.path.join(os.getcwd(), "data", "train_jobs")
os.makedirs(FEEDBACK_DIR, exist_ok=True)
os.makedirs(TRAIN_DIR, exist_ok=True)


class FeedbackItem(BaseModel):
    model_id: str = Field(..., description="Model the user ran (e.g., latin_model:1.0.0)")
    text: str = Field(..., description="Original input text")
    got: Dict[str, Any] = Field(..., description="What the model returned (engine/label/confidence/scores/translation/analysis)")
    want: Dict[str, Any] = Field(..., description="What the user wants instead (corrected label/translation/analysis/etc.)")
    notes: Optional[str] = Field(None, description="Free-form user notes")
    tags: Optional[List[str]] = Field(default_factory=list)


class TrainRequest(BaseModel):
    model_id: str
    preset_name: Optional[str] = None
    # Optional filters to select a subset of feedback examples
    tags: Optional[List[str]] = None
    limit: Optional[int] = None


@router.post("/feedback")
async def submit_feedback(item: FeedbackItem) -> Dict[str, Any]:
    day = datetime.utcnow().strftime("%Y-%m-%d")
    path = os.path.join(FEEDBACK_DIR, f"{day}.jsonl")
    record = {
        "id": str(uuid.uuid4()),
        "ts": datetime.utcnow().isoformat() + "Z",
        **item.model_dump(),
    }
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
    return {"ok": True, "id": record["id"]}


@router.post("/train")
async def trigger_train(req: TrainRequest) -> Dict[str, Any]:
    job_id = str(uuid.uuid4())
    job = {
        "id": job_id,
        "ts": datetime.utcnow().isoformat() + "Z",
        "model_id": req.model_id,
        "preset_name": req.preset_name,
        "filters": {"tags": req.tags or [], "limit": req.limit},
        "status": "queued",
        "notes": "Attach your fine-tune script here (LoRA/RAG rebuild/prompt refresh).",
    }
    with open(os.path.join(TRAIN_DIR, f"{job_id}.json"), "w", encoding="utf-8") as f:
        json.dump(job, f, ensure_ascii=False, indent=2)
    return {"ok": True, "job_id": job_id, "status": "queued"}
