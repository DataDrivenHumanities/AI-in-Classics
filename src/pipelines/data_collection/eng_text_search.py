import csv, os
import xml.etree.ElementTree as ET
from io import BytesIO

"""
Run this from directory containing /original_xml/ and /translated_xml/ sub-directories
Moving to a different folder will likely require some changes to navigate the directories correctly.
Most likely changes could be made to the function default values

Directory structure used during coding for reference:
data_collection <- This code run from this directory
    |- original_xml
    |   |- Part1
    |   |- Part2
    |   |- Part3
    |   |- Part4
    |- translated_xml <- English xmls from perseus
    |- csvTextPartsWithTitleAndAuthor.csv
    |- This file (currently eng_text_search.py)
    |- The output csv file will also be created here
"""


def CreateOriginalXMLDict(ogFolder: str = "./original_xml/"):
    """
    Creates dict for navigating xml directory with nested directories,
    such as that found in original_xml.zip.
    Returned dict looks like:
    dictOut = {
        <xml file> : <path to xml file (ex. "./original_xml/Part1/")>,
        ...
    }
    """
    dictOut = {}
    for subDir in os.listdir(ogFolder):
        subDirPath = os.path.join(ogFolder, subDir, "")
        for file in os.listdir(subDirPath):
            #file = file.replace(".xml", "")
            dictOut[file] = subDirPath
    return dictOut


def rowNameToReadableString(filename, src: str = ""):
    """
    Function that converts number index into human words
    in a list of dicts
    Ex. "1-0-0-1-2" returns 
    targetList = [
        {'div' : {'textpart': 'chapter', 'n': 1}}
        {'div': {'textpart': 'section', 'n': 2}}
    ]
    """
    filename = filename.replace("Data/", "")
    filename = filename.replace(",","")
    filename = filename.replace("_clean", "")
    filename = filename.split("xml")
    filename[0] = filename[0] + "xml"
    #print("XML:", filename[0], filename[1])
    indices = map(int, filename[1].split('-'))
    src = CreateOriginalXMLDict()[filename[0]] if src == "" else src
    tree = ET.parse(src + filename[0])
    root = tree.getroot()
    # find specific node and print out tags
    prevBranch = root
    body = 0
    targetList = []
    for index in indices:
        branch = prevBranch[index]
        if (body > 0): # start printing tags 2 lines after body starts
            if (body > 2):
                temp = printTag(branch)
                if temp != None:
                    targetList.append(temp)
            else:
                body = body + 1
        elif (branch.tag.find("body")):
            body = 1
        prevBranch = branch
    #print("")
    #print("Target List:",targetList)
    #print(list(targetList[0].values())[0].values(), len(list(targetList[0].values())[0].values()))
    while (len(list(targetList[0].values())[0].values()) == 0):
        targetList.pop(0)
        if len(targetList) == 0: break
    return targetList


def printTag(branch: ET.Element):
    """
    Helper function of rowNameToReadableString.
    Pulls element attribute keys and values from element
    """
    tags = branch.attrib
    dictOut = {}
    tag = branch.tag.split("}")[-1]
    dictOut[tag] = {}
    temp = ""
    for key, value in tags.items():
        if (value != 'textpart'):
            dictOut[tag][key] = value
            temp += value + " "
            #print(value, end=' ')
    #print('')
    return dictOut if len(dictOut) > 0 else None

def ElemText(elemIn: ET.Element, addSkipList: str = []):
    """
    Parses element for text. Is able to nested elements using iterparse
    Use skipList for elements where text is not desired.
    """
    for item in addSkipList: skipList.append(item)
    if elemIn == None: return None
    skipList = [
        'note',
        'pb',
    ]
    textOut = ""
    # elemElems tracks when an element from skipList is entered and exited
    elemElems = []
    for event, elem in ET.iterparse(BytesIO(ET.tostring(elemIn)), events=('start', 'end',)):
        tag = elem.tag.split("}")[-1]
        if tag in skipList:
            if event == 'start' and tag in skipList:
                elemElems.append(True)
            elif event == 'end' and tag in skipList:
                elemElems.pop(-1)
                if len(elemElems) == 0 and elem.tail != None:
                    textOut = textOut + elem.tail
        else:
            if event == 'start' and len(elemElems) == 0 and elem.text != None:
                textOut = textOut + elem.text
            elif event == 'end' and len(elemElems) == 0 and elem.tail != None:
                textOut = textOut + elem.tail
    textOut = None if textOut == "" else textOut
    return textOut

