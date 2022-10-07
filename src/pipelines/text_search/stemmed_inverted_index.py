import json
import pickle
import tqdm

from typing import Dict, Iterable
from pprint import pprint
from cltk.stem.lat import stem as latin_stem

class InvertedIndexJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, set):
                return list(obj)
        return self.default(obj=obj)

def inverted_index_to_stemmed_inverted_index(inverted_index: Dict[str, Iterable]) -> Dict[str, Dict[str, Iterable]]:
    stemmed_inverted_index=dict()
    for inflected_term in tqdm.tqdm(iterable=inverted_index):
        stem=latin_stem(word=inflected_term)
        if stem not in stemmed_inverted_index:
                stemmed_inverted_index[stem]=dict()
        stemmed_inverted_index[stem] = stemmed_inverted_index[stem] | {inflected_term : inverted_index[inflected_term]}
    return stemmed_inverted_index

def stemmed_inverted_index_to_json(stemmed_inverted_index: Dict[str, Dict[str, Iterable]], save: bool=False) -> str:
    stemmed_inverted_index_str=json.dumps(obj=stemmed_inverted_index, cls=InvertedIndexJSONEncoder)
    if save:
        with open(file='stemmed_inverted_index.json', mode='w') as jsonfile:
            jsonfile.write(stemmed_inverted_index_str)
    return stemmed_inverted_index_str

inverted_index=pickle.load(file=open(file='inverted_index.pkl', mode='rb'))

stemmed_inverted_index=None
try:
    stemmed_inverted_index=pickle.load(file=open(file='stemmed_inverted_index.pkl', mode='rb'))
except:
    stemmed_inverted_index=inverted_index_to_stemmed_inverted_index(inverted_index)
    pickle.dump(obj=stemmed_inverted_index, file=open(file='stemmed_inverted_index.pkl', mode='wb'))
pprint(stemmed_inverted_index)

# stemmed_inverted_index_str=None
# try:
#     stemmed_inverted_index_str=open(file='stemmed_inverted_index.json', mode='w').read()
# except:
#     stemmed_inverted_index_str=stemmed_inverted_index_to_json(stemmed_inverted_index=stemmed_inverted_index, save=True)
# pprint(stemmed_inverted_index_str)