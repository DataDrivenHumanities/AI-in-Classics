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


rowNameToReadableString("Data/tlg0015tlg001opp-grc1_clean.xml1-0-0-4-7-7-0,")
