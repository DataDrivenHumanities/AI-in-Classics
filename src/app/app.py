import streamlit as st
from app_functions import *

st.header(body='AI in Classics')
st.title('Greek and Latin Query Engine')


dir_path_input = st.text_input(
    label='Directory Path:',
    help='Enter path to directory of texts:'
)

dir_path_button = st.button(
    label='Load',
    help='Check for existence of directory and texts.'
)

if dir_path_input or dir_path_button:
    dir_path_cb(dir_path=dir_path_input)

query_input = st.text_input(
    label='Query Documents:',
    help='Enter some keywords to search across texts.'
)

query_button = st.button(
    label='🔎',
    help='Execute query for given keywords.'
)

if query_input or query_button:
    query_cb()
    # X = doc_term_matrix()
    # st.table(data=X)