"""
Client for querying the Latin lemmatizer database.
"""

import os
from typing import Optional, List, Dict, Any
import psycopg
from psycopg.rows import dict_row


class LatinLemmatizer:
    """Client for querying Latin lemmas and forms from PostgreSQL database."""
    
    def __init__(self, dsn: Optional[str] = None):
        """
        Initialize the Latin Lemmatizer client.
        
        Args:
            dsn: PostgreSQL connection string. If None, uses DATABASE_URL env var.
        """
        self.dsn = dsn or os.getenv("DATABASE_URL")
        if not self.dsn:
            raise ValueError("No database connection string provided. Set DATABASE_URL or pass dsn parameter.")
        self._conn = None
    
    def _get_conn(self):
        """Get or create database connection."""
        if self._conn is None or self._conn.closed:
            self._conn = psycopg.connect(self.dsn, row_factory=dict_row)
        return self._conn
    
    def close(self):
        """Close the database connection."""
        if self._conn and not self._conn.closed:
            self._conn.close()
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
    
    def get_lemma(self, word: str) -> Optional[Dict[str, Any]]:
        """
        Get lemma information from a word (lemma or inflected form).
        
        If the word is already a lemma, returns that lemma.
        If the word is an inflected form, returns its lemma.
        
        Args:
            word: A Latin word (lemma or inflected form)
            
        Returns:
            Dictionary with lemma information (id, lemma_code, lemma_nod, lemma_diac, pos, gender, page_url)
            or None if not found.
            
        Example:
            >>> client.get_lemma("amavi")
            {'id': 123, 'lemma_nod': 'amo', 'lemma_diac': 'ămo', 'pos': 'verb', ...}
        """
        conn = self._get_conn()
        
        # First, try as a lemma
        result = conn.execute(
            "SELECT * FROM lemmas WHERE lemma_nod = norm(%s)",
            (word,)
        ).fetchone()
        
        if result:
            return dict(result)
        
        # If not found as lemma, try as a form
        result = conn.execute(
            """
            SELECT l.* FROM forms f
            JOIN lemmas l ON l.id = f.lemma_id
            WHERE f.form_nod = norm(%s)
            LIMIT 1
            """,
            (word,)
        ).fetchone()
        
        return dict(result) if result else None
    
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
        
        You must provide either `lemma` or `form`, but not both.
        
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
            List of dictionaries with form information
            
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
        
        conn = self._get_conn()
        
        if lemma is not None:
            # Get forms by lemma
            query = """
                SELECT f.* FROM lemmas l
                JOIN forms f ON f.lemma_id = l.id
                WHERE l.lemma_nod = norm(%s)
                  AND (%s IS NULL OR f.mood = %s)
                  AND (%s IS NULL OR f.tense = %s)
                  AND (%s IS NULL OR f.voice = %s)
                  AND (%s IS NULL OR f.person = %s)
                  AND (%s IS NULL OR f.number = %s)
                  AND (%s IS NULL OR f.gender = %s)
                  AND (%s IS NULL OR f."case" = %s)
                  AND (%s IS NULL OR f.degree = %s)
                  AND (%s IS NULL OR f.verb_form = %s)
                ORDER BY f.mood, f.tense, f.voice, f.person, f.number, f.gender, f."case", f.degree, f.verb_form, f.form_nod
            """
            params = (
                lemma,
                mood, mood,
                tense, tense,
                voice, voice,
                person, person,
                number, number,
                gender, gender,
                case, case,
                degree, degree,
                verb_form, verb_form,
            )
        else:
            # Get forms by starting form (inflect within same lemma)
            query = """
                WITH base AS (
                    SELECT l.id AS lemma_id
                    FROM forms f JOIN lemmas l ON l.id = f.lemma_id
                    WHERE f.form_nod = norm(%s)
                    LIMIT 1
                )
                SELECT f.* FROM forms f, base b
                WHERE f.lemma_id = b.lemma_id
                  AND (%s IS NULL OR f.mood = %s)
                  AND (%s IS NULL OR f.tense = %s)
                  AND (%s IS NULL OR f.voice = %s)
                  AND (%s IS NULL OR f.person = %s)
                  AND (%s IS NULL OR f.number = %s)
                  AND (%s IS NULL OR f.gender = %s)
                  AND (%s IS NULL OR f."case" = %s)
                  AND (%s IS NULL OR f.degree = %s)
                  AND (%s IS NULL OR f.verb_form = %s)
                ORDER BY f.mood, f.tense, f.voice, f.person, f.number, f.gender, f."case", f.degree, f.verb_form, f.form_nod
            """
            params = (
                form,
                mood, mood,
                tense, tense,
                voice, voice,
                person, person,
                number, number,
                gender, gender,
                case, case,
                degree, degree,
                verb_form, verb_form,
            )
        
        results = conn.execute(query, params).fetchall()
        return [dict(row) for row in results]


# Convenience singleton instance
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
        List of dictionaries with form information
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

