import numpy as np
import streamlit as st
import load, query, analyze
from app_functions import *
from globals import globals

st.set_page_config(
    page_title='AI in Classics',
    page_icon='🏺',
    layout='centered',
    initial_sidebar_state='expanded',
    menu_items=dict({
        'About' : 'https://classics.ufl.edu/people/faculty/bozia/',
        'Get help' : 'https://www.youtube.com/',
    })
)

st.header(body='AI in Classics')
st.title(body='Greek and Latin Query Engine')

tasks = np.asarray(a=list([
        'Load',
        'Query',
        'Analyze',
    ]))

task_select = st.sidebar.selectbox(
    label='Tasks',
    options=tasks,
    help='Select a task after loading a dataset.'
)
globals['task_select'] = task_select

mode_toggle = st.sidebar.radio(
    label='Mode',
    options=np.asarray(a=list([
        'Production',
        'Debug',    
    ])),
    help='Set mode.'
)
# Set DEBUG based on mode_toggle selection
if mode_toggle == 'Production':
    DEBUG = False
else:
    DEBUG = True

# Store DEBUG value in globals for access across modules
globals['DEBUG'] = DEBUG
#do the task selected 
if task_select == tasks[0]:
    load.app()
elif task_select == tasks[1]:
    query.app()
elif task_select == tasks[2]:
    analyze.app()
