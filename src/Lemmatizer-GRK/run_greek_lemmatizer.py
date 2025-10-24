"""
Greek Lemmatizer Runner Script

This script implements a workflow for the Greek lemmatizer using existing
dictionary files instead of generating them from XML sources.

The workflow follows these steps:
1. Load the existing dictionary CSV files
2. Process the dictionary data
3. Create a lemmatization function
4. Test with sample Greek words
"""

import pandas as pd
import os
import sys
from typing import List, Dict, Any, Tuple, Optional
import unicodedata
import re

class GreekLemmatizer:
    """Greek lemmatizer using existing dictionary files"""
    
    def __init__(self):
        """Initialize the Greek lemmatizer with dictionary files"""
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.dict_dir = os.path.join(self.base_dir, 'greek_dictionary')
        
        # Dictionary files
        self.nouns_file = os.path.join(self.dict_dir, 'nouns.csv')
        self.verbs_file = os.path.join(self.dict_dir, 'verbs.csv')
        self.adjectives_file = os.path.join(self.dict_dir, 'adjectives.csv')
        self.adverbs_file = os.path.join(self.dict_dir, 'adverbs.csv')
        
        # Dictionary dataframes
        self.nouns_df = None
        self.verbs_df = None
        self.adjectives_df = None
        self.adverbs_df = None
        
        # Combined dictionary
        self.combined_dict = {}
        
        # Load dictionaries
        self.load_dictionaries()
        
    def load_dictionaries(self):
        """Load all dictionary files into dataframes"""
        print("Loading Greek dictionary files...")
        
        try:
            # Load each dictionary with appropriate encoding for Greek
            self.nouns_df = pd.read_csv(self.nouns_file, encoding='utf-8', sep=None, engine='python')
            print(f"Loaded nouns dictionary: {len(self.nouns_df)} entries")
            
            self.verbs_df = pd.read_csv(self.verbs_file, encoding='utf-8', sep=None, engine='python')
            print(f"Loaded verbs dictionary: {len(self.verbs_df)} entries")
            
            self.adjectives_df = pd.read_csv(self.adjectives_file, encoding='utf-8', sep=None, engine='python')
            print(f"Loaded adjectives dictionary: {len(self.adjectives_df)} entries")
            
            self.adverbs_df = pd.read_csv(self.adverbs_file, encoding='utf-8', sep=None, engine='python')
            print(f"Loaded adverbs dictionary: {len(self.adverbs_df)} entries")
            
            # Build combined dictionary for faster lookup
            self._build_combined_dict()
            
        except Exception as e:
            print(f"Error loading dictionary files: {e}")
            sys.exit(1)
    
    def _build_combined_dict(self):
        """Build a combined dictionary from all dataframes for faster lookup"""
        print("Building combined dictionary for faster lookup...")
        
        # Process nouns
        if 'FPP' in self.nouns_df.columns:
            for _, row in self.nouns_df.iterrows():
                word = row['FPP']
                if isinstance(word, str) and word.strip():
                    normalized_word = self.normalize_greek_nfd(word.strip())
                    if normalized_word not in self.combined_dict:
                        self.combined_dict[normalized_word] = []
                    
                    entry = {
                        'lemma': normalized_word,
                        'pos': 'noun',
                        'definition': row.get('English', 'No definition available')
                    }
                    self.combined_dict[normalized_word].append(entry)
        
        # Process verbs
        if 'FPP' in self.verbs_df.columns:
            for _, row in self.verbs_df.iterrows():
                word = row['FPP']
                if isinstance(word, str) and word.strip():
                    normalized_word = self.normalize_greek_nfd(word.strip())
                    if normalized_word not in self.combined_dict:
                        self.combined_dict[normalized_word] = []
                    
                    entry = {
                        'lemma': normalized_word,
                        'pos': 'verb',
                        'definition': row.get('English', 'No definition available')
                    }
                    self.combined_dict[normalized_word].append(entry)
        
        # Process adjectives
        if 'FPP' in self.adjectives_df.columns:
            for _, row in self.adjectives_df.iterrows():
                word = row['FPP']
                if isinstance(word, str) and word.strip():
                    normalized_word = self.normalize_greek_nfd(word.strip())
                    if normalized_word not in self.combined_dict:
                        self.combined_dict[normalized_word] = []
                    
                    entry = {
                        'lemma': normalized_word,
                        'pos': 'adjective',
                        'definition': row.get('English', 'No definition available')
                    }
                    self.combined_dict[normalized_word].append(entry)
        
        # Process adverbs
        if 'FPP' in self.adverbs_df.columns:
            for _, row in self.adverbs_df.iterrows():
                word = row['FPP']
                if isinstance(word, str) and word.strip():
                    normalized_word = self.normalize_greek_nfd(word.strip())
                    if normalized_word not in self.combined_dict:
                        self.combined_dict[normalized_word] = []
                    
                    entry = {
                        'lemma': normalized_word,
                        'pos': 'adverb',
                        'definition': row.get('English', 'No definition available')
                    }
                    self.combined_dict[normalized_word].append(entry)
        
        print(f"Combined dictionary built with {len(self.combined_dict)} unique lemmas")
    
    def normalize_greek_nfc(self, word: str) -> str:
        """Normalize Greek Unicode characters"""
        if not word:
            return ""
        return unicodedata.normalize('NFC', word)

    def normalize_greek_nfd(self, word: str) -> str:
        if not word:
            return ""
        decomposed = unicodedata.normalize('NFD', word)
        stripped = ''.join(c for c in decomposed if not unicodedata.combining(c))
        recomposed = unicodedata.normalize('NFC', stripped)

        return recomposed.lower()
    
    def lemmatize(self, word: str) -> List[Dict[str, Any]]:
        """
        Lemmatize a Greek word
        
        Args:
            word: Greek word to lemmatize
            
        Returns:
            List of possible lemmas with part of speech and definition
        """
        normalized_word = self.normalize_greek_nfd(word)
        
        # Direct match in combined dictionary
        if normalized_word in self.combined_dict:
            return self.combined_dict[normalized_word]
            
        # Try stem matching by removing final letters
        for i in range(1, min(4, len(normalized_word))):
            stem = normalized_word[:-i]
            matches = []
            
            for lemma, entries in self.combined_dict.items():
                if lemma.startswith(stem) and len(lemma) >= len(stem) + 1:
                    for entry in entries:
                        matches.append(entry)
            
            if matches:
                print(f"Found stem matches for '{word}' using stem '{stem}'")
                return matches[:5]  # Limit to top 5 matches
        
        return []
        
    def analyze_text(self, text: str) -> List[Dict[str, Any]]:
        """
        Analyze a Greek text by lemmatizing each word
        
        Args:
            text: Greek text to analyze
            
        Returns:
            List of lemmatized words with their analyses
        """
        # Simple word tokenization (split by whitespace)
        words = text.split()
        results = []
        
        for word in words:
            # Clean up punctuation
            clean_word = word.strip('.,;:!?""''()[]{}')
            if not clean_word:
                continue
                
            lemmas = self.lemmatize(clean_word)
            results.append({
                'word': clean_word,
                'lemmas': lemmas
            })
            
        return results
        
