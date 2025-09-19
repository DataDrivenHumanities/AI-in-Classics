import os

import findDiv
from numpy import unsignedinteger


def runDiv(
    templatePath: str, cleanFolder: str, ogFolder: str, limit: unsignedinteger = -1
):
    """templatePath - template for reference
    cleanFolder - folder to write to
    ogFolder - source files
    limit - max number of files to convert (optional)"""
    i = 0
    for filename in os.listdir(ogFolder):
        f = os.path.join(ogFolder, filename)
        # check if file within specified limit
        if os.path.isfile(f) & (i < limit):
            # checks that the files are in the correct language
            if (f[-8:-5] in {"grc", "lat", "mul"}) | (
                f[-9:-6] in {"grc", "lat", "mul"}
            ):
                print(f)
                cleanPath = filename[0:-4] + "_clean.xml"
                cleanPath = os.path.join(cleanFolder, cleanPath)
                file = open(cleanPath, "w")
                findDiv.findDiv(
                    templatePath=templatePath, temWritePath=cleanPath, filePath=f
                )
                i += 1


runDiv(
    templatePath="template.xml",
    cleanFolder="C:/Users/morga/source/repos/Research/cleaned_XML",
    ogFolder="C:/Users/morga/source/repos/Research/original_xml/Part1",
    limit=10,
)
