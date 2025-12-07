# word to readble string
import csv
import xml.etree.ElementTree as ET


def rowNameToReadableString(filename):
    # command line funciont that converts index
    # into human words, for example book 1 chapter 3
    filename = filename.replace("Data/", "")
    filename = filename.replace(",", "")
    filename = filename.replace("_clean", "")
    filename = filename.split("xml")
    filename[0] = filename[0] + "xml"
    print("XML:", filename[0])
    indices = map(int, filename[1].split("-"))
    tree = ET.parse(filename[0])
    root = tree.getroot()
    # find specific node and print out tags
    prevBranch = root
    body = 0
    for index in indices:
        branch = prevBranch[index]
        if body > 0:  # start printing tags 2 lines after body starts
            if body > 2:
                printTag(branch.attrib)
            else:
                body = body + 1
        elif branch.tag.find("body"):
            body = 1
        prevBranch = branch


def printTag(tags: dict):
    # print only the values of the tags
    for values in tags.values():
        if values != "textpart":
            print(values, end=" ")
    print("")


def wordToReadableString(word, xml, csvfile):
    with open(csvfile, "r") as csvfile:
        csvreader = csv.reader(csvfile)
        # This skips the first row of the CSV file.
        next(csvreader)
        for row in csvreader:
            if (row[0].replace("_clean", "")).find(xml) != -1:
                if row[1].find(word) != -1:
                    rowNameToReadableString(row[0])


def indexToCleanedXMLDict(xmlFolder: str = "./cleaned_xml/"):
    # Point xmlFolder to cleaned_xml folder
    if xmlFolder[-1] != "/":
        xmlFolder = xmlFolder + "/"
    indexXmlDict = {}
    i = 0
    fileList = os.listdir(xmlFolder)
    fileList.sort()
    for file in fileList:
        # Comment below replaces _cleaned.xml to have only the unique part of the xml filename
        # i.e abc123 instead of abc123_cleaned.xml
        # file = file.replace("_cleaned.xml", "")
        indexXmlDict[i] = xmlFolder + file
        i += 1
    return indexXmlDict
