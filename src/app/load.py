import numpy as np
import streamlit as st
from app.app_functions import dir_path_cb, load_cb, csv_upload_cb
from app.settings import main_settings


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
    main_settings["selector"] = selector

    # control flow for type of data input
    if selector == "Directory Path":
        dir_path_input = st.text_input(
            label="Directory Path", help="Enter path to directory of texts:"
        )
        main_settings["dir_path_input"] = dir_path_input

        dir_path_button = st.button(
            label="Load", help="Check for existence of directory and texts."
        )
        main_settings["dir_path_button"] = dir_path_button

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
        main_settings["csv_upload"] = csv_upload

        if csv_upload:
            main_settings["csv_upload"] = csv_upload
            csv_upload_cb()
            load_cb()
