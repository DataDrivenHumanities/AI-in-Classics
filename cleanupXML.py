import os
import re
from pprint import pprint

import numpy as np
import requests
from termcolor import colored, cprint


def cleanup_XML(urn: str, save_raw_path: str = None, save_clean_path: str = None):
    """
    Parses XML and optionally saves it to a specified directory. Note that this works for First1KGreek Proejct only.

    Parameters:
        urn (str): URN of work for XML parsing.
        save_raw_path (str): Path to directorry to save XML file. If None, no saving is done. Defaults to None. Does before cleanup
        save_clean_path (str)


    Return:
        str - XML as a string.
    """
    url_base = "https://github.com/OpenGreekAndLatin/First1KGreek/blob/cdacf1f80ca7abef67f1cb9a0772556afa87c2b1/data/"
    urn_parts = np.asarray(a=re.split(string=urn, pattern=":|\."))
    url = url_base + "/".join(urn_parts[-3:-1]) + f'/{urn.split(":")[-1]}.xml'
    xml_text = requests.get(url=url).text
    """""
    Save raw xml into a file path 
    """ ""
    if save_raw_path and os.path.exists(path=save_raw_path):
        with open(file=f'{"".join(urn_parts[-3:])}.xml', mode="w") as file:
            file.write(xml_text)
    """
    Cleaning up the data
    """
    # Declaring variables
    author = ""
    title = ""
    text = ""
    # Find title, author, and text in the XML file and add to variables
    if xml_text.find("<author") != -1:
        start = xml_text.find("<author")
        end = (
            xml_text.find("</author>") + 9
        )  # to grab until after </author>. < only in case lang or something in title
        author = xml_text.substring(start, end)
    if xml_text.find("<title") != -1:
        start = xml_text.find("<title")
        end = xml_text.find("</title>") + 9
        title = xml_text.substring(start, end)
    if xml_text.find("<text") != -1:
        start = xml_text.find("<text")
        end = xml_text.find("</text>") + 7
        text = xml_text.substring(start, end)
    # make the new file
    xml_new_text = '<?xml version="1.0" encoding="UTF-8"?> \n '
    # need to add TEI formatting to the file still
    xml_new_text += "\t" + title + "\n \t" + author + "\n \t" + text
    # works if code has things saved as <title> <author> and <text>
    """
    Save new data into a new file path
    """
    if save_clean_path and os.path.exists(path=save_clean_path):
        with open(file=f'{"".join(urn_parts[-3:])}.xml', mode="w") as file:
            file.write(xml_new_text)
    return xml_new_text


if __name__ == "__main__":
    urn = "urn:cts:greekLit:ggm0001.ggm001.1st1K-grc1"
    xml_text = cleanup_XML(urn=urn, save_raw_path=".", save_clean_path=".")
    pprint(xml_text)
