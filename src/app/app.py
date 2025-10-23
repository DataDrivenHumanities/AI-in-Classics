import analyze
import load
import numpy as np
import query
import streamlit as st
from app_functions import *
from globals import globals
from chatbot import init_chatbot

st.set_page_config(
    page_title="AI in Classics",
    page_icon="🏺",
    layout="centered",
    initial_sidebar_state="expanded",
    menu_items=dict(
        {
            "About": "https://classics.ufl.edu/people/faculty/bozia/",
            "Get help": "https://www.youtube.com/",
        }
    ),
)

st.header(body="AI in Classics")
st.title(body="Greek and Latin Query Engine")

# Initialize the chatbot component
init_chatbot()

tasks = np.asarray(a=list([
        'Load',
        'Query',
        'Analyze',
    ]))

task_select = st.sidebar.selectbox(
    label="Tasks", options=tasks, help="Select a task after loading a dataset."
)
globals["task_select"] = task_select

mode_toggle = st.sidebar.radio(
    label="Mode",
    options=np.asarray(
        a=list(
            [
                "Production",
                "Debug",
            ]
        )
    ),
    help="Set mode.",
)
# Set DEBUG based on mode_toggle selection
if mode_toggle == 'Production':
    DEBUG = False
else:
    DEBUG = True

# Store DEBUG value in globals for access across modules
globals['DEBUG'] = DEBUG

# Chatbot toggle
chatbot_toggle = st.sidebar.checkbox(
    label="Enable AI Assistant",
    value=True,
    help="Toggle the AI chatbot assistant on or off"
)
globals['show_chat'] = chatbot_toggle

#do the task selected 
if task_select == tasks[0]:
    load.app()
elif task_select == tasks[1]:
    query.app()
elif task_select == tasks[2]:
    analyze.app()
