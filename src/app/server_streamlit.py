# --- server_streamlit.py (safe import order, no top-level package imports) ---
import os, sys

# sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import numpy as np
import streamlit as st
from app.settings import main_settings
import app.app_functions as app_func
import app.model_registry as model_cfg
import app.webUI as ui

try:
    from app.ollama_client import chat_stream
except Exception:
    st.error(
        "Cannot import ollama_client. Make sure src/ollama_client.py exists and is importable."
    )
    raise

# ---------- Page config ----------
st.set_page_config(
    page_title="AI in Classics",
    page_icon="🏺",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        "About": "https://classics.ufl.edu/people/faculty/bozia/",
        "Get help": "https://www.youtube.com/",
    },
)

ui.use_light_preset(centered=True, max_width_px=1100)
ui.sidebar_logo(
    "images/uf_logo.png", link="https://classics.ufl.edu", height_px=56, align="center"
)


def main():

    try:
        import app.analyze as analyze
        import app.load as load
        import app.query as query
    except Exception as e:
        st.error(f"Failed to import app pages: {e}")
        st.stop()

    # ---------- Sidebar ----------
    try:
        registry = model_cfg.get_registry()
    except model_cfg.ModelRegistryError as exc:
        st.sidebar.error(f"Model registry error: {exc}")
        st.stop()

    available_models = registry.available_models()
    upcoming_models = registry.upcoming_models()
    if not available_models:
        st.sidebar.error("No models are currently marked as available.")
        if upcoming_models:
            st.sidebar.caption(
                "Configured (coming soon): "
                + ", ".join(model.display_label for model in upcoming_models)
            )
        st.stop()

    default_index = model_cfg.ModelRegistry.index_for(
        registry.default_model_id, available_models
    )
    selected_model = st.sidebar.radio(
        "Choose model",
        options=available_models,
        index=default_index,
        format_func=lambda model: model.display_label,
    )

    if selected_model.description:
        st.sidebar.caption(selected_model.description)
    if upcoming_models:
        st.sidebar.caption(
            "Coming soon: " + ", ".join(model.name for model in upcoming_models)
        )

    model_choice = selected_model.model_id

    tasks = np.asarray(["Load", "Query", "Analyze"])
    task_select = st.sidebar.selectbox(
        label="Tasks", options=tasks, help="Select a task after loading a dataset."
    )
    main_settings["task_select"] = task_select

    mode_toggle = st.sidebar.radio(
        label="Mode",
        options=np.asarray(["Production", "Debug"]),
        help="Set mode.",
    )

    DEBUG = True

    # ---------- Header ----------
    ui.hero_header("AI in Classics", "Greek and Latin Query Engine")

    # ---------- Main task router ----------
    if task_select == tasks[0]:
        load.app()
    elif task_select == tasks[1]:
        query.app()
    elif task_select == tasks[2]:
        analyze.app()

    # ---------- Sentiment Analysis ----------
    st.markdown("---")
    st.subheader("Sentiment Analysis")
    ui.card(
        "Run quick polarity scoring either with a built-in lexicon (fast) or via the selected model (slower but more contextual)."
    )

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
                        with st.container():
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
                with st.container():
                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric("Label", (parsed.get("label") or "unknown").title())
                    with col2:
                        conf = parsed.get("confidence")
                        st.metric("Confidence", conf if conf is not None else "—")
                    with st.expander("Model output (raw)"):
                        st.code(raw)

    # ---------- LLM Chat ----------
    st.markdown("---")
    user_q = st.text_input("Ask the model")
    ui.card(
        "Enter a question for the selected model; streamed tokens will render live.",
        title="LLM Chat",
    )

    if st.button("Ask"):
        messages = [{"role": "user", "content": user_q}]
        out = st.empty()
        buf = []
        for token in chat_stream(messages, model=model_choice):
            buf.append(token)
            out.markdown("".join(buf))
        out.markdown("".join(buf))


if __name__ == "__main__":
    main()
