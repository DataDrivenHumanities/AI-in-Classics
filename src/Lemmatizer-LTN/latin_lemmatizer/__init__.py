"""
Latin Lemmatizer - A package for querying Latin lemmas and inflected forms.

This package provides an interface to query a PostgreSQL database containing
Latin lemmas and their inflected forms.
"""

from .client import LatinLemmatizer, get_form, get_lemma

__all__ = ["LatinLemmatizer", "get_form", "get_lemma"]
__version__ = "0.1.0"

