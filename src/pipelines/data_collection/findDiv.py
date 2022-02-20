import xml.etree.ElementTree as ET
import fileinput

# templatePath - template for reference
# temWritePath - file to write to
# filePath - source file
def findDiv (templatePath: str, temWritePath: str, filePath: str):
    # cycles through file
    tree = ET.parse(filePath)
    tTree = ET.parse(templatePath)
    root = tree.getroot()
    ET.register_namespace('', "http://www.tei-c.org/ns/1.0")
    # add non-div elements
    addDescrip(root, tTree)
    # find each div tag here
    findElements(root, tTree, [], False)
    #do this last to save changes
    writeFile(tTree, temWritePath)


def findElements(root: ET.Element, tTree: ET.ElementTree, index: list, isBody: bool = False):
    # do whatever you want with root here
    if (isBody & (root.text is not None)):
        if (len(set(root.text) - {" ", "\n","\t"}) > 0): # if text contains letters other than tab or space
            writePath(tTree, index, root.text)
    
    if (root.tag == '{http://www.tei-c.org/ns/1.0}body'):
        isBody = True
    # recurse
    children = list(root)
    if (len(children) == 0): return  #base case
    i = 0
    for child in children:
        index.append(i)
        findElements(child, tTree, index, isBody)
        index.pop()
        i += 1


def writePath (tTree: ET.ElementTree, index: list, bodyText: str):
    # get string of index
    strings = [str(i) for i in index]
    strIndex = ''.join(strings)
    # write the Xpath to file
    tRoot = tTree.getroot()
    child = ET.Element('div', {'n': strIndex}) # create new div element
    # tRoot[1][0] is location of <body> in file
    tRoot[1][0].append(child)
    child.text = '\n\t\t' + bodyText + '\n\t\t'
    child.tail = "\n\t\t"


def addDescrip(root: ET.Element, tTree: ET.ElementTree):
    #author
    author = "error: no author"
    for authors in root.iter('{http://www.tei-c.org/ns/1.0}author'):
        author = authors.text
        break  # gets first author only
    if (author == "error: no author"):
        print("author:",author)
        return 1
    # title
    title = "error: no title"
    titleTag = "error: no lang"
    for titles in root.iter('{http://www.tei-c.org/ns/1.0}title'):
        title = titles.text
        titleTag = titles.attrib
        break  # gets first author only
    if (title == "error: no title"):
        print("title:",title)
        return 1
    # save variables into tree
    writeDescrip(tTree, author, title, titleTag)

def writeDescrip(tTree: ET.ElementTree, t_author: str = "Unnamed", t_title: str = "Unknown", titleTag: str = ""):
    # add author title
    tRoot = tTree.getroot()
    tRoot[0][0].text = t_title
    tRoot[0][0].attrib = titleTag
    tRoot[0][1].text = t_author


def writeFile(tTree: ET.ElementTree, temWritePath: str):
    # write the tree to the template file
    tTree.write(temWritePath)

    line = '<?xml version="1.0" encoding="UTF-8"?>\n<?xml-model href="http://www.stoa.org/epidoc/schema/latest/tei-epidoc.rng" schematypens="http://relaxng.org/ns/structure/1.0"?>'
    with open(temWritePath, 'r+') as f:
        content = f.read()
        f.seek(0, 0)
        f.write(line.rstrip('\r\n') + '\n' + content)

findDiv(templatePath= "template.xml", temWritePath= "C://Users//morga//source//repos//Research//TestTemplate1.xml", filePath= "C:\\Users\\morga\\source\\repos\\Research\\Test2.xml")