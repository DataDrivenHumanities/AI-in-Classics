import multiprocessing as mp, numpy as np, os, re, tqdm
from pyquery import PyQuery as pq, text
from termcolor import colored, cprint

# global variables
line_color = 'green'
text_color = 'magenta'

def clean(path: str, save_dir_path: str = './'):
    """
    Cleans XML file of unneeded tags by extracting only needed tags and inserting them into a template.

    Parameters:
        path (str): Path to XML file.
        save_dir_path (str): Path to immediate directory where cleaned XML file is saved. Defaults to current directory.

    Returns:
        None
    """
    # loading and creating PyQuery objects
    content = str(open(file=path, mode='rb').read())
    doc = pq(content)
    doc_cleaned = pq(str(open(file='template.xml', mode='r').read()))

    # loading and saving metadata
    title = doc('title').eq(index=0).text()
    author = doc('author').eq(index=0).text()
    doc_cleaned('title').append(value=title)
    doc_cleaned('author').append(value=author)

    # saving <div> tags based on highest-level subtype
    textparts = doc('div:parent').filter(selector=lambda x: pq(this).attr['type'] == 'textpart')
    subtypes = set([textparts.eq(index=i).attr['subtype'] for i in np.arange(len(textparts))])
    subtype_top_level = sorted(subtypes)[0]
    textparts = textparts.filter(selector=lambda x: pq(this).attr['subtype'] == subtype_top_level)
    for index in np.arange(len(textparts)):
        # cprint(text='-' * 100, color=line_color)
        # print(index)
        textpart = textparts.eq(index=index)
        html_decoded = textpart.html().encode().decode(encoding='unicode_escape').encode(encoding='raw_unicode_escape').decode()
        
        if not html_decoded.startswith('<div'):
            html_decoded = f'\n<div type="textpart" subtype="{subtype_top_level}" n="{index + 1}">\n' + html_decoded
        if not html_decoded.endswith('</div>'):
            html_decoded += '\n</div>\n'
        # print(html_decoded)
        doc_cleaned('text').append(value=html_decoded)

    # deleting interrupting tags based on text from lowest-level subtype
    subtype_bottom_level = sorted(subtypes)[-1]
    textparts = doc_cleaned('div:parent').filter(selector=lambda x: pq(this).attr['subtype'] == subtype_bottom_level).find(selector='p')
    for index in np.arange(len(textparts)):
        # cprint(text='-' * 100, color=line_color)
        # print(index)
        textpart = textparts.eq(index=index)

        # converting bytes to Greek
        txt_without_tags = ' '.join(re.split(pattern='<.*>', string=textpart.text()))
        textpart.replace_with(value=f'\n<p>\n{txt_without_tags}\n</p>\n')

    # verifying and saving cleaned XML file
    os.makedirs(name=save_dir_path, exist_ok=True)
    with open(file=f'{save_dir_path + path.split("/")[-1][:-4]}_cleaned.xml', mode='w') as xml_cleaned:
        xml_cleaned.write(doc_cleaned.html())

def xml_to_text(path: str, save_dir_path: str = './'):
    """
    Extract all content text from an XML file merged together in reading order.

    Parameters:
        path (str): Path to XML file.
        save_dir_path (str): Path to immediate directory where raw text is saved. Defaults to current directory.

    Returns:
        None
    """
    # loading and creating PyQuery objects
    content = str(open(file=path, mode='rb').read())
    doc = pq(content)

    # finding subtype of highest level and fetching all contained texts
    textparts = doc('div:parent').filter(selector=lambda x: pq(this).attr['type'] == 'textpart')
    subtypes = set([textparts.eq(index=i).attr['subtype'] for i in np.arange(len(textparts))])
    subtype_top_level = sorted(subtypes)[0]
    textparts = textparts.filter(selector=lambda x: pq(this).attr['subtype'] == subtype_top_level)
    txt = textparts.text().encode().decode(encoding='unicode_escape').encode(encoding='raw_unicode_escape').decode()

    # saving text file
    os.makedirs(name=save_dir_path, exist_ok=True)
    with open(file=f'{save_dir_path + path.split("/")[-1][:-4]}_text.txt', mode='w') as text_file:
        text_file.write(txt)

if __name__ == '__main__':
    pool = mp.Pool(processes=mp.cpu_count())
    pool.starmap(
        func=clean,
        iterable=tqdm.tqdm(np.asarray(a=list([(f'./original_xml/{xml_name}', './cleaned_xml/') for xml_name in os.listdir(path='./original_xml/')])))
    )

    pool.starmap(
        func=xml_to_text,
        iterable=tqdm.tqdm(np.asarray(a=list([(f'./original_xml/{xml_name}', './full_texts/') for xml_name in os.listdir(path='./original_xml/')])))
    )
