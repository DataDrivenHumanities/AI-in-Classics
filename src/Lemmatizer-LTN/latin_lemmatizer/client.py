"""
Client for querying the Latin Lemmatizer API.

This package is a thin HTTP wrapper around the Latin Lemmatizer FastAPI
server.

Configuration (environment variables or constructor args):
    LATIN_API_URL   — Base URL of the API (e.g. https://latin-api.example.com)
    LATIN_API_TOKEN — Bearer token for authentication
"""

import os
from pathlib import Path
from typing import Optional, List, Dict, Any, Union

import httpx

try:
    from dotenv import load_dotenv

    cwd = Path(os.getcwd())
    for env_path in [cwd / ".env", Path(__file__).parent.parent.parent.parent / ".env"]:
        if env_path.exists():
            load_dotenv(env_path)
            break
except ImportError:
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
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    # ------------------------------------------------------------------
    # Public query methods
    # ------------------------------------------------------------------

    def get_lemmas(
        self,
        word: str,
        pos: Optional[str] = None,
        top: bool = False,
    ) -> Union[List[Dict[str, Any]], Optional[Dict[str, Any]]]:
        """
        Look up lemmas matching a Latin word, ranked by relevance.

        Args:
            word: A Latin word (lemma or inflected form).
            pos: Optional part-of-speech filter (e.g. "noun", "verb").
                 Matches as a substring so "noun" matches
                 "feminine noun I declension".
            top: If True, return only the single best match (Dict) or
                 None.  If False (default), return all matches as a
                 list ranked by relevance.

        Returns:
            If top=False: List of lemma dicts, best match first.
            If top=True:  Single best-match dict, or None.

        Examples:
            >>> client.get_lemmas("rosam")
            [{'lemma_nod': 'rosa', ...}, {'lemma_nod': 'rodo', ...}]

            >>> client.get_lemmas("rosam", top=True)
            {'lemma_nod': 'rosa', ...}

            >>> client.get_lemmas("rosam", pos="noun")
            [{'lemma_nod': 'rosa', ...}]
        """
        params: Dict[str, str] = {}
        if pos is not None:
            params["pos"] = pos

        resp = self._client.get(f"/api/v1/lemma/{word}", params=params)

        if resp.status_code == 404:
            return None if top else []
        resp.raise_for_status()
        results = resp.json()

        if top:
            return results[0] if results else None
        return results

    def get_forms(
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
            tense: Filter by tense (present, imperfect, future, perfect,
                   pluperfect, future perfect)
            voice: Filter by voice (active, passive)
            person: Filter by person (first, second, third)
            number: Filter by number (singular, plural)
            gender: Filter by gender (masculine, feminine, neuter)
            case: Filter by case (nominative, genitive, dative, accusative,
                  ablative, vocative, locative)
            degree: Filter by degree (positive, comparative, superlative)
            verb_form: Filter by verb form (infinitive, participle, gerund,
                       gerundive, supine)

        Returns:
            List of dictionaries with form information.

        Examples:
            >>> client.get_forms(lemma="amo", tense="perfect", voice="active")
            >>> client.get_forms(form="amavi", number="plural")
            >>> client.get_forms(lemma="amo", verb_form="infinitive")
        """
        if (lemma is None and form is None) or (lemma is not None and form is not None):
            raise ValueError("Must provide exactly one of: lemma or form")

        params: Dict[str, str] = {}
        if lemma is not None:
            params["lemma"] = lemma
        if form is not None:
            params["form"] = form
        for key, val in [
            ("mood", mood), ("tense", tense), ("voice", voice),
            ("person", person), ("number", number), ("gender", gender),
            ("case", case), ("degree", degree), ("verb_form", verb_form),
        ]:
            if val is not None:
                params[key] = val

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


def get_lemmas(
    word: str,
    pos: Optional[str] = None,
    top: bool = False,
) -> Union[List[Dict[str, Any]], Optional[Dict[str, Any]]]:
    """
    Look up lemmas matching a Latin word (convenience function).

    Args:
        word: A Latin word (lemma or inflected form).
        pos: Optional part-of-speech filter (e.g. "noun", "verb").
        top: If True, return single best match or None.
             If False (default), return ranked list.

    Returns:
        List of lemma dicts (top=False) or single dict/None (top=True).
    """
    return _get_default_client().get_lemmas(word, pos=pos, top=top)


def get_forms(
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
    Get inflected forms (convenience function).

    Must provide exactly one of ``lemma`` or ``form``.
    """
    return _get_default_client().get_forms(
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
