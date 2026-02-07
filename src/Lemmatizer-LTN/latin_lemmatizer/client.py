"""
Client for querying the Latin Lemmatizer API.

This package is a thin HTTP wrapper around the Latin Lemmatizer FastAPI
server.  It preserves the same public interface as the original direct-SQL
client so existing code continues to work — only the configuration changes:

    Before:  DATABASE_URL=postgresql://...
    After:   LATIN_API_URL=https://latin-api.example.com
             LATIN_API_TOKEN=<bearer-token>
"""

import os
from pathlib import Path
from typing import Optional, List, Dict, Any

import httpx

try:
    from dotenv import load_dotenv

    # Try to load .env file from current working directory or project root
    # This allows users to place .env in the project root or notebook directory
    cwd = Path(os.getcwd())
    # Try current directory first, then project root (4 levels up from this file)
    for env_path in [cwd / ".env", Path(__file__).parent.parent.parent.parent / ".env"]:
        if env_path.exists():
            load_dotenv(env_path)
            break
except ImportError:
    # python-dotenv not installed, skip .env loading
    pass


class LatinLemmatizer:
    """Client for querying Latin lemmas and forms via the Lemmatizer API."""

    def __init__(
        self,
        api_url: Optional[str] = None,
        api_token: Optional[str] = None,
        timeout: float = 30.0,
    ):
        """
        Initialize the Latin Lemmatizer client.

        Args:
            api_url: Base URL of the Lemmatizer API (e.g. "https://latin-api.example.com").
                     Falls back to the LATIN_API_URL environment variable.
            api_token: Bearer token for authentication.
                       Falls back to the LATIN_API_TOKEN environment variable.
            timeout: HTTP request timeout in seconds (default 30).
        """
        self.api_url = (api_url or os.getenv("LATIN_API_URL", "")).rstrip("/")
        self.api_token = api_token or os.getenv("LATIN_API_TOKEN", "")

        if not self.api_url:
            raise ValueError(
                "No API URL provided. Set LATIN_API_URL or pass api_url parameter."
            )
        if not self.api_token:
            raise ValueError(
                "No API token provided. Set LATIN_API_TOKEN or pass api_token parameter."
            )

        self._client = httpx.Client(
            base_url=self.api_url,
            headers={"Authorization": f"Bearer {self.api_token}"},
            timeout=timeout,
        )

    # ------------------------------------------------------------------
    # Lifecycle helpers
    # ------------------------------------------------------------------

    def close(self):
        """Close the underlying HTTP client."""
        self._client.close()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()

    # ------------------------------------------------------------------
    # Public query methods
    # ------------------------------------------------------------------

    def get_lemma(self, word: str) -> Optional[Dict[str, Any]]:
        """
        Get lemma information from a word (lemma or inflected form).

        If the word is already a lemma, returns that lemma.
        If the word is an inflected form, returns its lemma.

        Args:
            word: A Latin word (lemma or inflected form)

        Returns:
            Dictionary with lemma information (id, lemma_code, lemma_nod,
            lemma_diac, pos, gender, page_url) or None if not found.

        Example:
            >>> client.get_lemma("amavi")
            {'id': 123, 'lemma_nod': 'amo', 'lemma_diac': 'ămo', 'pos': 'verb', ...}
        """
        resp = self._client.get(f"/api/v1/lemma/{word}")

        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        return resp.json()

    def get_form(
        self,
        *,
        lemma: Optional[str] = None,
        form: Optional[str] = None,
        mood: Optional[str] = None,
        tense: Optional[str] = None,
        voice: Optional[str] = None,
        person: Optional[str] = None,
        number: Optional[str] = None,
        gender: Optional[str] = None,
        case: Optional[str] = None,
        degree: Optional[str] = None,
        verb_form: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get inflected forms matching the specified criteria.

        You must provide either ``lemma`` or ``form``, but not both.

        Args:
            lemma: Starting lemma (finds forms of this lemma)
            form: Starting form (finds other forms of the same lemma)
            mood: Filter by mood (indicative, subjunctive, imperative)
            tense: Filter by tense (present, imperfect, future, perfect, pluperfect, future perfect)
            voice: Filter by voice (active, passive, deponent)
            person: Filter by person (first, second, third)
            number: Filter by number (singular, plural)
            gender: Filter by gender (masculine, feminine, neuter)
            case: Filter by case (nominative, genitive, dative, accusative, ablative, vocative, locative)
            degree: Filter by degree (positive, comparative, superlative)
            verb_form: Filter by verb form (infinitive, participle, gerund, gerundive, supine)

        Returns:
            List of dictionaries with form information.

        Examples:
            >>> # Get all perfect active forms of "amo"
            >>> client.get_form(lemma="amo", tense="perfect", voice="active")

            >>> # Get plural forms of the same lemma as "amavi"
            >>> client.get_form(form="amavi", number="plural")

            >>> # Get the infinitive form of "amo"
            >>> client.get_form(lemma="amo", verb_form="infinitive")
        """
        if (lemma is None and form is None) or (lemma is not None and form is not None):
            raise ValueError("Must provide exactly one of: lemma or form")

        params: Dict[str, str] = {}
        if lemma is not None:
            params["lemma"] = lemma
        if form is not None:
            params["form"] = form
        if mood is not None:
            params["mood"] = mood
        if tense is not None:
            params["tense"] = tense
        if voice is not None:
            params["voice"] = voice
        if person is not None:
            params["person"] = person
        if number is not None:
            params["number"] = number
        if gender is not None:
            params["gender"] = gender
        if case is not None:
            params["case"] = case
        if degree is not None:
            params["degree"] = degree
        if verb_form is not None:
            params["verb_form"] = verb_form

        resp = self._client.get("/api/v1/forms", params=params)
        resp.raise_for_status()
        return resp.json()


# ======================================================================
# Convenience singleton + module-level functions
# ======================================================================

_default_client: Optional[LatinLemmatizer] = None


def _get_default_client() -> LatinLemmatizer:
    """Get or create the default client instance."""
    global _default_client
    if _default_client is None:
        _default_client = LatinLemmatizer()
    return _default_client


def get_lemma(word: str) -> Optional[Dict[str, Any]]:
    """
    Get lemma information from a word (convenience function using default client).

    Args:
        word: A Latin word (lemma or inflected form)

    Returns:
        Dictionary with lemma information or None if not found.
    """
    return _get_default_client().get_lemma(word)


def get_form(
    *,
    lemma: Optional[str] = None,
    form: Optional[str] = None,
    mood: Optional[str] = None,
    tense: Optional[str] = None,
    voice: Optional[str] = None,
    person: Optional[str] = None,
    number: Optional[str] = None,
    gender: Optional[str] = None,
    case: Optional[str] = None,
    degree: Optional[str] = None,
    verb_form: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Get inflected forms (convenience function using default client).

    Args:
        lemma: Starting lemma
        form: Starting form
        (plus optional filters for mood, tense, voice, etc.)

    Returns:
        List of dictionaries with form information.
    """
    return _get_default_client().get_form(
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
