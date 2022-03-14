# primary libraries
import bs4, csv,json, multiprocessing as mp, numpy as np, os, pandas as pd, pickle, re, requests, tqdm
from inspect import signature
from dotenv import load_dotenv
from pprint import pprint
from termcolor import colored, cprint

# CLTK
from cltk.data.fetch import FetchCorpus
from cltk.lemmatize.grc import GreekBackoffLemmatizer
from cltk.alphabet.text_normalization import cltk_normalize

grc_corpus = FetchCorpus(language='grc')
grc_corpus.import_corpus(corpus_name='grc_models_cltk')
lemmatizer = GreekBackoffLemmatizer()

# Machine Learning
from sklearn.feature_extraction.text import CountVectorizer

# app development
import streamlit as st
PREPROCESSED_TEXTS_PATH = './preprocessed_texts/'
FULL_TEXTS_PATH = None

def dir_path_cb(dir_path: str):
    if os.path.exists(path=dir_path):
        if(len(os.listdir(path=dir_path)) == 0):
            st.warning(body='WARNING: No files detected in directory path:')
        else:
            global FULL_TEXTS_PATH
            FULL_TEXTS_PATH = dir_path
            st.success(body='SUCCESS: Confirmed directory path.')
    else:
        st.error(body=f'ERROR: The path does not exist.')

def query_cb():
    preprocess_texts()
    X = doc_term_matrix()
    st.dataframe(data=X)

def preprocess_texts():    
    # checking for correct setup
    if FULL_TEXTS_PATH is None:
        st.error(body='ERROR: No directory path for full texts loaded.')
        return
    
    os.makedirs(name=PREPROCESSED_TEXTS_PATH, exist_ok=True)
    # if len(os.listdir(path=PREPROCESSED_TEXTS_PATH)) > 0:
    #     st.warning(body='WARNING: Preprocessing previously completed already.')
    #     return
    
    for filename in os.listdir(path=FULL_TEXTS_PATH)[:10]:
        # extract text
        st.write(filename)
        text = open(file=os.path.join(FULL_TEXTS_PATH, filename), mode='r').read()
        text = cltk_normalize(text=text)
        
        # lemmatize text and save as single text blob with no punctuation or marks
        lemmatized_blob = ' '.join(list([pair[1] for pair in lemmatizer.lemmatize(tokens=text.split())]))
        with open(file=os.path.join(PREPROCESSED_TEXTS_PATH, filename.split(sep='.txt')[0] + '_preprocessed.txt'), mode='w') as preprocessed_file:
            preprocessed_file.write(lemmatized_blob)

def doc_term_matrix():
    txt_paths = [PREPROCESSED_TEXTS_PATH + file_name for file_name in os.listdir(path=PREPROCESSED_TEXTS_PATH)]
    vectorizer = CountVectorizer(input='filename')
    X = vectorizer.fit_transform(raw_documents=txt_paths)
    # st.write(vectorizer.vocabulary_)
    return X.toarray()
