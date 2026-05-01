"""
API route handlers for the Latin Lemmatizer.

Endpoints:
    GET  /api/v1/health            — health check (no auth)
    GET  /api/v1/lemma/{word}      — look up a lemma
    GET  /api/v1/forms             — query inflected forms (requires lemma or form)
    GET  /api/v1/forms/random      — N random forms by morph filters (no lemma needed)
    GET  /api/v1/random-lemmas     — random lemmas (optionally by POS)
    POST /api/v1/forms/batch       — resolve many form queries at once
"""

from typing import List, Optional, Literal

from fastapi import APIRouter, Depends, HTTPException, Query

from .auth import verify_token
from .db import get_lemmas as db_get_lemmas
from .db import get_forms as db_get_forms
from .db import random_forms as db_random_forms
from .db import random_lemmas as db_random_lemmas
from .db import batch_forms as db_batch_forms
from .db import health_check as db_health_check
from .models import (
    BatchFormQuery,
    BatchFormsRequest,
    BatchFormsResponseItem,
    FormResponse,
    HealthResponse,
    LemmaResponse,
    RandomFormResponse,
)

router = APIRouter(prefix="/api/v1")


# ------------------------------------------------------------------
# Health
# ------------------------------------------------------------------

@router.get("/health", response_model=HealthResponse)
async def health():
    """Public health check (no auth required)."""
    db_ok = db_health_check()
    return HealthResponse(
        status="ok" if db_ok else "degraded",
        database="connected" if db_ok else "unreachable",
    )


# ------------------------------------------------------------------
# Lemma lookup
# ------------------------------------------------------------------

@router.get("/lemma/{word}", response_model=List[LemmaResponse])
async def get_lemma(
    word: str,
    pos: Optional[str] = Query(None, description="Filter by part of speech (e.g. 'noun', 'verb')"),
    _token: str = Depends(verify_token),
):
    """
    Look up lemmas matching any Latin word (lemma or inflected form).

    Returns all matching lemmas ranked by relevance. Optionally filter
    by part of speech with the ``pos`` parameter.
    """
    return db_get_lemmas(word, pos=pos)


# ------------------------------------------------------------------
# Forms query
# ------------------------------------------------------------------

@router.get("/forms", response_model=List[FormResponse])
async def get_forms(
    lemma: Optional[str] = Query(None, description="Starting lemma (e.g. 'amo')"),
    form: Optional[str] = Query(None, description="Starting inflected form (e.g. 'amavi')"),
    mood: Optional[str] = Query(None),
    tense: Optional[str] = Query(None),
    voice: Optional[str] = Query(None),
    person: Optional[str] = Query(None),
    number: Optional[str] = Query(None),
    gender: Optional[str] = Query(None),
    case: Optional[str] = Query(None),
    degree: Optional[str] = Query(None),
    verb_form: Optional[str] = Query(None),
    _token: str = Depends(verify_token),
):
    """
    Query inflected forms with optional morphological filters.

    Exactly one of `lemma` or `form` must be provided.
    """
    # Validate mutual exclusivity
    if (lemma is None) == (form is None):
        raise HTTPException(
            status_code=422,
            detail="Provide exactly one of 'lemma' or 'form' (not both, not neither).",
        )

    results = db_get_forms(
        lemma=lemma,
        form=form,
        mood=mood,
        tense=tense,
        voice=voice,
        person=person,
        number=number,
        gender=gender,
        case=case,
        degree=degree,
        verb_form=verb_form,
    )
    return results


# ------------------------------------------------------------------
# Random forms (no lemma required)
# ------------------------------------------------------------------

@router.get("/forms/random", response_model=List[RandomFormResponse])
async def get_random_forms(
    n: int = Query(50, ge=1, le=500, description="Number of random forms"),
    pos: Optional[str] = Query(None, description="Filter parent lemma by POS (e.g. 'verb', 'noun')"),
    mood: Optional[str] = Query(None),
    tense: Optional[str] = Query(None),
    voice: Optional[str] = Query(None),
    person: Optional[str] = Query(None),
    number: Optional[str] = Query(None),
    gender: Optional[str] = Query(None),
    case: Optional[str] = Query(None),
    degree: Optional[str] = Query(None),
    verb_form: Optional[str] = Query(None),
    exclude_proper: bool = Query(True, description="Exclude likely proper-name lemmas"),
    allow_nonfinite: bool = Query(False, description="Allow participles/infinitives/gerunds/etc."),
    rarity_mode: Literal["common", "balanced", "all"] = Query("balanced"),
    _token: str = Depends(verify_token),
):
    """
    Return *n* random forms from the entire database, filtered by
    morphological features and optionally by parent-lemma POS.

    No lemma or form input needed — useful for generating random
    sentences or sampling training data.
    """
    try:
        return db_random_forms(
            n=n,
            pos=pos,
            mood=mood,
            tense=tense,
            voice=voice,
            person=person,
            number=number,
            gender=gender,
            case=case,
            degree=degree,
            verb_form=verb_form,
            exclude_proper=exclude_proper,
            allow_nonfinite=allow_nonfinite,
            rarity_mode=rarity_mode,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


# ------------------------------------------------------------------
# Random lemmas
# ------------------------------------------------------------------

@router.get("/random-lemmas", response_model=List[LemmaResponse])
async def get_random_lemmas(
    n: int = Query(10, ge=1, le=500, description="Number of random lemmas to return"),
    pos: Optional[str] = Query(None, description="Filter by POS substring (e.g. 'verb', 'noun')"),
    _token: str = Depends(verify_token),
):
    """Return *n* random lemmas from the database, optionally filtered by POS."""
    return db_random_lemmas(n=n, pos=pos)


# ------------------------------------------------------------------
# Batch forms
# ------------------------------------------------------------------

@router.post("/forms/batch", response_model=List[BatchFormsResponseItem])
async def post_forms_batch(
    body: BatchFormsRequest,
    _token: str = Depends(verify_token),
):
    """
    Resolve multiple form queries in a single request.

    Accepts a JSON body with a ``queries`` array. Each query has a
    ``lemma`` field and optional morphological filters. Returns one
    result set per query, in the same order.
    """
    if len(body.queries) > 500:
        raise HTTPException(status_code=422, detail="Maximum 500 queries per batch.")
    raw = db_batch_forms([q.model_dump() for q in body.queries])
    return [BatchFormsResponseItem(forms=forms) for forms in raw]
