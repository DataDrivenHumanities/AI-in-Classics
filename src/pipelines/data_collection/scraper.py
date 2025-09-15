import os
import re
from pprint import pprint

import numpy as np
import requests
from termcolor import colored, cprint


def parse(urn: str, type: str = "xml", save_dir_path: str = None):
    """
    Parses XML or HTML and optionally saves it to a specified directory. Note that this works for First1KGreek Project only.

    Parameters:
        urn (str): URN of work for XML parsing.
        type (str): Type of file to parse. Defaults to 'xml'.
        save_dir_path (str): Path to directorry to save XML file. If None, no saving is done. Defaults to None.

    Return:
        str - XML or HTML as a string.
    """
    url_base = (
        "https://raw.githubusercontent.com/OpenGreekAndLatin/First1KGreek/cdacf1f80ca7abef67f1cb9a0772556afa87c2b1/data/"
        if type == "xml"
        else "https://github.com/OpenGreekAndLatin/First1KGreek/blob/cdacf1f80ca7abef67f1cb9a0772556afa87c2b1/data/"
    )

    urn_parts = np.asarray(a=re.split(string=urn, pattern=":|\."))
    url = url_base + "/".join(urn_parts[-3:-1]) + f'/{urn.split(":")[-1]}.xml'
    text = requests.get(url=url).text

    if save_dir_path and os.path.exists(path=save_dir_path):
        with open(
            file=f'{save_dir_path}{"".join(urn_parts[-3:])}.{type}', mode="w"
        ) as file:
            file.write(text)

    return text


if __name__ == "__main__":
    pass
    # urn = 'urn:cts:greekLit:ggm0001.ggm001.1st1K-grc1'
    # text = parse(urn=urn, type = 'xml', save_dir_path='.')
    # pprint(text)
