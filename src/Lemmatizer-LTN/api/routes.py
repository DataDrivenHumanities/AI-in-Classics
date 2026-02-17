"""
API route handlers for the Latin Lemmatizer.

Endpoints:
    GET /api/v1/health        — health check (no auth)
    GET /api/v1/lemma/{word}  — look up a lemma
    GET /api/v1/forms         — query inflected forms
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from .auth import verify_token
from .db import get_lemmas as db_get_lemmas
from .db import get_forms as db_get_forms
from .db import health_check as db_health_check
from .models import FormResponse, HealthResponse, LemmaResponse

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
