import streamlit as st
from app_functions import *
from globals import globals

def app():
    PREPROCESSED_TEXTS_PATH = globals['PREPROCESSED_TEXTS_PATH']
    
    # check for preprocessed texts
    if not os.path.exists(path=PREPROCESSED_TEXTS_PATH) or len(os.listdir(path=PREPROCESSED_TEXTS_PATH)) == 0:
        st.error(body='ERROR (QUERY PAGE): No dataset loaded or preprocessing has not finished.')
        return

    st.header(body='🔎 Query')
    st.text(body='Retrieve documents or text snippets containing any specified keywords.')

    with st.container():
        query_input = st.text_input(
            label='Query Documents',
            help='Enter some keywords to search across texts.'
        )
        globals['query_input'] = query_input
        
        save_corpus = st.checkbox(
            label='Save Corpus',
            value=False,
            
        )

        query_button = st.button(
            label='Search',
            help='Execute query for given keywords.'
        )
        globals['query_button'] = query_button

    if query_button:
        query_cb()
