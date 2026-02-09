"""
Greek Lemmatizer Dictionary Functions

This module implements the core dictionary functions for the Greek lemmatizer
following a similar workflow to the Latin lemmatizer.
"""

import pandas as pd
import os
import unicodedata
from typing import List, Dict, Any, Optional, Tuple

class GreekLemmatizer:
    def __init__(self, dict_dir: str = None):
        """
        Initialize the Greek lemmatizer with dictionary files
        
        Args:
            dict_dir: Path to dictionary directory (optional)
        """
        # Set up directory paths
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.dict_dir = dict_dir or os.path.join(self.base_dir, 'greek_dictionary')
        
        # Dictionary dataframes
        self.nouns_df = None
        self.verbs_df = None
        self.adjectives_df = None
        self.adverbs_df = None
        
        # Load dictionaries
        self.load_dictionaries()
        
    def load_dictionaries(self):
        """Load all dictionary files into dataframes"""
        try:
            # Load each dictionary with appropriate encoding for Greek
            self.nouns_df = pd.read_csv(os.path.join(self.dict_dir, 'nouns.csv'), 
                                     encoding='utf-8', sep=None, engine='python')
            print(f"Loaded nouns dictionary: {len(self.nouns_df)} entries")
            
            self.verbs_df = pd.read_csv(os.path.join(self.dict_dir, 'verbs.csv'), 
                                      encoding='utf-8', sep=None, engine='python')
            print(f"Loaded verbs dictionary: {len(self.verbs_df)} entries")
            
            self.adjectives_df = pd.read_csv(os.path.join(self.dict_dir, 'adjectives.csv'), 
                                          encoding='utf-8', sep=None, engine='python')
            print(f"Loaded adjectives dictionary: {len(self.adjectives_df)} entries")
            
            self.adverbs_df = pd.read_csv(os.path.join(self.dict_dir, 'adverbs.csv'), 
                                       encoding='utf-8', sep=None, engine='python')
            print(f"Loaded adverbs dictionary: {len(self.adverbs_df)} entries")
            
        except Exception as e:
            print(f"Error loading dictionary files: {e}")
            raise
    
    def normalize_greek(self, word: str) -> str:
        """Normalize Greek Unicode characters"""
        if not word:
            return ""
        return unicodedata.normalize('NFC', word.lower())
    
    def get_id(self, word: str) -> List[int]:
        """
        Get the ID(s) for a given word
        
        Args:
            word: Greek word to look up
            
        Returns:
            List of IDs for the word
        """
        word = self.normalize_greek(word)
        output = []
        
        # Check each dictionary for matches
        for df in [self.nouns_df, self.verbs_df, self.adjectives_df, self.adverbs_df]:
            if 'FPP' in df.columns:
                matches = df.loc[df['FPP'].str.lower() == word]
                if not matches.empty:
                    for idx, row in matches.iterrows():
                        output.append(idx)
        
        return output
    
    def get_words_by_id(self, ids: List[int]) -> Dict[int, List[str]]:
        """
        Get all word forms for given IDs
        
        Args:
            ids: List of word IDs
            
        Returns:
            Dictionary mapping IDs to lists of word forms
        """
        output = {}
        
        if not isinstance(ids, list):
            print("Invalid ID format provided")
            return {}
        
        for id in ids:
            # Search across all dataframes
            forms = []
            for df in [self.nouns_df, self.verbs_df, self.adjectives_df, self.adverbs_df]:
                if id < len(df):
                    row = df.iloc[id]
                    if 'FPP' in row and isinstance(row['FPP'], str):
                        forms.append(row['FPP'])
            
            if forms:
                output[id] = forms
                
        return output
    
    def get_words(self, word: str) -> Dict[int, List[str]]:
        """
        Get all word forms for a given word
        
        Args:
            word: Greek word to look up
            
        Returns:
            Dictionary mapping IDs to lists of word forms
        """
        ids = self.get_id(word)
        return self.get_words_by_id(ids)
    
    def get_definition(self, id: int) -> str:
        """
        Get the English definition for a given word ID
        
        Args:
            id: Word ID
            
        Returns:
            English definition as a string
        """
        output = "No definition found"
        
        # Check each dataframe for the ID
        for df in [self.nouns_df, self.verbs_df, self.adjectives_df, self.adverbs_df]:
            if id < len(df):
                row = df.iloc[id]
                if 'English' in row and isinstance(row['English'], str):
                    output = row['English']
                    break
                    
        return output
    
    def get_pos(self, id: int) -> str:
        """
        Get the part of speech for a given word ID
        
        Args:
            id: Word ID
            
        Returns:
            Part of speech as a string
        """
        # Check each dataframe for the ID
        if id < len(self.nouns_df):
            return "noun"
        elif id < len(self.verbs_df):
            return "verb"
        elif id < len(self.adjectives_df):
            return "adjective"
        elif id < len(self.adverbs_df):
            return "adverb"
        else:
            return "unknown"
    
    def get_dict_entry(self, word: str, show_def: bool = True) -> Dict[int, str]:
        """
        Get dictionary entries for a given word
        
        Args:
            word: Greek word to look up
            show_def: Whether to include definitions in the output
            
        Returns:
            Dictionary mapping IDs to dictionary entries
        """
        ids = self.get_id(word)
        output = {}
        
        for id in ids:
            pos = self.get_pos(id)
            
            # Find the correct dataframe based on POS
            df = None
            if pos == "noun":
                df = self.nouns_df
            elif pos == "verb":
                df = self.verbs_df
            elif pos == "adjective":
                df = self.adjectives_df
            elif pos == "adverb":
                df = self.adverbs_df
                
            if df is not None and id < len(df):
                row = df.iloc[id]
                
                # Get dictionary entry format based on part of speech
                if 'FPP' in row and isinstance(row['FPP'], str):
                    entry_text = f"{row['FPP']}"
                    
                    if show_def and 'English' in row and isinstance(row['English'], str):
                        definition = row['English']
                        entry_text += f" - {definition}"
                        
                    output[id] = f"{pos}: {entry_text}"
                    
        return output
    
    def lemmatize(self, word: str) -> List[Dict[str, Any]]:
        """
        Lemmatize a Greek word
        
        Args:
            word: Greek word to lemmatize
            
        Returns:
            List of lemmatization results with part of speech and definition
        """
        normalized_word = self.normalize_greek(word)
        results = []
        
        # Direct matches
        for df_name, df in [("noun", self.nouns_df), 
                            ("verb", self.verbs_df), 
                            ("adjective", self.adjectives_df), 
                            ("adverb", self.adverbs_df)]:
            
            if 'FPP' in df.columns:
                # Look for exact matches
                matches = df[df['FPP'].str.lower() == normalized_word]
                
                if not matches.empty:
                    for idx, row in matches.iterrows():
                        result = {
                            'lemma': row['FPP'] if isinstance(row['FPP'], str) else "",
                            'pos': df_name,
                            'definition': row['English'] if 'English' in row and isinstance(row['English'], str) else "No definition"
                        }
                        results.append(result)
        
        # If no direct matches, try stem matching
        if not results:
            # Try stem matching - remove final letters
            for i in range(1, min(4, len(normalized_word))):
                stem = normalized_word[:-i]
                if len(stem) < 3:  # Don't use stems that are too short
                    continue
                    
                for df_name, df in [("noun", self.nouns_df), 
                                    ("verb", self.verbs_df), 
                                    ("adjective", self.adjectives_df), 
                                    ("adverb", self.adverbs_df)]:
                    
                    if 'FPP' in df.columns:
                        # Look for stem matches
                        matches = df[df['FPP'].str.lower().str.startswith(stem)]
                        
                        if not matches.empty:
                            for idx, row in matches.iterrows():
                                result = {
                                    'lemma': row['FPP'] if isinstance(row['FPP'], str) else "",
                                    'pos': df_name,
                                    'definition': row['English'] if 'English' in row and isinstance(row['English'], str) else "No definition"
                                }
                                results.append(result)
                                
                            # If we found matches with this stem, stop looking for more
                            if results:
                                break
                                
                # If we found matches with this stem length, stop trying shorter stems
                if results:
                    break
        
        return results
    
    def analyze_text(self, text: str) -> List[Dict[str, Any]]:
        """
        Analyze a Greek text by lemmatizing each word
        
        Args:
            text: Greek text to analyze
            
        Returns:
            List of analysis results for each word
        """
        # Simple word tokenization by whitespace
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
    
    def find_all_forms(self, lemma: str) -> List[str]:
        """
        Find all forms of a given lemma
        
        Args:
            lemma: Greek lemma to look up
            
        Returns:
            List of all forms of the lemma
        """
        normalized_lemma = self.normalize_greek(lemma)
        results = []
        
        # Find the lemma in our dictionaries
        lemma_ids = self.get_id(normalized_lemma)
        
        if lemma_ids:
            # Find all forms for each lemma ID
            for id in lemma_ids:
                forms = self.get_words_by_id([id])
                for form_list in forms.values():
                    results.extend(form_list)
        
        return results

# Function to demonstrate the workflow
def demonstrate_greek_lemmatizer():
    """Run a demonstration of the Greek lemmatizer workflow"""
    lemmatizer = GreekLemmatizer()
    
    # Test with some Greek words
    test_words = [
        "λόγος",      # logos (word)
        "ἄνθρωπος",   # anthropos (human)
        "φιλοσοφία",  # philosophia (philosophy)
        "ἀγάπη",      # agape (love)
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

if __name__ == "__main__":
    demonstrate_greek_lemmatizer()
