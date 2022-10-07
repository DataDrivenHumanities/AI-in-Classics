import multiprocessing as mp
import numpy as np
import pickle
import tqdm

from pprint import pprint

vectorizer=pickle.load(file=open(file='../text_analytics/vectorizer.pkl',mode='rb'))['vectorizer']
pprint(vectorizer)

dtm=np.load(file='../text_analytics/DocumentTermMatrix.npy')
pprint(dtm)
pprint(dtm.shape)

inverted_index=dict()

terms_per_doc=vectorizer.inverse_transform(X=dtm)
pprint(terms_per_doc[0])

for doc_idx, terms in tqdm.tqdm(enumerate(terms_per_doc)):
	for term in terms:
		if term not in inverted_index:
			inverted_index[term]=set()
		inverted_index[term].add(doc_idx)

pprint(inverted_index)

pickle.dump(obj=inverted_index, file=open(file='inverted_index.pkl', mode='wb'))