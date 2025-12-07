#!/usr/bin/env python
"""
Test script to demonstrate the performance improvements of the cached lemmatizer.

This script:
1. Loads a sample Greek text
2. Times the lemmatization using both the standard and cached lemmatizers
3. Reports performance statistics
"""
import os
import sys
import time
import unittest
from collections import Counter

# Add project root to path to import utils
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.append(project_root)

# Import CLTK lemmatizer
from cltk.lemmatize.grc import GreekBackoffLemmatizer

# Import our cached lemmatizer wrapper
try:
    from src.utils.lemmatizer_utils import wrap_lemmatizer, CachedLemmatizer
except ImportError:
    print("Error: lemmatizer_utils module not found")
    sys.exit(1)


class TestLemmatizerCache(unittest.TestCase):
    """Tests for the cached lemmatizer implementation"""
    
    def setUp(self):
        """Set up lemmatizers and test data"""
        # Create standard and cached lemmatizers
        self.standard_lemmatizer = GreekBackoffLemmatizer()
        self.cached_lemmatizer = wrap_lemmatizer(GreekBackoffLemmatizer())
        
        # Sample Greek text with deliberately repeated words
        # This is a contrived example with repetition to demonstrate caching benefits
        self.sample_text = """
        ἄνδρα μοι ἔννεπε, μοῦσα, πολύτροπον, ὃς μάλα πολλὰ
        πλάγχθη, ἐπεὶ Τροίης ἱερὸν πτολίεθρον ἔπερσεν·
        πολλῶν δ᾽ ἀνθρώπων ἴδεν ἄστεα καὶ νόον ἔγνω,
        πολλὰ δ᾽ ὅ γ᾽ ἐν πόντῳ πάθεν ἄλγεα ὃν κατὰ θυμόν,
        ἀρνύμενος ἥν τε ψυχὴν καὶ νόστον ἑταίρων.
        ἀλλ᾽ οὐδ᾽ ὣς ἑτάρους ἐρρύσατο, ἱέμενός περ·
        αὐτῶν γὰρ σφετέρῃσιν ἀτασθαλίῃσιν ὄλοντο,
        νήπιοι, οἳ κατὰ βοῦς Ὑπερίονος Ἠελίοιο
        ἤσθιον· αὐτὰρ ὁ τοῖσιν ἀφείλετο νόστιμον ἦμαρ.
        τῶν ἁμόθεν γε, θεά, θύγατερ Διός, εἰπὲ καὶ ἡμῖν.
        """
        
        # Split into tokens, skipping empty strings
        self.tokens = [token for token in self.sample_text.split() if token]
        
        # Create a text with more repetition to demonstrate caching benefits
        repeated_tokens = self.tokens * 5  # Repeat 5 times
        self.repeated_text = repeated_tokens

    def test_lemmatization_correctness(self):
        """Test that cached lemmatizer produces the same results as the standard one"""
        # Lemmatize with both lemmatizers
        standard_results = self.standard_lemmatizer.lemmatize(self.tokens)
        cached_results = self.cached_lemmatizer.lemmatize(self.tokens)
        
        # Check each pair of results
        for (orig_token1, lemma1), (orig_token2, lemma2) in zip(standard_results, cached_results):
            self.assertEqual(orig_token1, orig_token2)
            self.assertEqual(lemma1, lemma2)
    
    def test_performance_improvement(self):
        """Test that cached lemmatizer provides performance improvement with repeated text"""
        # Time standard lemmatizer
        start_time = time.time()
        standard_results = self.standard_lemmatizer.lemmatize(self.repeated_text)
        standard_time = time.time() - start_time
        
        # Time cached lemmatizer
        start_time = time.time()
        cached_results = self.cached_lemmatizer.lemmatize(self.repeated_text)
        cached_time = time.time() - start_time
        
        # Print results
        print(f"\nPerformance test results:")
        print(f"Standard lemmatizer: {standard_time:.4f}s")
        print(f"Cached lemmatizer:   {cached_time:.4f}s")
        
        if standard_time > 0:  # Avoid division by zero
            improvement = (standard_time - cached_time) / standard_time * 100
            print(f"Performance improvement: {improvement:.1f}%")
        
        # Analysis of word frequency in the text
        token_counter = Counter(self.repeated_text)
        unique_tokens = len(token_counter)
        total_tokens = len(self.repeated_text)
        repeat_ratio = unique_tokens / total_tokens
        
        print(f"Text analysis:")
        print(f"Total tokens:      {total_tokens}")
        print(f"Unique tokens:     {unique_tokens}")
        print(f"Repetition ratio:  {repeat_ratio:.4f}")
        print(f"Most common words: {token_counter.most_common(5)}")
        
        # Check cache stats
        hits = self.cached_lemmatizer.stats.get("cache_hits", 0)
        misses = self.cached_lemmatizer.stats.get("cache_misses", 0)
        
        print(f"Cache stats:")
        print(f"Cache hits:   {hits}")
        print(f"Cache misses: {misses}")
        if hits + misses > 0:
            hit_rate = hits / (hits + misses) * 100
            print(f"Hit rate:     {hit_rate:.1f}%")
        
        # Assert that there's improvement, though exact amount depends on hardware
        self.assertLess(cached_time, standard_time)
        
        # For highly repetitive text, expected hit rate should be high
        if hits + misses > 0:
            hit_rate = hits / (hits + misses) * 100
            # We should expect a high hit rate with our repetitive text
            self.assertGreater(hit_rate, 60.0)


def main():
    """Run the tests and display results"""
    unittest.main()


if __name__ == "__main__":
    main()
