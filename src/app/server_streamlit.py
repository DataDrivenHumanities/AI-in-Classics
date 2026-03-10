from __future__ import annotations

import os
import sys
from pathlib import Path

# Streamlit runs this file directly, so the project root may not be on `sys.path`.
# Add it so imports like `from src.app import ...` work reliably.
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import numpy as np
import streamlit as st
import streamlit.components.v1 as components

from src.app import app_functions as app_func
from src.app import model_registry as model_cfg
from src.app import webUI as ui
from src.app.settings import main_settings

try:
    from src.app.ollama_client import chat_stream
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
        from src.app import analyze, query, load
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

    DEBUG = mode_toggle == "Debug"

    # ---------- Session state defaults ----------
    st.session_state.setdefault("latin_text", "")
    st.session_state.setdefault("latin_chat_messages", [])  # list[{role,content}]

    # ---------- Header ----------
    ui.hero_header("AI in Classics", "Greek and Latin Query Engine")

    # ---------- Main task router ----------
    if task_select == tasks[0]:
        load.app()
    elif task_select == tasks[1]:
        query.app()
    elif task_select == tasks[2]:
        analyze.render_analyze()

    # ---------- Latin text workspace ----------
    st.markdown("---")
    st.subheader("Latin Text")
    ui.card(
        "Load a Latin passage once, preview it, and reuse it for highlighting + model runs (no copy/paste)."
    )

    sample_dir = PROJECT_ROOT / "src" / "sample_text" / "latin"
    sample_files = []
    try:
        if sample_dir.exists():
            sample_files = sorted(
                [p.name for p in sample_dir.glob("*.txt") if p.is_file()]
            )
    except Exception:
        sample_files = []

    t_paste, t_upload, t_sample = st.tabs(["Paste", "Upload", "Sample"])
    with t_paste:
        draft = st.text_area(
            "Paste Latin text",
            height=180,
            placeholder="Paste Latin text here…",
            key="latin_text_paste_draft",
        )
        if st.button("Use pasted text", key="use_paste"):
            st.session_state["latin_text"] = draft or ""
            try:
                st.query_params.pop("lemma", None)
            except Exception:
                pass

    with t_upload:
        uploaded = st.file_uploader(
            "Upload a file (txt/md/csv/tsv/pdf)",
            type=["txt", "md", "csv", "tsv", "pdf"],
            accept_multiple_files=False,
            key="latin_text_upload",
        )
        if st.button("Use uploaded file", key="use_upload"):
            text = ""
            if uploaded is not None:
                text = app_func.read_uploaded_file(uploaded)
                try:
                    uploaded.seek(0)
                except Exception:
                    pass
            st.session_state["latin_text"] = text or ""
            try:
                st.query_params.pop("lemma", None)
            except Exception:
                pass

    with t_sample:
        if not sample_files:
            st.caption("No sample texts found in `src/sample_text/latin/`.")
        else:
            picked = st.selectbox("Choose a sample", options=sample_files)
            if st.button("Load sample", key="use_sample"):
                p = sample_dir / picked
                try:
                    st.session_state["latin_text"] = p.read_text(encoding="utf-8")
                except Exception as e:
                    st.error(f"Failed to load sample: {e}")
                try:
                    st.query_params.pop("lemma", None)
                except Exception:
                    pass

    latin_text = app_func.cltk_normalize(st.session_state.get("latin_text") or "")
    if not latin_text:
        st.warning("No Latin text loaded yet. Paste, upload, or pick a sample above.")
    else:
        with st.expander("Preview"):
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Characters", f"{len(latin_text):,}")
            with col2:
                st.metric("Words (rough)", f"{len(latin_text.split()):,}")
            st.code(latin_text[:2000] + ("\n\n[...preview truncated...]" if len(latin_text) > 2000 else ""))

    # ---------- Lexicon overlay ----------
    st.subheader("Lexicon Highlight (LatinAffectus)")
    ui.use_lexicon_overlay_css()

    dsn = app_func.resolve_database_url()
    show_overlay = st.checkbox("Show sentiment overlay", value=True)
    if show_overlay and latin_text:
        if not dsn:
            st.info("Set `DATABASE_URL` to enable lexicon lookup + highlighting.")
        else:
            MAX_OVERLAY_CHARS = 12000
            overlay_text = latin_text
            if len(overlay_text) > MAX_OVERLAY_CHARS:
                overlay_text = overlay_text[:MAX_OVERLAY_CHARS] + "\n\n[...overlay truncated...]"
                st.caption("Overlay is shown on the first 12k characters for performance.")

            @st.cache_data(show_spinner=False)
            def _cached_spans(text: str, dsn: str) -> dict:
                ann = app_func._latin_lexicon_annotator(dsn)
                return ann.annotate_spans(text)

            with st.spinner("Computing lexicon highlights..."):
                res = _cached_spans(overlay_text, dsn)

            spans = res.get("spans") or []
            lemma_details = res.get("lemma_details") or {}
            cov = res.get("coverage") or {}

            st.caption("Click a colored lemma chip to see details. Press Esc to close.")
            html = ui.latin_sentiment_overlay_popup_html(
                overlay_text,
                spans,
                lemma_details=lemma_details,
            )
            # Heuristic: allocate height based on text length (keeps scroll within the Streamlit page).
            est_lines = max(6, min(60, int(len(overlay_text) / 80)))
            height_px = 80 + est_lines * 26
            components.html(html, height=height_px, scrolling=True)

            c1, c2, c3 = st.columns(3)
            with c1:
                st.metric("Tokens", int(cov.get("token_count") or 0))
            with c2:
                st.metric("Lexicon hit rate", round(float(cov.get("affectus_hit_rate") or 0.0), 3))
            with c3:
                st.metric("Sentiment lemmas", int(cov.get("sentiment_lemma_hits") or 0))

            if DEBUG:
                with st.expander("Debug: overlay payload"):
                    st.json(res)

    # ---------- Sentiment Analysis ----------
    st.markdown("---")
    st.subheader("Sentiment Analysis")
    ui.card(
        "Run quick polarity scoring either with a built-in lexicon (fast) or via the selected model (slower but more contextual)."
    )

    engine = st.radio("Engine", ["Built-in (VADER)", "Model (Ollama)", "Model (Hugging Face)"], horizontal=True)

    run_sa = st.button("Analyze Sentiment")

    if run_sa:
        if not latin_text:
            st.warning("Load Latin text above first.")
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
                try:
                    with st.spinner("Asking model..."):
                        raw = app_func.llm_sentiment(latin_text, model_choice)
                except RuntimeError as exc:
                    st.error(str(exc))
                else:
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

    # ---------- Latin LLM ----------
    st.markdown("---")
    st.subheader("Latin LLM")
    ui.card(
        "Run a structured analysis (six modes) or ask freeform questions about the loaded text.",
        title="Run Analysis / Chat",
    )

    if not latin_text:
        st.caption("Load Latin text above to enable LLM features.")
    else:
        tab_run, tab_chat = st.tabs(["Run Analysis", "Chat about this text"])

        with tab_run:
            mode_options = [
                (1, "Translation Only"),
                (2, "Word/Lemma Sentiment"),
                (3, "Document-Level Sentiment"),
                (4, "Aspect-Based Sentiment"),
                (5, "Sentence/Paragraph-Level"),
                (6, "All"),
            ]
            picked = st.selectbox(
                "Analysis mode",
                options=mode_options,
                format_func=lambda x: f"{x[0]}: {x[1]}",
            )
            period = st.text_input("Period (optional)", value="")
            genre = st.text_input("Genre/Context (optional)", value="")
            out_len = st.selectbox("Output length", options=["Short", "Medium", "Long"], index=1)
            include_priors = st.checkbox(
                "Include lexicon priors (LEXICON_PRIORS)",
                value=bool(dsn),
                disabled=not bool(dsn),
            )

            if st.button("Run analysis", key="run_latin_analysis"):
                try:
                    with st.spinner("Running analysis..."):
                        out = app_func.latin_llm_analyze(
                            latin_text,
                            model_choice,
                            mode=int(picked[0]),
                            period=period,
                            genre=genre,
                            output_length=out_len,
                            include_lexicon_priors=include_priors,
                        )
                    st.markdown(out)
                except Exception as exc:
                    st.error(str(exc))

                if DEBUG and include_priors:
                    with st.expander("Debug: injected priors"):
                        clip = app_func._clip_latin_text(latin_text)
                        st.code(app_func._latin_lexicon_priors_json(clip))

        with tab_chat:
            col1, col2 = st.columns([1, 1])
            with col1:
                period = st.text_input("Period (optional)", value="", key="chat_period")
            with col2:
                genre = st.text_input("Genre/Context (optional)", value="", key="chat_genre")
            include_priors = st.checkbox(
                "Include lexicon priors in chat context",
                value=bool(dsn),
                disabled=not bool(dsn),
                key="chat_priors",
            )

            if st.button("Reset chat", key="reset_chat"):
                st.session_state["latin_chat_messages"] = []

            # Render transcript
            for m in st.session_state.get("latin_chat_messages") or []:
                role = m.get("role") or "assistant"
                content = m.get("content") or ""
                if role not in {"user", "assistant"}:
                    role = "assistant"
                with st.chat_message(role):
                    st.markdown(content)

            q = st.chat_input("Ask a question about the loaded Latin text…")
            if q:
                st.session_state["latin_chat_messages"].append({"role": "user", "content": q})
                system = app_func.build_latin_chat_system_prompt(
                    latin_text,
                    period=period,
                    genre=genre,
                    include_lexicon_priors=include_priors,
                )
                history = st.session_state["latin_chat_messages"][-12:]
                messages = [{"role": "system", "content": system}] + history

                with st.chat_message("assistant"):
                    out = st.empty()
                    buf: list[str] = []
                    try:
                        for tok in chat_stream(messages, model=model_choice):
                            buf.append(tok)
                            out.markdown("".join(buf))
                        answer = "".join(buf).strip()
                        out.markdown(answer)
                    except RuntimeError as exc:
                        st.error(str(exc))
                        answer = ""

                if answer:
                    st.session_state["latin_chat_messages"].append(
                        {"role": "assistant", "content": answer}
                    )


if __name__ == "__main__":
    main()
