"""
This script lemmatizes text file input from files located at <root>/data/greek/raw_text_from_xml in the root directory.
raw_text_from_xml should contain a series of text files that have been cleaned of xml or non-Greek text.
See the clean_xml.py script in the root directory for correct text output compatible with this script.

Output of this script is lemmatized text stored in like-named documents within <root>/data/greek/lemmatized_text
Lemmatized text can be pre-processed and passed through a tokenizer for usage in training a Hugging Face model.
"""

import os
import csv

from GreekCLTKLemmatizer import GreekCLTKLemmatizer

def main():
    lemmatizer = GreekCLTKLemmatizer()  # instantiate Lemmatizer

    corpus_directory = "../../data/greek/raw_text_from_xml"  # location of text files based on xml data
    output_dir = "../../data/greek/lemmatized_csv"
    csv_filename = "lemmatized_sentences.csv"

    sentence_list = [["sentence"]]

    for f in os.listdir(corpus_directory):  # iterate through corpus directory
        if not str(f).endswith(".txt"):
            continue
        print(f"Starting lemmatization of {f}")
        file_path = corpus_directory + "/" + f

        # for each file, open file, conduct word-by-word lemmatization
        with open(file_path, "r", encoding="utf-8") as file:
            try:
                content = file.read()
            except Exception as err:
                print(err)
            lemmatized_text = lemmatizer.lemmatize_text(content)
            if len(lemmatized_text) == 1 and lemmatized_text[0] == '':
                continue
            sentence_list.append(lemmatized_text)

    try:
        os.mkdir(output_dir)
    except FileExistsError:
        print(f"Directory '{output_dir}' already exists.")

    flattened_sentences = []
    for item in sentence_list:
        if isinstance(item, list):
            for s in item:
                if s.strip():
                    flattened_sentences.append(s.strip())
        elif isinstance(item, str) and item.strip():
            flattened_sentences.append(item.strip())

    new_file_path = os.path.join(output_dir, csv_filename)
    with open(new_file_path, "w", encoding="utf-8", newline='') as csv_file:
        writer = csv.writer(csv_file)
        for s in flattened_sentences:
            writer.writerow([s])
    print("Completed lemmatization of Greek corpus")

if __name__ == "__main__":
    main()