from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from ..latin_lexicon import make_latin_lexicon_annotator, resolve_database_url
from ..text_extract import extract_text_from_upload


PROJECT_ROOT = Path(__file__).resolve().parents[3]
SAMPLE_DIR = PROJECT_ROOT / "src" / "sample_text" / "latin"

router = APIRouter()


class LexiconAnnotateBody(BaseModel):
    text: str = Field(..., description="Latin text to annotate")
    max_chars: int = Field(12000, ge=200, le=200000)


@router.post("/text/extract")
async def text_extract(file: UploadFile = File(...)):
    try:
        data = await file.read()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid file")

    text, warnings = extract_text_from_upload(file.filename or "", data or b"")
    return JSONResponse(
        {"text": text or "", "filename": file.filename or "", "warnings": warnings}
    )


@router.get("/samples/latin")
def list_latin_samples():
    if not SAMPLE_DIR.exists():
        return JSONResponse({"samples": []})
    out: List[Dict[str, Any]] = []
    for p in sorted(SAMPLE_DIR.glob("*.txt")):
        try:
            out.append({"id": p.name, "name": p.stem, "bytes": int(p.stat().st_size)})
        except Exception:
            # Skip unreadable entries
            continue
    return JSONResponse({"samples": out})


@router.get("/samples/latin/{sample_id}")
def get_latin_sample(sample_id: str):
    if not SAMPLE_DIR.exists():
        raise HTTPException(status_code=404, detail="No samples directory configured")

    # Allowlist: only serve filenames present in the directory listing.
    allow = {p.name: p for p in SAMPLE_DIR.glob("*.txt")}
    p = allow.get(sample_id)
    if p is None:
        raise HTTPException(status_code=404, detail="Sample not found")

    try:
        text = p.read_text(encoding="utf-8")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read sample: {e}")

    return JSONResponse({"id": p.name, "name": p.stem, "text": text})


@router.post("/latin/lexicon/annotate")
def latin_lexicon_annotate(body: LexiconAnnotateBody):
    dsn = resolve_database_url()
    if not dsn:
        raise HTTPException(
            status_code=400,
            detail="Set DATABASE_URL to enable lexicon lookup + highlighting.",
        )

    text = (body.text or "").strip()
    if not text:
        return JSONResponse(
            {"truncated": False, "coverage": {}, "spans": [], "lemma_details": {}}
        )

    max_chars = int(body.max_chars or 12000)
    truncated = False
    clip = text
    if len(clip) > max_chars:
        clip = clip[:max_chars]
        truncated = True

    try:
        ann = make_latin_lexicon_annotator(dsn)
        res = ann.annotate_spans(clip)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lexicon annotate failed: {e}")

    return JSONResponse(
        {
            "truncated": truncated,
            "coverage": res.get("coverage") or {},
            "spans": res.get("spans") or [],
            "lemma_details": res.get("lemma_details") or {},
        }
    )