def FindEngElem(elemList: list = [], element: ET.Element = None, IOI: ET.Element = None):
    """
    Given an elemList (from rowNameToReadableString), navigate
    the english xml and find the equivalent element.
    Function is recursive, "digging" down the xml tree.
    As it finds each element it calls itself again with
    a modified elemList (elemList[1:]).

    IOI is Item of Interest. It's used to track previous elements
    that may contain the desired text. This happens when a given ancient
    greek text has element attributes such as n = 1, 2, 3, etc
    but the english text combines n's to n = 1, 5, 10, etc.
    TODO Is there a consistent way to separate the combined n text?
    """
    def _cleanattribs(attribDict):
        """removes unwanted attributes"""
        cleanList = [
            "rend",
        ]
        for word in cleanList:
            if word in attribDict: attribDict.pop(word)
        return attribDict
    def _keycheck(d1, d2):
        """compares keys of 2 elements"""
        for key in d1:
            if key not in d2.keys():
                return False
        return True
    def _valuecheck(d1, d2):
        """compares values of 2 elements"""
        for key, val in d1.items():
            if d2[key] != val:
                return False
        return True
    
    for event, elem in ET.iterparse(BytesIO(ET.tostring(element)), events=('start',)):#, 'end')):
        if list(elemList[0].keys())[0] != elem.tag.split("}")[-1]:
            continue
        cleanedAttribs = _cleanattribs(elem.attrib)
        elemTarget = list(elemList[0].values())[0]
        if _keycheck(elemTarget, cleanedAttribs):
            if _valuecheck(elemTarget, cleanedAttribs):
                if len(elemList) == 1:
                    theText = ElemText(elem)
                    return [theText, None, False]
                else:
                    try:
                        dig = FindEngElem(elemList[1:], elem, IOI=IOI)
                    except ET.ParseError:
                        dig = [None, IOI, False]
                    if dig[0] != None: return dig
                    else: IOI = dig[1]
            elif 'n' in cleanedAttribs.keys() and 'n' in elemTarget and len(elemList) == 1:
                if cleanedAttribs['n'].isdigit() and elemTarget['n'].isdigit():
                    thisN = int(cleanedAttribs['n'])
                    targetN = int(elemTarget['n'])
                    if thisN < targetN:
                        IOI = elem
                    elif thisN > targetN:
                        theText = ElemText(IOI)
                        return [theText, None, True]
    """
    returns [text, IOI, status]
    status is a boolean that is supposed to indicate whether
    the returned text is a combined english element
    (containing n = 1 thru n = 5 for example),
    but it doesn't work consistently.
    """
    return [None, IOI, False]

def CompileEngXmls():
    """
    Creates a list of all english tranlation xmls.
    Some english xmls are commentary and do not contain translation of the actual text
    """
    ogXmlDict = CreateOriginalXMLDict()
    listOut = []
    for item in ogXmlDict.keys():
        if "eng" not in item: continue
        xmlPath = os.path.join(ogXmlDict[item], item)
        tree = ET.parse(xmlPath)
        root = tree.getroot()
        targetElem = root[1][0][0]
        xmlType = targetElem.attrib['type'] if 'type' in targetElem.attrib else ""
        #print(xmlType, item)
        if xmlType == "translation":
            listOut.append(item)
    
    translatedXmlDir = os.listdir("./translated_xml/")
    for item in translatedXmlDir:
        if "eng" not in item: continue
        xmlPath = os.path.join("./translated_xml/", item)
        try:
            tree = ET.parse(xmlPath)
            root = tree.getroot()
            targetElem = root[1][0][0]
            xmlType = targetElem.attrib['type'] if 'type' in targetElem.attrib else ""
            #print(xmlType, item)
            if xmlType == "translation":
                listOut.append(item)
        except: continue
    return listOut

