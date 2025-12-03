#!/usr/bin/env python3
"""
Batch Processing Example

Demonstrates efficient batch lookups for processing multiple words at once.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from database import DictionaryQuery


def main():
    print("="*60)
    print("Greek Dictionary - Batch Processing")
    print("="*60 + "\n")
    
    query = DictionaryQuery()
    
    # Example 1: Batch lookup of multiple words
    print("1. Batch Lookup of Common Words")
    print("-" * 40)
    
    common_words = [
        "λογος",    # word, reason
        "ανθρωπος", # human, man
        "θεος",     # god
        "αγαπω",    # to love
        "λεγω",     # to say
    ]
    
    results = query.batch_lookup(common_words)
    
    for word in common_words:
        word_results = results[word]
        total = sum(len(items) for items in word_results.values())
        print(f"\n  '{word}': {total} total result(s)")
        
        for pos, items in word_results.items():
            if items:
                print(f"    {pos}: {len(items)}")
                for item in items[:2]:
                    print(f"      • {item.fpp}: {item.english[:50]}...")
    
    print("\n")
    
    # Example 2: Processing text with multiple Greek words
    print("2. Processing Greek Text")
    print("-" * 40)
    
    # Sample text (simplified)
    text_words = ["εν", "αρχη", "ην", "λογος"]
    print(f"  Text words: {' '.join(text_words)}\n")
    
    for word in text_words:
        word_results = query.lookup_word(word, exact=False)
        found = False
        
        for pos, items in word_results.items():
            if items:
                found = True
                print(f"  '{word}' ({pos}):")
                for item in items[:1]:
                    print(f"    → {item.english}")
        
        if not found:
            print(f"  '{word}': Not found in dictionary")
    
    print("\n")
    
    # Example 3: English to Greek batch lookup
    print("3. English to Greek Translations")
    print("-" * 40)
    
    english_words = ["love", "wisdom", "word", "man", "god"]
    
    for eng_word in english_words:
        print(f"\n  Searching for '{eng_word}':")
        results = query.search_by_english(eng_word, limit=3)
        
        found_any = False
        for pos, items in results.items():
            if items:
                found_any = True
                for item in items[:2]:
                    print(f"    {item.fpp} ({pos})")
        
        if not found_any:
            print(f"    No results found")
    
    print("\n")
    print("="*60)
    print("Batch processing completed!")
    print("="*60)


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
