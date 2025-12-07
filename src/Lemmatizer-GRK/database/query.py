"""
Dictionary Query API

High-level Python API for querying Greek dictionary data from PostgreSQL.
Provides convenient methods for common lookup operations.
"""

from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy import or_, and_, func
from sqlalchemy.orm import Session
from sqlalchemy.engine import Engine

from .config import get_engine, get_session
from .models import (
    GreekWord, GreekVerb, GreekNoun, 
    GreekAdjective, GreekAdverb, GreekLemma, GreekParse
)


class DictionaryQuery:
    """
    High-level API for querying Greek dictionary data.
    
    Example:
        >>> from database import DictionaryQuery
        >>> query = DictionaryQuery()
        >>> 
        >>> # Look up a verb
        >>> verbs = query.lookup_verb("λεγω")
        >>> for verb in verbs:
        ...     print(f"{verb.fpp}: {verb.english}")
        >>> 
        >>> # Search by English meaning
        >>> words = query.search_by_english("love", pos="verb")
        >>> 
        >>> # Get all forms of a word
        >>> lemmas = query.get_lemmas_by_base("λογος")
    """
    
    def __init__(self, engine: Optional[Engine] = None):
        """
        Initialize query interface.
        
        Args:
            engine: SQLAlchemy engine (creates new if None)
        """
        self.engine = engine or get_engine()
    
    def _get_session(self) -> Session:
        """Get database session."""
        return get_session(self.engine)
    
    # === Verb Queries ===
    
    def lookup_verb(self, fpp: str, exact: bool = False) -> List[GreekVerb]:
        """
        Look up Greek verb by first principal part.
        
        Args:
            fpp: First principal part of verb
            exact: If True, exact match; if False, pattern match
            
        Returns:
            List of matching GreekVerb objects
        """
        session = self._get_session()
        try:
            query = session.query(GreekVerb)
            if exact:
                query = query.filter(GreekVerb.fpp == fpp)
            else:
                query = query.filter(GreekVerb.fpp.ilike(f'%{fpp}%'))
            return query.all()
        finally:
            session.close()
    
    def get_all_verbs(self, limit: Optional[int] = None) -> List[GreekVerb]:
        """Get all verbs (optionally limited)."""
        session = self._get_session()
        try:
            query = session.query(GreekVerb)
            if limit:
                query = query.limit(limit)
            return query.all()
        finally:
            session.close()
    
    # === Noun Queries ===
    
    def lookup_noun(self, fpp: str, exact: bool = False) -> List[GreekNoun]:
        """Look up Greek noun by first principal part."""
        session = self._get_session()
        try:
            query = session.query(GreekNoun)
            if exact:
                query = query.filter(GreekNoun.fpp == fpp)
            else:
                query = query.filter(GreekNoun.fpp.ilike(f'%{fpp}%'))
            return query.all()
        finally:
            session.close()
    
    def get_all_nouns(self, limit: Optional[int] = None) -> List[GreekNoun]:
        """Get all nouns (optionally limited)."""
        session = self._get_session()
        try:
            query = session.query(GreekNoun)
            if limit:
                query = query.limit(limit)
            return query.all()
        finally:
            session.close()
    
    # === Adjective Queries ===
    
    def lookup_adjective(self, fpp: str, exact: bool = False) -> List[GreekAdjective]:
        """Look up Greek adjective by first principal part."""
        session = self._get_session()
        try:
            query = session.query(GreekAdjective)
            if exact:
                query = query.filter(GreekAdjective.fpp == fpp)
            else:
                query = query.filter(GreekAdjective.fpp.ilike(f'%{fpp}%'))
            return query.all()
        finally:
            session.close()
    
    def get_all_adjectives(self, limit: Optional[int] = None) -> List[GreekAdjective]:
        """Get all adjectives (optionally limited)."""
        session = self._get_session()
        try:
            query = session.query(GreekAdjective)
            if limit:
                query = query.limit(limit)
            return query.all()
        finally:
            session.close()
    
    # === Adverb Queries ===
    
    def lookup_adverb(self, fpp: str, exact: bool = False) -> List[GreekAdverb]:
        """Look up Greek adverb by first principal part."""
        session = self._get_session()
        try:
            query = session.query(GreekAdverb)
            if exact:
                query = query.filter(GreekAdverb.fpp == fpp)
            else:
                query = query.filter(GreekAdverb.fpp.ilike(f'%{fpp}%'))
            return query.all()
        finally:
            session.close()
    
    def get_all_adverbs(self, limit: Optional[int] = None) -> List[GreekAdverb]:
        """Get all adverbs (optionally limited)."""
        session = self._get_session()
        try:
            query = session.query(GreekAdverb)
            if limit:
                query = query.limit(limit)
            return query.all()
        finally:
            session.close()
    
    # === Combined Queries ===
    
    def lookup_word(
        self, 
        text: str, 
        pos: Optional[str] = None,
        exact: bool = False
    ) -> Dict[str, List[Any]]:
        """
        Look up word across all parts of speech.
        
        Args:
            text: Greek word to look up
            pos: Part of speech filter ('verb', 'noun', 'adjective', 'adverb')
            exact: If True, exact match; if False, pattern match
            
        Returns:
            Dictionary with keys for each POS containing matching words
        """
        results = {}
        
        if pos is None or pos == 'verb':
            results['verbs'] = self.lookup_verb(text, exact=exact)
        if pos is None or pos == 'noun':
            results['nouns'] = self.lookup_noun(text, exact=exact)
        if pos is None or pos == 'adjective':
            results['adjectives'] = self.lookup_adjective(text, exact=exact)
        if pos is None or pos == 'adverb':
            results['adverbs'] = self.lookup_adverb(text, exact=exact)
        
        return results
    
    def search_by_english(
        self, 
        english_text: str,
        pos: Optional[str] = None,
        limit: int = 50
    ) -> Dict[str, List[Any]]:
        """
        Search for Greek words by English translation.
        
        Args:
            english_text: English text to search for
            pos: Part of speech filter
            limit: Maximum results per POS
            
        Returns:
            Dictionary with keys for each POS containing matching words
        """
        results = {}
        session = self._get_session()
        
        try:
            search_pattern = f'%{english_text}%'
            
            if pos is None or pos == 'verb':
                results['verbs'] = session.query(GreekVerb)\
                    .filter(GreekVerb.english.ilike(search_pattern))\
                    .limit(limit).all()
            
            if pos is None or pos == 'noun':
                results['nouns'] = session.query(GreekNoun)\
                    .filter(GreekNoun.english.ilike(search_pattern))\
                    .limit(limit).all()
            
            if pos is None or pos == 'adjective':
                results['adjectives'] = session.query(GreekAdjective)\
                    .filter(GreekAdjective.english.ilike(search_pattern))\
                    .limit(limit).all()
            
            if pos is None or pos == 'adverb':
                results['adverbs'] = session.query(GreekAdverb)\
                    .filter(GreekAdverb.english.ilike(search_pattern))\
                    .limit(limit).all()
            
            return results
        finally:
            session.close()
    
    # === Lemma and Parse Queries ===
    
    def get_lemmas_by_base(self, base_form: str, exact: bool = True) -> List[GreekLemma]:
        """
        Get lemmas by base form.
        
        Args:
            base_form: Base form to search for
            exact: If True, exact match; if False, pattern match
            
        Returns:
            List of matching GreekLemma objects
        """
        session = self._get_session()
        try:
            query = session.query(GreekLemma)
            if exact:
                query = query.filter(GreekLemma.bare_base_form == base_form)
            else:
                query = query.filter(GreekLemma.bare_base_form.ilike(f'%{base_form}%'))
            return query.all()
        finally:
            session.close()
    
    def get_parses_for_form(self, text: str, exact: bool = True) -> List[GreekParse]:
        """
        Get all possible parses for an inflected form.
        
        Args:
            text: Inflected form to parse
            exact: If True, exact match; if False, pattern match
            
        Returns:
            List of matching GreekParse objects
        """
        session = self._get_session()
        try:
            query = session.query(GreekParse)
            if exact:
                query = query.filter(GreekParse.bare_text == text)
            else:
                query = query.filter(GreekParse.bare_text.ilike(f'%{text}%'))
            return query.all()
        finally:
            session.close()
    
    # === Statistics ===
    
    def get_stats(self) -> Dict[str, int]:
        """
        Get database statistics.
        
        Returns:
            Dictionary with counts for each table
        """
        session = self._get_session()
        try:
            return {
                'verbs': session.query(func.count(GreekVerb.id)).scalar() or 0,
                'nouns': session.query(func.count(GreekNoun.id)).scalar() or 0,
                'adjectives': session.query(func.count(GreekAdjective.id)).scalar() or 0,
                'adverbs': session.query(func.count(GreekAdverb.id)).scalar() or 0,
                'lemmas': session.query(func.count(GreekLemma.id)).scalar() or 0,
                'parses': session.query(func.count(GreekParse.id)).scalar() or 0,
            }
        finally:
            session.close()
    
    # === Batch Operations ===
    
    def batch_lookup(
        self, 
        words: List[str],
        pos: Optional[str] = None
    ) -> Dict[str, Dict[str, List[Any]]]:
        """
        Look up multiple words at once.
        
        Args:
            words: List of Greek words to look up
            pos: Part of speech filter
            
        Returns:
            Dictionary mapping each word to its results
        """
        results = {}
        for word in words:
            results[word] = self.lookup_word(word, pos=pos, exact=False)
        return results
    
    def get_random_words(self, pos: str = 'verb', count: int = 10) -> List[Any]:
        """
        Get random words for a given part of speech.
        
        Args:
            pos: Part of speech ('verb', 'noun', 'adjective', 'adverb')
            count: Number of random words
            
        Returns:
            List of random word objects
        """
        session = self._get_session()
        try:
            model_map = {
                'verb': GreekVerb,
                'noun': GreekNoun,
                'adjective': GreekAdjective,
                'adverb': GreekAdverb,
            }
            
            if pos not in model_map:
                raise ValueError(f"Invalid POS: {pos}")
            
            model = model_map[pos]
            return session.query(model).order_by(func.random()).limit(count).all()
        finally:
            session.close()


def demo():
    """Demo of query API."""
    print("="*60)
    print("Greek Dictionary Query Demo")
    print("="*60 + "\n")
    
    query = DictionaryQuery()
    
    # Get stats
    print("Database Statistics:")
    stats = query.get_stats()
    for key, value in stats.items():
        print(f"  {key}: {value:,}")
    print()
    
    # Look up a verb
    print("Looking up verb 'αγαπω':")
    verbs = query.lookup_verb("αγαπω", exact=True)
    for verb in verbs:
        print(f"  {verb.fpp}: {verb.english}")
    print()
    
    # Search by English
    print("Searching for 'love':")
    results = query.search_by_english("love", pos="verb", limit=5)
    for verb in results.get('verbs', []):
        print(f"  {verb.fpp}: {verb.english}")
    print()
    
    # Get random words
    print("Random verbs:")
    random_verbs = query.get_random_words(pos='verb', count=5)
    for verb in random_verbs:
        print(f"  {verb.fpp}: {verb.english}")
    print()


if __name__ == '__main__':
    demo()