def OgFileCheck(fileIn):
    """
    Used on the og file (ancient greek, latin xml)
    Some of the xmls are commentary. Those are just commentary of
    the equivalent text, often with multiple languages. 
    To make writing this code easier, it was limited to working
    with xmls that were of the types found in okList below. This info
    was found in the first element within body element of xml
    """
    okList = ["edition", "translation"]
    srcTree = ET.parse(fileIn)
    srcDesc = srcTree.getroot()[1][0][0]
    srcType = srcDesc.attrib['type'] if 'type' in srcDesc.attrib else "TYPENOTFOUND"
    if srcType not in okList: return False
    return True

def CreateCsvWithEngText():
    """
    This was used to create csvTextPartsWithTitleAuthorAndEng.csv
    It itereates through the csv and creates a new csv with column for english text
    Comments below to help describe steps
    """
    # dict and list used throughout
    ogXmlDict = CreateOriginalXMLDict()
    allEngXmls = CompileEngXmls()

    count = 1
    # noEngXml tracks which xmls don't have an english version, so it can be skipped
    noEngXml = []
    # tracks which xmls have already been seen
    processedXmls = []

    with open('./temp.csv', 'w', newline='', encoding='UTF8') as newCsv:
        fieldnames = ['', 'Section ID', 'Text Section', 'Title', 'Author', 'Translated Text']
        writer = csv.DictWriter(newCsv, fieldnames=fieldnames)
        writer.writeheader()
        with open("./csvTextPartsWithTitleAndAuthor.csv", newline='') as csvIn:
            reader = csv.DictReader(csvIn, delimiter=',')
            for row in reader:
                # count is just to have something in the terminal showing progress
                count += 1
                if (count % 10000) == 0: print(int(count/10000), end=' ', flush=True)
                fileAndIndex = row["Section ID"]
                fileAndIndex = fileAndIndex.replace("Data/","").replace(",","").replace("_clean","")
                filename = fileAndIndex.split("xml")[0]
                ogFile = os.path.join(ogXmlDict[filename+'xml'], filename+'xml')
                if filename in noEngXml:
                    # xml already seen and has no english xml. 
                    # Write None for Translated Text
                    writer.writerow({'':row[''], 'Section ID': row["Section ID"],
                    'Text Section': row['Text Section'], 'Title': row['Title'],
                    'Author': row['Author'],'Translated Text': "None"})
                    continue
                p1 = filename[0:7]
                p2 = filename[7:13]
                foundEngXml = False
                engXml = [i for i in allEngXmls if ((p1 + p2 in i) or (p1+"."+p2 in i))]
                if len(engXml) == 0:
                    # Searched for english xml, none found.
                    noEngXml.append(filename)
                    # Write None for Translated Text
                    writer.writerow({'':row[''], 'Section ID': row["Section ID"],
                    'Text Section': row['Text Section'], 'Title': row['Title'],
                    'Author': row['Author'],'Translated Text': "None"})
                    continue
                if filename not in processedXmls:
                    if not OgFileCheck(ogFile):
                        noEngXml.append(filename)
                        # Write None for Translated Text
                        writer.writerow({'':row[''], 'Section ID': row["Section ID"],
                        'Text Section': row['Text Section'], 'Title': row['Title'],
                        'Author': row['Author'],'Translated Text': "None"})
                        processedXmls.append(filename)
                        continue
                engXml = engXml[0]
                engTree = None
                # Grab the english xml from whichever place contains it
                # ./original_xml via ogXmlDict or ./translated_xml
                if engXml in ogXmlDict.keys():
                    tempPath = os.path.join(ogXmlDict[engXml], engXml)
                    engTree = ET.parse(tempPath)
                else: engTree = ET.parse("./translated_xml/" + engXml)
                # given the if-else above, engTree should never == None
                # Left it in because it wasn't not high priority to modify
                if engTree == None: print("ERROR!!")
                # Get the list of dicts containing element location
                theList = rowNameToReadableString(row["Section ID"])
                # Ensuring the returned list is not empty
                # An empty list means there's nothing to work with
                notEmptyList = False
                if len(theList) == 0: notEmptyList = False
                else:
                    for subDict in theList:
                        for val in subDict.values():
                            if val: notEmptyList = True
                    """
                    elemSkipList elements usually had minimal attributes
                    and, as a result, often returned the wrong text. 
                    Skipped these elements since it was easier. Would have
                    to find where it sits in reference to other elements in
                    order to accurately locate. This code doesn't do that.
                    """
                    elemSkipList = ["speaker", "foreign",]
                    for item in elemSkipList:
                        if item in theList[-1]: notEmptyList = False
                if notEmptyList:
                    
                    findEngElemRes = FindEngElem(theList, engTree.getroot()[1][0][0])
                    transText = "None"
                    if findEngElemRes[0] != None: transText = findEngElemRes[0]
                    # If there is no returned text, but there is an IOI, get IOI text
                    elif findEngElemRes[1] != None: transText = ElemText(findEngElemRes[1])
                    writer.writerow({'':row[''], 'Section ID': row["Section ID"],
                    'Text Section': row['Text Section'], 'Title': row['Title'],
                    'Author': row['Author'],'Translated Text': transText})
                else:
                    # Write None for Translated Text
                    writer.writerow({'':row[''], 'Section ID': row["Section ID"],
                    'Text Section': row['Text Section'], 'Title': row['Title'],
                    'Author': row['Author'],'Translated Text': "None"})
                processedXmls.append(filename)

