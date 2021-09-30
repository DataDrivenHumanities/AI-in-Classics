
import numpy as np, os, pickle, streamlit as st
from dotenv import load_dotenv
from pprint import pprint

import scraper

# loading paths and metadata
load_dotenv()
METADATA_DF_PATH = os.getenv(key='METADATA_DF_PATH')
metadata_df = pickle.load(file=open(file=METADATA_DF_PATH, mode='rb'))['metadata_df']

# setting up folder to save original XML files
os.makedirs(name='original_xml/', exist_ok=True)

# aesthetics
st.set_page_config(
    page_title='Data Collection',
    page_icon='⛏️',
    layout='centered',
    initial_sidebar_state='collapsed'
)

st.title(body='Scrape XML or HTML for First1KOpenGreek Project')
st.write(metadata_df)

index_range = st.slider(
    label='Index Range',
    min_value=0,
    max_value=1000,
    value=(0, 1000)
)

if st.button(label='Scrape'):
    for idx in np.arange(*index_range):
        scraper.parse(urn=metadata_df.loc[idx, 'URN'], type='xml', save_dir_path='original_xml/')
    st.balloons()
