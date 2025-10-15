import os
import re
import numpy as np

def clean_xml(directory_path, save_path):
    for filename in os.listdir(directory_path):
        # check to make sure that the given file is a Greek XML
        if not re.fullmatch(".*\.xml", filename) or not re.search("-grc.*\.xml", filename):
            continue
        filepath = directory_path + "/" + filename
        author = ""
        title = ""
        text = ""
        metadata = ""
        with open(filepath) as file:
            
            # find <text> section, start point for text extraction
            # remove all tags, maintain some information as metadata such as <pb> tags which indicate pagebreak

    return

if __name__ == "__main__":
    parent = "./original_xml"
    directory = "script_test"
    path = parent + "/" + directory

    output_path = "./cleaned_xml"
    if path == "./original_xml/script_test":
        clean_xml(path, output_path)
        print(f"{directory} cleaning complete.")
    else:
        for d in os.walk(path):
            sub = d[0]
            clean_xml(sub, output_path)
            print(f"{sub} parsing complete.")
    print("Cleaning of non-Greek XML files is complete.")