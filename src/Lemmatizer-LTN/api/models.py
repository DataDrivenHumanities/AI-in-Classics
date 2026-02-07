"""
Pydantic response models for the Latin Lemmatizer API.
"""

from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel


class LemmaResponse(BaseModel):
    """A single lemma entry."""

    id: int
    lemma_code: Optional[str] = None
    lemma_nod: str
    lemma_diac: Optional[str] = None
    pos: Optional[str] = None
    gender: Optional[str] = None
    page_url: Optional[str] = None
    created_at: Optional[datetime] = None


class FormResponse(BaseModel):
    """A single inflected form entry."""

    id: int
    lemma_id: int
    form_nod: str
    form_diac: Optional[str] = None
    mood: Optional[str] = None
    tense: Optional[str] = None
    voice: Optional[str] = None
    person: Optional[str] = None
    number: Optional[str] = None
    gender: Optional[str] = None
    case: Optional[str] = None
    degree: Optional[str] = None
    verb_form: Optional[str] = None
    page_url: Optional[str] = None


class FormsQueryParams(BaseModel):
    """Validated query parameters for the /forms endpoint."""

    lemma: Optional[str] = None
    form: Optional[str] = None
    mood: Optional[str] = None
    tense: Optional[str] = None
    voice: Optional[str] = None
    person: Optional[str] = None
    number: Optional[str] = None
    gender: Optional[str] = None
    case: Optional[str] = None
    degree: Optional[str] = None
    verb_form: Optional[str] = None


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    database: str
