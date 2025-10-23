import numpy as np
import streamlit as st
from app_functions import *
from globals import globals


def app():
    st.header(body="🚚 Load")
    st.text(
        body="Load textual dataset for preprocessing and preparations for other tasks."
    )

    selector = st.selectbox(
        label="Locate Dataset",
        options=np.asarray(
            a=list(
                [
                    "Directory Path",
                    "CSV Upload",
                    "Previously Saved",
                ]
            )
        ),
        help="Choose mode of accessing data for querying.",
    )
    globals["selector"] = selector

    # control flow for type of data input
    if selector == "Directory Path":
        dir_path_input = st.text_input(
            label="Directory Path", help="Enter path to directory of texts:"
        )
        globals["dir_path_input"] = dir_path_input

        dir_path_button = st.button(
            label="Load", help="Check for existence of directory and texts."
        )
        globals["dir_path_button"] = dir_path_button

        if dir_path_input or dir_path_button:
            dir_path_cb()
            load_cb()

    else:
        csv_upload = st.file_uploader(
            label="CSV Upload",
            type="csv",
            accept_multiple_files=False,
            help="Upload CSV file containing source location in first column and text snippet in second column.",
        )
        globals["csv_upload"] = csv_upload

        if csv_upload:
            globals["csv_upload"] = csv_upload
            csv_upload_cb()
            load_cb()
