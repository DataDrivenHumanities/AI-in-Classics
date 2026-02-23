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
    lemma_diathesis: Optional[str] = None
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


class RandomFormResponse(BaseModel):
    """A form with its parent lemma info, for random-forms endpoint."""

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
    lemma_nod: Optional[str] = None
    lemma_diac: Optional[str] = None
    lemma_code: Optional[str] = None
    lemma_diathesis: Optional[str] = None
    pos: Optional[str] = None


class RandomFormsQueryParams(BaseModel):
    """Validated query parameters for the /forms/random endpoint."""

    n: int = 50
    pos: Optional[str] = None
    mood: Optional[str] = None
    tense: Optional[str] = None
    voice: Optional[str] = None
    person: Optional[str] = None
    number: Optional[str] = None
    gender: Optional[str] = None
    case: Optional[str] = None
    degree: Optional[str] = None
    verb_form: Optional[str] = None
    exclude_proper: bool = True
    allow_nonfinite: bool = False
    rarity_mode: str = "balanced"


class BatchFormQuery(BaseModel):
    """A single query within a batch forms request."""

    lemma: str
    mood: Optional[str] = None
    tense: Optional[str] = None
    voice: Optional[str] = None
    person: Optional[str] = None
    number: Optional[str] = None
    gender: Optional[str] = None
    case: Optional[str] = None
    degree: Optional[str] = None
    verb_form: Optional[str] = None


class BatchFormsRequest(BaseModel):
    """Request body for POST /forms/batch."""

    queries: List[BatchFormQuery]


class BatchFormsResponseItem(BaseModel):
    """One result set in the batch response."""

    forms: List[FormResponse]


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    database: str