def EngTextSearch(fileAndIndex: str = None):
    """
    This is for single inputs.
    Given an xml and index, return english text if it exists
    Returns Text or None
    Provide ancient greek/latin xml and index
    fileAndIndex format assumed similar to what is found in the csv's,
    which is cleaned file immediately followed by index
    Format: Data/tlg####tlg###...xml#-#-#-# Ex: Data/tlg0085tlg007opp-grc3_clean.xml1-0-0-2-6-5
    Should be run in same directory where original_xml and translated_xml directories are located
    """
    
    if fileAndIndex == None: return None
    # If CompileEngXmls() or CreateOriginalXMLDict()
    # don't work, there's no english text to search
    try: ogXmlDict = CreateOriginalXMLDict()
    except: return None
    try: allEngXmls = CompileEngXmls()
    except: return None
    fileAndIndex = fileAndIndex.replace("Data/","").replace(",","").replace("_clean","")
    filename = fileAndIndex.split("xml")[0]
    ogFile = os.path.join(ogXmlDict[filename+'xml'], filename+'xml')

    if not OgFileCheck(ogFile): return None
    p1 = filename[0:7]
    p2 = filename[7:13]
    engXml = [i for i in allEngXmls if ((p1 + p2 in i) or (p1+"."+p2 in i))]
    if len(engXml) == 0: return None
    engXml = engXml[0]
    engTree = None
    if engXml in ogXmlDict.keys():
        tempPath = os.path.join(ogXmlDict[engXml], engXml)
        engTree = ET.parse(tempPath)
    else: engTree = ET.parse("./translated_xml/" + engXml)
    if engTree == None: return None
    theList = rowNameToReadableString(fileAndIndex)
    
    notEmptyList = False
    if len(theList) == 0: notEmptyList = False
    else:
        for subDict in theList:
            for val in subDict.values():
                if val: notEmptyList = True
        elemSkipList = ["speaker", "foreign",]
        for item in elemSkipList:
            if item in theList[-1]: notEmptyList = False
    if not notEmptyList: return None
    findEngElemRes = FindEngElem(theList, engTree.getroot()[1][0][0])
    transText = None
    if findEngElemRes[0] != None: transText = findEngElemRes[0]
    elif findEngElemRes[1] != None: transText = ElemText(findEngElemRes[1])
    return transText


if __name__ == '__main__':
    pass
    #CreateCsvWithEngText()
"""
    # Testing EngTextSearch
    with open("./csvTextPartsWithTitleAuthorAndEng.csv", newline='') as csvIn:
        reader = csv.DictReader(csvIn, delimiter=',')
        for row in reader:
            if row['Translated Text'] != "None":
                print(row[""], row['Translated Text'])
                print("this", EngTextSearch(row["Section ID"]))
                input("Continue?")"""

