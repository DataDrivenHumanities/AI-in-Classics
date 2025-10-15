import os
import re
import xml.etree.ElementTree as ET
import numpy as np

def strip_namespace(tag):
    """
    Strips namespace from the xml tags to improve parsing ability
    Args:
        tag: xml tag to be parsed

    Returns:
        cleaned tag without the namespace denotation
    """
    return tag.split('}', 1)[-1] if '}' in tag else tag

def get_save_path(save_directory, filename):
    """
    get_save_path generates the full file path for the new text file
    Args:
        save_directory: directory to which the new text files should be saved
        filename: name of the file to which the new text should be stored

    Returns:
        string file path for the new text file
    """
    return save_directory + "/" + filename[:-3] + "txt"

def get_all_xml_text(file_path):
    """
    get_all_xml_text pulls relevant metadata and text from a xml file, returning the text string and mutating the
    author_title list and metadata list as needed.
    Args:
        file_path: string file path of xml file

    Returns:
        full text body as a string, author as a string, title as a string, metadata as a list
    """
    try:
        tree = ET.parse(file_path)
        root = tree.getroot()

        in_text = False

        all_text = []
        author = ""
        title = ""
        metadata = []
        for element in root.iter():  # iterate through xml tree starting at the root
            tag = strip_namespace(element.tag)
            if tag == 'author':
                author = element.text
            elif tag == 'title':
                title = element.text
            elif tag == 'text':  # boolean to determine when the actual text body has started
                in_text = True
            elif tag == 'head':  # can add more tag searches to add more metadata as needed
                metadata.append(f"Head: {element.text}")

            if in_text and element.text:
                all_text.append(element.text.strip())
        return " ".join(all_text), author, title, metadata
    except FileNotFoundError:
        return "Error: XML file not found"
    except ET.ParseError as e:
        return f"Error parsing XML: {e}"

def clean_xml(directory_path, save_directory):
    """
    clean_xml iterates through the given directory, identifies greek xml files, and extracts xml text into a string
    by calling get_all_xml_text. clean_xml then saves this text as a txt file to the save_directory, using the original filename.
    Args:
        directory_path: directory hosting the xml corpus
        save_directory: directory where txt files are saved

    Returns:
        string value identifying that all xml files have been parsed

    """
    for filename in os.listdir(directory_path):
        # check to make sure that the given file is a Greek XML
        if not re.fullmatch(".*\.xml", filename) or not re.search("-grc.*\.xml", filename):
            continue
        file_path = directory_path + "/" + filename

        xml_text, author, title, metadata = get_all_xml_text(file_path)

        save_path = get_save_path(save_directory, filename)
        with open(save_path, "w", encoding="utf-8") as f:
            f.write(xml_text)
    return "All xml files parsed"

if __name__ == "__main__":
    parent = "./original_xml"
    test_path = parent + "/script_test"
    test_mode = False

    output_path = "./cleaned_xml"
    if test_mode:
        output = clean_xml(test_path, output_path)
        print(f"script_test xml parsing complete.")
        print(output)
    else:
        for d in os.walk(parent):  # walk through parent directory, skips test path, executes clean_xml on all other directories
            sub = d[0]
            if sub == test_path:
                continue
            clean_xml(sub, output_path)
            print(f"{sub} xml parsing complete.")
    print("Text extraction from Greek XML files is complete.")