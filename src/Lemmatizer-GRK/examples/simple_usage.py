#!/usr/bin/env python3
"""
Simple Usage Examples

Quick start guide for querying the Greek dictionary.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from database import DictionaryQuery


def main():
    # Initialize query interface
    query = DictionaryQuery()
    
    # Example 1: Look up a verb
    print("Looking up verb 'αγαπω':")
    verbs = query.lookup_verb("αγαπω", exact=True)
    for verb in verbs:
        print(f"  {verb.fpp}: {verb.english}")
    
    print()
    
    # Example 2: Search by English
    print("Searching for 'love':")
    results = query.search_by_english("love", pos="verb", limit=5)
    for verb in results.get('verbs', []):
        print(f"  {verb.fpp}: {verb.english}")
    
    print()
    
    # Example 3: Get database stats
    print("Database statistics:")
    stats = query.get_stats()
    for pos, count in stats.items():
        print(f"  {pos}: {count:,}")


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        print("\nMake sure PostgreSQL is running and data is loaded.")
        print("Run: python -m database.loader --drop")
        sys.exit(1)
