import streamlit as st
from app_functions import *
from globals import globals

def app():
    PREPROCESSED_TEXTS_PATH = globals['PREPROCESSED_TEXTS_PATH']
    
    # check for preprocessed texts
    if not os.path.exists(path=PREPROCESSED_TEXTS_PATH) or len(os.listdir(path=PREPROCESSED_TEXTS_PATH)) == 0:
        st.error(body='ERROR (ANALYZE PAGE): No dataset loaded or preprocessing has not finished.')
        return
    
    st.header(body='🕵️ Analyze Text')
    st.text(body='Perform statistical analysis on loaded corpus.')

    dtm_button = st.button(
        label='Document Term Matrix',
        help='Compute frequency of each word stem for each document.'
    )
    globals['dtm_button'] = dtm_button

    if dtm_button:
        dtm_cb()
