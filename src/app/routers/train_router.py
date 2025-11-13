from __future__ import annotations
import os
import json
import uuid
import glob
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional
from datetime import datetime


router = APIRouter(prefix="/api", tags=["train"])

BASE_DIR = os.getcwd()
FEEDBACK_DIR = os.path.join(BASE_DIR, "data", "feedback")
TRAIN_DIR = os.path.join(BASE_DIR, "data", "train_jobs")
os.makedirs(FEEDBACK_DIR, exist_ok=True)
os.makedirs(TRAIN_DIR, exist_ok=True)


class TrainRequest(BaseModel):
    model_id: str = Field(..., description="Target model to train (e.g. latin_model:1.0.0)")
    preset_name: Optional[str] = None
    strategy: Optional[str] = Field(default="rag_refresh", description="rag_refresh|lora|prompt_update")
    tags: Optional[List[str]] = None
    limit: Optional[int] = None


class TrainJob(BaseModel):
    id: str
    ts: str
    model_id: str
    preset_name: Optional[str]
    strategy: str
    filters: Dict[str, Any]
    status: str
    stats: Dict[str, Any]


def _load_feedback_records(tags: Optional[List[str]], limit: Optional[int]) -> List[Dict[str, Any]]:
    paths = sorted(glob.glob(os.path.join(FEEDBACK_DIR, "*.jsonl")))
    rows: List[Dict[str, Any]] = []
    for p in paths:
        with open(p, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except Exception:
                    continue
                if tags:
                    rt = set(map(str.lower, rec.get("tags") or []))
                    need = set(map(str.lower, tags))
                    if rt.isdisjoint(need):
                        continue
                rows.append(rec)
                if limit and len(rows) >= limit:
                    return rows
    return rows


def _save_job(job: TrainJob) -> None:
    path = os.path.join(TRAIN_DIR, f"{job.id}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(job.model_dump(), f, ensure_ascii=False, indent=2)


def _read_job(job_id: str) -> Optional[Dict[str, Any]]:
    path = os.path.join(TRAIN_DIR, f"{job_id}.json")
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


@router.post("/train")
async def trigger_train(req: TrainRequest) -> Dict[str, Any]:
    rows = _load_feedback_records(req.tags, req.limit)
    job_id = str(uuid.uuid4())
    job = TrainJob(
        id=job_id,
        ts=datetime.utcnow().isoformat() + "Z",
        model_id=req.model_id,
        preset_name=req.preset_name,
        strategy=req.strategy or "rag_refresh",
        filters={"tags": req.tags or [], "limit": req.limit},
        status="queued",
        stats={"feedback_count": len(rows)},
    )
    _save_job(job)
    dataset_path = os.path.join(TRAIN_DIR, f"{job_id}.jsonl")
    with open(dataset_path, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    return {"ok": True, "job_id": job_id, "status": "queued", "feedback_count": len(rows)}


@router.get("/train")
async def list_train_jobs() -> Dict[str, Any]:
    paths = sorted(glob.glob(os.path.join(TRAIN_DIR, "*.json")))
    out: List[Dict[str, Any]] = []
    for p in paths:
        try:
            with open(p, "r", encoding="utf-8") as f:
                out.append(json.load(f))
        except Exception:
            continue
    return {"jobs": out}


@router.get("/train/{job_id}")
async def get_train_job(job_id: str) -> Dict[str, Any]:
    job = _read_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="job not found")
    return job
