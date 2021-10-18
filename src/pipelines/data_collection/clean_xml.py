from pyquery import PyQuery as pq
from pprint import pprint
from termcolor import colored, cprint

# global variables
line_color = 'green'

def clean(path: str):
    """
    Cleans XML file of unneeded tags by extracting only needed tags and inserting them into a template.

    Parameters:
        path (str): Path to XML file.
    """
    doc = pq(path)
    pprint(doc)

if __name__ == '__main__':
    path = 'ggm0001ggm0011st1K-grc1.xml'
    content = str(open(file=path, mode='rb').read())

    doc = pq(content)
    doc_cleaned = pq(str(open(file='template.xml', mode='r').read()))

    title = doc('title').eq(index=0).text()
    author = doc('author').eq(index=0).text()
    textparts = doc('div').filter(selector=lambda x: pq(this).attr['subtype'] == 'chapter')
    for textpart in textparts:
        cprint(text='-' * 20, color=line_color)
        # pprint(textpart)
        # pprint(type(textpart))
        # pprint(str(textpart))
        txt = pq(textpart).html().encode().decode(encoding='unicode_escape').encode(encoding='raw_unicode_escape').decode()
        doc_cleaned('text').append(value=txt)
        # pprint(txt)

    doc_cleaned('title').append(value=title)
    doc_cleaned('author').append(value=author)
    print(doc_cleaned.html())

    with open(file='cleaned.xml', mode='w') as xml_cleaned:
        xml_cleaned.write(doc_cleaned.html())
    