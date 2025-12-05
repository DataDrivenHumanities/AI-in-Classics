"""
This script lemmatizes text file input from files located at <root>/data/greek/raw_text_from_xml in the root directory.
raw_text_from_xml should contain a series of text files that have been cleaned of xml or non-Greek text.
See the clean_xml.py script in the root directory for correct text output compatible with this script.

Output of this script is lemmatized text stored in like-named documents within <root>/data/greek/lemmatized_text
Lemmatized text can be pre-processed and passed through a tokenizer for usage in training a Hugging Face model.
"""

import os
import re

from run_greek_lemmatizer import GreekLemmatizer

def main():
    lemmatizer = GreekLemmatizer()  # instantiate Lemmatizer

    corpus_directory = "../../data/greek/raw_text_from_xml"  # location of text files based on xml data
    for f in os.listdir(corpus_directory):  # iterate through corpus directory
        print(f"Starting lemmatization of {f}")
        file_path = corpus_directory + "/" + f
        lemmatized_text = ""
        # for each file, open file, conduct word-by-word lemmatization
        with open(file_path, "r", encoding="utf-8") as file:
            try:
                content = re.split(r"(\s+)", file.read())
            except Exception as err:
                print(err)
            for token in content:
                if token.isspace():
                    lemmatized_text += token
                    continue
                res = lemmatizer.lemmatize(token)
                if len(res) > 0:
                    if res[0]["lemma"] != "nan":
                        lemmatized_text += res[0]["lemma"]
                    else:
                        lemmatized_text += token.lower()
                else:
                    continue
        output_dir = "../../data/greek/lemmatized_text"
        new_file_path = os.path.join(output_dir, f)
        with open(new_file_path, "w", encoding="utf-8") as new_file:
            new_file.write(lemmatized_text)
    print("Completed lemmatization of Greek corpus")

if __name__ == "__main__":
    main()