#!/usr/bin/env python3
"""
Greek Lemmatizer Workflow Demonstration

This script demonstrates the workflow for the Greek lemmatizer,
following the same pattern as the Latin lemmatizer workflow.

It shows the process of:
1. Loading dictionary data
2. Finding word IDs
3. Getting dictionary entries
4. Lemmatizing words and texts
5. Finding all forms for a lemma
"""

from GreekDictFunctions import GreekLemmatizer
import sys
import unicodedata
import pandas as pd
import os

def print_separator(title=None):
    """Print a separator line with optional title"""
    width = 80
    if title:
        print("\n" + "=" * 10 + f" {title} " + "=" * (width - len(title) - 12) + "\n")
    else:
        print("\n" + "=" * width + "\n")

def format_dict_entry(entry):
    """Format dictionary entry for pretty printing"""
    if not entry:
        return "No entry found"
    
    lines = []
    for id, text in entry.items():
        lines.append(f"ID {id}: {text}")
    
    return "\n".join(lines)

def main():
    """Run the Greek lemmatizer workflow demonstration"""
    print_separator("GREEK LEMMATIZER WORKFLOW DEMONSTRATION")
    
    # Step 1: Initialize the lemmatizer
    print("Initializing Greek Lemmatizer...")
    try:
        lemmatizer = GreekLemmatizer()
    except Exception as e:
        print(f"Error initializing lemmatizer: {e}")
        sys.exit(1)
        
    print("Greek Lemmatizer initialized successfully!")
    
    # Step 2: Demonstrate looking up words
    print_separator("WORD LOOKUP DEMONSTRATION")
    
    # Define test words with their English translations
    test_words = [
        ("λόγος", "logos (word)"),
        ("ἄνθρωπος", "anthropos (human)"),
        ("φιλοσοφία", "philosophia (philosophy)"),
        ("ἀγάπη", "agape (love)"),
        ("ψυχή", "psyche (soul)"),
        ("σοφία", "sophia (wisdom)"),
        ("θεός", "theos (god)")
    ]
    
    for greek_word, english in test_words:
        print(f"\nLooking up: {greek_word} ({english})")
        
        # Get word IDs
        ids = lemmatizer.get_id(greek_word)
        
        if ids:
            print(f"Found {len(ids)} ID(s): {', '.join(map(str, ids))}")
            
            # Get dictionary entries
            entries = lemmatizer.get_dict_entry(greek_word)
            print("\nDictionary entries:")
            print(format_dict_entry(entries))
            
            # Get all forms
            forms = lemmatizer.find_all_forms(greek_word)
            if forms:
                print(f"\nAll forms: {', '.join(forms)}")
            else:
                print("\nNo additional forms found")
        else:
            print("No IDs found - using fallback search...")
            
            # Try lemmatization as fallback
            lemmas = lemmatizer.lemmatize(greek_word)
            if lemmas:
                print(f"Found {len(lemmas)} possible lemmas:")
                for i, lemma in enumerate(lemmas, 1):
                    print(f"  {i}. {lemma['lemma']} ({lemma['pos']}): {lemma['definition']}")
            else:
                print("No matches found in dictionary")
                
    # Step 3: Demonstrate text analysis
    print_separator("TEXT ANALYSIS DEMONSTRATION")
    
    # Test passages
    passages = [
        ("ἐν ἀρχῇ ἦν ὁ λόγος", "In the beginning was the word"),
        ("γνῶθι σεαυτόν", "Know thyself"),
        ("σοφία ἄρχει", "Wisdom rules"),
    ]
    
    for greek_text, english in passages:
        print(f"\nAnalyzing text: {greek_text} ({english})")
        
        analysis = lemmatizer.analyze_text(greek_text)
        for item in analysis:
            print(f"\nWord: {item['word']}")
            if item['lemmas']:
                for lemma in item['lemmas']:
                    print(f"  → {lemma['lemma']} ({lemma['pos']}): {lemma['definition']}")
            else:
                print("  → No lemma found")
                
    # Step 4: Demonstrate morphological form generation
    print_separator("MORPHOLOGICAL FORM GENERATION")
    
    # Sample words for form generation
    for greek_word, english in test_words[:3]:  # Use first three test words
        print(f"\nGenerating forms for: {greek_word} ({english})")
        
        # First get its lemmas
        lemmas = lemmatizer.lemmatize(greek_word)
        if lemmas:
            print(f"Found {len(lemmas)} lemmas")
            
            # For each lemma, try to find all forms
            for lemma in lemmas:
                print(f"\nForms for lemma '{lemma['lemma']}' ({lemma['pos']}):")
                forms = lemmatizer.find_all_forms(lemma['lemma'])
                
                if forms:
                    print("Found forms:")
                    for i, form in enumerate(set(forms), 1):  # Use set to remove duplicates
                        print(f"  {i}. {form}")
                else:
                    print("No additional forms found")
        else:
            print("No lemmas found for this word")
            
    print_separator("WORKFLOW DEMONSTRATION COMPLETE")
    print("The Greek lemmatizer workflow follows the same pattern as the Latin lemmatizer:")
    print("1. Load dictionary data")
    print("2. Find word IDs")
    print("3. Get dictionary entries")
    print("4. Lemmatize words and texts")
    print("5. Find all forms for a lemma")
    
    print("\nThis demonstration shows how to use the Greek lemmatizer")
    print("in a workflow matching the Latin lemmatizer approach.")

if __name__ == "__main__":
    main()
