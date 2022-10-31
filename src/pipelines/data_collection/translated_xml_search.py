import os, shutil


def CopyTranslatedXMLs(src: str = "../../../../canonical-greekLit/data/", dest: str = "./translated_xml/", lang: str = "eng"):
    """
    src folder from this repository: https://github.com/PerseusDL/canonical-greekLit
    src and dest folders assume nested folders of format: <src folder>/tlg0020/tlg001/<xml files here>    
    """
    if not os.path.exists(src): 
        print("Error: src directory does not exist:", src)
        return
    if not os.path.exists(dest):
        print("Error: dest directory does not exist:", dest)
        return
    
    skip = ["__cts__.xml", "tracking"]
    
    def ConcatDir(dir: str, subDir: str):
        output = ""
        for item in [dir, subDir]:
            if item[-1] != "/": output += item + "/"
            else: output += item
        return output

    for folder in next(os.walk(src))[1]:
        p1 = ConcatDir(src, folder)
        for subFolder in next(os.walk(p1))[1]:
            p2 = ConcatDir(p1, subFolder)
            langXml = None
            for item in next(os.walk(p2))[2]:
                if (True in [i in item for i in skip]): continue
                if (item[-3:] == "xml"):
                    filenameParts = item.split(".")
                    if (filenameParts[2][-4:-1] == lang):
                        print(item, end=' ')
                        if langXml == None: langXml = item
                        elif (int(item[-5]) > int(langXml[-5])): langXml = item
            if (langXml):
                tempSplit = langXml.split(".")
                tempSplit = tempSplit[0] + "." + tempSplit[1]
                if (langXml in item for item in os.listdir(dest)): print("File already moved")
                else:
                    print("Moved file:", langXml)
                    shutil.copy2(p2 + langXml, dest + langXml)
            else:
                print("No", lang, "file found. No file moved")
    return
