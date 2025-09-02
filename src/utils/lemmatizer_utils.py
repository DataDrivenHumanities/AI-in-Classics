"""
Utilities for lemmatization caching to improve performance of the Greek lemmatizer.

This module provides a caching wrapper for the CLTK Greek lemmatizer to avoid
re-lemmatizing the same tokens multiple times, significantly improving performance
for repetitive text processing tasks.
"""
import logging
from typing import List, Dict, Tuple, Any, Optional, Union
import os
import time

# Try to import the cache utility, fall back to a simple dict if not available
try:
    from src.utils.cache_utils import cache
    from src.utils.logging_utils import setup_logger
    logger = setup_logger('lemmatizer_cache')
except ImportError:
    import logging
    logger = logging.getLogger('lemmatizer_cache')
    logging.basicConfig(level=logging.INFO)
    
    # Create a simple dictionary-based cache if the cache utility isn't available
    class SimpleCache:
        def __init__(self):
            self.cache_dict = {}
            
        def has(self, key):
            return key in self.cache_dict
            
        def get(self, key, default=None):
            return self.cache_dict.get(key, default)
            
        def set(self, key, value):
            self.cache_dict[key] = value
    
    cache = SimpleCache()

class CachedLemmatizer:
    """
    A wrapper class for CLTK's GreekBackoffLemmatizer that caches lemmatization results.
    
    This significantly improves performance by avoiding repeated lemmatization of
    the same tokens, which is especially useful for processing large classical texts
    where the same words appear frequently.
    """
    
    def __init__(self, lemmatizer, cache_prefix="lemmatizer_grk_"):
        """
        Initialize the cached lemmatizer wrapper.
        
        Args:
            lemmatizer: The underlying lemmatizer instance (must have a lemmatize method)
            cache_prefix: Prefix to use for cache keys
        """
        self.lemmatizer = lemmatizer
        self.cache_prefix = cache_prefix
        self.cache = cache
        self.stats = {
            "cache_hits": 0,
            "cache_misses": 0,
            "tokens_processed": 0,
            "time_saved": 0
        }
        
        # Record initialization time
        self.start_time = time.time()
        logger.info(f"CachedLemmatizer initialized with prefix '{cache_prefix}'")
        
    def _get_cache_key(self, token: str) -> str:
        """Generate a consistent cache key for a token"""
        # Normalize the token to ensure consistent caching
        normalized_token = token.lower().strip()
        return f"{self.cache_prefix}{normalized_token}"
        
    def lemmatize_token(self, token: str) -> Tuple[str, str]:
        """
        Lemmatize a single token with caching.
        
        Args:
            token: A single word token to lemmatize
            
        Returns:
            Tuple of (original_token, lemma)
        """
        self.stats["tokens_processed"] += 1
        
        # Check if the token is already in cache
        cache_key = self._get_cache_key(token)
        
        if self.cache.has(cache_key):
            self.stats["cache_hits"] += 1
            return (token, self.cache.get(cache_key))
            
        # Not in cache, call the actual lemmatizer
        start_time = time.time()
        
        # The CLTK lemmatizer returns a list of tuples even for a single token
        # We extract just the first result's lemma
        result = self.lemmatizer.lemmatize(tokens=[token])
        lemma = result[0][1] if result else token
        
        # Track time that would have been spent on repeated lemmatizations
        lemmatize_time = time.time() - start_time
        self.stats["cache_misses"] += 1
        
        # Cache the result
        self.cache.set(cache_key, lemma)
        
        return (token, lemma)
    
    def lemmatize(self, tokens: List[str]) -> List[Tuple[str, str]]:
        """
        Lemmatize a list of tokens, using cache where possible.
        
        This maintains the same interface as the CLTK lemmatizer but uses
        caching to avoid redundant work.
        
        Args:
            tokens: List of tokens to lemmatize
            
        Returns:
            List of tuples of (original_token, lemma)
        """
        start_time = time.time()
        
        # Process each token
        results = [self.lemmatize_token(token) for token in tokens]
        
        # Update time saved stat if we had any cache hits
        if self.stats["cache_hits"] > 0:
            # Estimate time saved based on cache hits and average lemmatization time
            avg_lemmatize_time = 0
            if self.stats["cache_misses"] > 0:
                avg_lemmatize_time = (time.time() - self.start_time) / max(1, self.stats["cache_misses"])
            self.stats["time_saved"] += self.stats["cache_hits"] * avg_lemmatize_time
        
        # Log statistics periodically
        if (self.stats["tokens_processed"] % 1000) == 0:
            hit_rate = 0
            if self.stats["tokens_processed"] > 0:
                hit_rate = self.stats["cache_hits"] / self.stats["tokens_processed"] * 100
            logger.info(f"Lemmatizer cache stats: {self.stats['cache_hits']} hits, {self.stats['cache_misses']} misses, "
                      f"{hit_rate:.1f}% hit rate, {self.stats['time_saved']:.2f}s saved")
        
        return results

def wrap_lemmatizer(lemmatizer):
    """
    Wrap a CLTK lemmatizer with caching functionality.
    
    Args:
        lemmatizer: An instance of a CLTK lemmatizer
        
    Returns:
        CachedLemmatizer instance wrapping the provided lemmatizer
    """
    return CachedLemmatizer(lemmatizer)