def main():
    """Main function to run the Greek lemmatizer"""
    print("Starting Greek Lemmatizer")
    
    # Initialize lemmatizer
    lemmatizer = GreekLemmatizer()
    
    # Test with some Greek words
    test_words = [
        "λόγος",      # logos (word)
        "ἄνθρωπος",   # anthropos (human)
        "φιλοσοφία",  # philosophia (philosophy)
        "ἀγάπη",      # agape (love)
        "ψυχή",       # psyche (soul)
        "σοφία",      # sophia (wisdom)
        "θεός"        # theos (god)
    ]
    
    print("\nTesting Greek lemmatizer with sample words:")
    
    for word in test_words:
        print(f"\nLemmatizing: {word}")
        results = lemmatizer.lemmatize(word)
        
        if results:
            print(f"Found {len(results)} possible lemmas:")
            for i, result in enumerate(results, 1):
                print(f"  {i}. {result['lemma']} ({result['pos']}): {result['definition']}")
        else:
            print("No matches found")
    
    # Test with a Greek text
    sample_text = "ἐν ἀρχῇ ἦν ὁ λόγος"  # "In the beginning was the word"
    
    print("\nAnalyzing Greek text:")
    print(f"Text: {sample_text}")
    
    analysis = lemmatizer.analyze_text(sample_text)
    for item in analysis:
        print(f"\nWord: {item['word']}")
        if item['lemmas']:
            for lemma in item['lemmas']:
                print(f"  → {lemma['lemma']} ({lemma['pos']}): {lemma['definition']}")
        else:
            print("  → No lemma found")
    
    print("\nGreek lemmatizer workflow completed!")

if __name__ == "__main__":
    main()
