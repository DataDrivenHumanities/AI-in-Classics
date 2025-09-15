import csv
import os
import sys
import timeit
import xml.etree.ElementTree as ET


def rowNameToReadableString(filename):
    # command line funcion that converts index
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
    title = root[0][0][0][0].text
    print("Title:", title)
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
    print()


def wordToReadableString(word, xml, csvfile):
    with open(csvfile, "r") as csvfile:
        csvreader = csv.reader(csvfile)
        # This skips the first row of the CSV file.
        next(csvreader)
        for row in csvreader:
            if (row[0].replace("_clean", "")).find(xml) != -1:
                if row[1].find(word) != -1:
                    rowNameToReadableString(row[0])
                    print("---------------")


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
        file = file.replace(xmlFolder, "")
        indexXmlDict[i] = file
        i += 1
    return indexXmlDict


def wordSearch(word, folderOfXmls, csv, txtFile=False, txtFileName=""):
    start = timeit.default_timer()
    _, _, files = next(os.walk(folderOfXmls))
    file_count = len(files)
    Dict = indexToCleanedXMLDict(folderOfXmls)
    if txtFile:
        with open(txtFileName, "w") as sys.stdout:
            print("test")
            for i in range(0, file_count):
                wordToReadableString(word, Dict[i], csv)
            print("All Matches printed.")
            stop = timeit.default_timer()
            print("Time: ", stop - start)
    else:
        for i in range(0, file_count):
            wordToReadableString(word, Dict[i], csv)
        print("All Matches printed.")
        stop = timeit.default_timer()
        print("Time: ", stop - start)
