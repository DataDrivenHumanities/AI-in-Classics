"""
Latin Lemmatizer - A package for querying Latin lemmas and inflected forms.

This package provides a client for the Latin Lemmatizer API, which serves
Latin lemmas and their inflected forms from a PostgreSQL database behind
a FastAPI server.

Configuration (environment variables or constructor args):
    LATIN_API_URL   — Base URL of the API (e.g. https://latin-api.example.com)
    LATIN_API_TOKEN — Bearer token for authentication
"""

from .client import LatinLemmatizer, get_forms, get_lemmas

__all__ = ["LatinLemmatizer", "get_forms", "get_lemmas"]
__version__ = "0.1.0"

