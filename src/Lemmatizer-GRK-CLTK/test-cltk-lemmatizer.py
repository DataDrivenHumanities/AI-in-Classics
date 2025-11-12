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
from GreekCLTKLemmatizer import GreekCLTKLemmatizer

def main():
    """Main function to run the Greek lemmatizer"""
    print("Starting Greek Lemmatizer")

    # Initialize lemmatizer
    lemmatizer = GreekCLTKLemmatizer()

    # Test with some Greek words
    test_words = [
        "λόγος",  # logos (word)
        "ἄνθρωπος",  # anthropos (human)
        "φιλοσοφία",  # philosophia (philosophy)
        "ἀγάπη",  # agape (love)
        "ψυχή",  # psyche (soul)
        "σοφία",  # sophia (wisdom)
        "θεός"  # theos (god)
    ]

    print("\nTesting Greek lemmatizer with sample words:")

    for i, word in enumerate(test_words, 1):
        print(f"\nLemmatizing: {word}")
        results = lemmatizer.lemmatize_text(word)

        if results:
            print(f"  {i}. {word} → {results[0]}")
        else:
            print("No matches found")

    # Test with a Greek text
    sample_text = "ἐν ἀρχῇ ἦν ὁ λόγος"  # "In the beginning was the word"

    print("\nAnalyzing Greek text:")
    print(f"Text: {sample_text}")

    lemmatized_text = lemmatizer.lemmatize_text(sample_text)

    print(" ".join(lemmatized_text))

    print("\nGreek lemmatizer workflow completed!")


if __name__ == "__main__":
    main()
