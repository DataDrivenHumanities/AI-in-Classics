#!/usr/bin/env python3
"""
Basic Dictionary Lookup Examples

Demonstrates simple lookups using the DictionaryQuery API.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from database import DictionaryQuery


def main():
    print("="*60)
    print("Greek Dictionary - Basic Lookups")
    print("="*60 + "\n")
    
    # Initialize query interface
    query = DictionaryQuery()
    
    # Example 1: Database Statistics
    print("1. Database Statistics")
    print("-" * 40)
    stats = query.get_stats()
    for pos, count in stats.items():
        print(f"  {pos.capitalize():<15} {count:>8,}")
    print()
    
    # Example 2: Look up a specific verb
    print("2. Verb Lookup: 'αγαπω' (to love)")
    print("-" * 40)
    verbs = query.lookup_verb("αγαπω", exact=True)
    if verbs:
        for verb in verbs:
            print(f"  Greek:   {verb.fpp}")
            print(f"  English: {verb.english}")
            if verb.sentiment:
                print(f"  Sentiment: {verb.sentiment}")
    else:
        print("  No results found")
    print()
    
    # Example 3: Pattern matching
    print("3. Pattern Search: Words containing 'λεγ'")
    print("-" * 40)
    verbs = query.lookup_verb("λεγ", exact=False)
    for i, verb in enumerate(verbs[:5], 1):
        print(f"  {i}. {verb.fpp}: {verb.english}")
    if len(verbs) > 5:
        print(f"  ... and {len(verbs) - 5} more")
    print()
    
    # Example 4: Look up a noun
    print("4. Noun Lookup: 'λογος' (word)")
    print("-" * 40)
    nouns = query.lookup_noun("λογος", exact=True)
    if nouns:
        for noun in nouns:
            print(f"  Greek:   {noun.fpp}")
            print(f"  English: {noun.english}")
    else:
        print("  No results found")
    print()
    
    # Example 5: Search by English translation
    print("5. English Search: 'love'")
    print("-" * 40)
    results = query.search_by_english("love", limit=5)
    for pos, items in results.items():
        if items:
            print(f"  {pos.capitalize()}:")
            for item in items[:3]:
                print(f"    • {item.fpp}: {item.english}")
            if len(items) > 3:
                print(f"    ... and {len(items) - 3} more")
    print()
    
    # Example 6: Combined lookup (all parts of speech)
    print("6. Combined Lookup: 'αγαθος' (good)")
    print("-" * 40)
    all_results = query.lookup_word("αγαθος", exact=False)
    for pos, items in all_results.items():
        if items:
            print(f"  {pos.capitalize()}: {len(items)} result(s)")
            for item in items[:2]:
                print(f"    • {item.fpp}: {item.english}")
    print()
    
    # Example 7: Random words
    print("7. Random Verbs (for practice)")
    print("-" * 40)
    random_verbs = query.get_random_words(pos='verb', count=5)
    for i, verb in enumerate(random_verbs, 1):
        print(f"  {i}. {verb.fpp}")
        print(f"     {verb.english}")
    print()
    
    print("="*60)
    print("Examples completed!")
    print("="*60)


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
