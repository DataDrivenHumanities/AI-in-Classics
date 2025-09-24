import numpy as np
import streamlit as st
import analyze
import load
import query
import app_functions as app_func
from globals import globals  # noqa: F401


try:
    from ollama_client import chat_stream
except Exception:
    st.error(
        "Cannot import ollama_client. Make sure src/ollama_client.py exists and is importable."
    )
    raise


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

model_choice = st.sidebar.radio(
    "Choose model",
    ["greek_model:1.0.0", "latin_model:1.0.0"],
)

st.header(body="AI in Classics")
st.title(body="Greek and Latin Query Engine")

# existing tasks (unchanged)
tasks = np.asarray(a=list(["Load", "Query", "Analyze"]))
task_select = st.sidebar.selectbox(
    label="Tasks", options=tasks, help="Select a task after loading a dataset."
)
globals["task_select"] = task_select

mode_toggle = st.sidebar.radio(
    label="Mode",
    options=np.asarray(a=list(["Production", "Debug"])),
    help="Set mode.",
)

DEBUG = True

if task_select == tasks[0]:
    load.app()
elif task_select == tasks[1]:
    query.app()
elif task_select == tasks[2]:
    analyze.app()


st.markdown("---")
st.subheader("Sentiment Analysis")

engine = st.radio("Engine", ["Built-in (VADER)", "Model (Ollama)"], horizontal=True)

uploaded = st.file_uploader(
    "Upload a file to analyze (txt/md/csv/tsv/pdf)",
    type=["txt", "md", "csv", "tsv", "pdf"],
    accept_multiple_files=False,
)

run_sa = st.button("Analyze Sentiment")

if run_sa:
    text = ""
    if uploaded is not None:
        text = app_func.read_uploaded_file(uploaded)
        try:
            uploaded.seek(0)
        except Exception:
            pass

    if not text:
        st.warning("Please upload a file with textual content.")
    else:
        if engine.startswith("Built-in"):
            if not app_func.VADER_OK:
                st.error(
                    "Built-in sentiment requires `vaderSentiment`. "
                    "Install with: `poetry add vaderSentiment`"
                )
            else:
                res = app_func.builtin_sentiment(text)
                if not res:
                    st.error("Could not compute sentiment.")
                else:
                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric("Label", res["label"].title())
                    with col2:
                        st.metric("Confidence", res["confidence"])
                    with st.expander("Raw scores"):
                        st.json(res["scores"])
        else:
            with st.spinner("Asking model..."):
                raw = app_func.llm_sentiment(text, model_choice)
            parsed = app_func.parse_llm_json(raw) or {}
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Label", (parsed.get("label") or "unknown").title())
            with col2:
                conf = parsed.get("confidence")
                st.metric("Confidence", conf if conf is not None else "—")
            with st.expander("Model output (raw)"):
                st.code(raw)


st.markdown("---")
user_q = st.text_input("Ask the model")
if st.button("Ask"):
    messages = [{"role": "user", "content": user_q}]
    out = st.empty()
    buf = []
    for token in chat_stream(messages, model=model_choice):
        buf.append(token)
        out.markdown("".join(buf))
