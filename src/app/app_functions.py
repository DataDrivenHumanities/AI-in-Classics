import io
import os
import shutil
import json
import re
import sys
import uuid
import tempfile
import unicodedata
from pathlib import Path
from typing import Optional, Dict, Any
from functools import lru_cache
import asyncio
import numpy as np
import pandas as pd
import tqdm

BASE_DIR = Path(__file__).resolve().parents[2]
DEFAULT_CLTK_DATA = BASE_DIR / "cltk_data"
if not os.getenv("CLTK_DATA"):
    os.environ["CLTK_DATA"] = str(DEFAULT_CLTK_DATA)
CLTK_DATA_PATH = Path(os.environ["CLTK_DATA"]).expanduser()
CLTK_DATA_PATH.mkdir(parents=True, exist_ok=True)

from cltk import NLP
from sklearn.feature_extraction.text import CountVectorizer

import streamlit as st
from .settings import main_settings
from . import model_registry as model_cfg

try:
    from transformers import pipeline

    TRANSFORMERS_OK = True
except Exception:
    pipeline = None
    TRANSFORMERS_OK = False

PREPROCESS_CHECKPOINT = False
DTM_CHECKPOINT = False
DEBUG = True
HISTORY = list()
try:
    nlp = NLP(language_code="grc")
except TypeError:
    nlp = NLP(language="grc")
HF_DEFAULT_MODEL = os.getenv(
    "HF_SENTIMENT_MODEL", "rtwins/greekbert_for_text_classification"
)


def cltk_normalize(text: str) -> str:
    # CLTK 1.x exposed `cltk_normalize`; CLTK 2.x removed/moved it.
    # We keep a minimal normalization layer so the rest of the app keeps working.
    if text is None:
        return ""
    if not isinstance(text, str):
        text = str(text)
    return unicodedata.normalize("NFC", text).strip()


@lru_cache(maxsize=1)
def resolve_database_url() -> str:
    """
    Resolve DATABASE_URL for local dev.

    Streamlit does not automatically load `.env`, so we try to load it here
    (best-effort) and then return the environment variable.
    """
    try:
        from dotenv import load_dotenv  # type: ignore

        project_root = BASE_DIR
        for env_path in (Path.cwd() / ".env", project_root / ".env"):
            if env_path.exists():
                load_dotenv(env_path)
                break
    except Exception:
        pass
    return (os.getenv("DATABASE_URL") or "").strip()


def _extract_lemmas(analysis: Any) -> list[str]:
    if analysis is None:
        return []
    if isinstance(analysis, (list, tuple, set)):
        return [str(item).strip() for item in analysis if str(item).strip()]
    words = getattr(analysis, "words", None)
    if words:
        out: list[str] = []
        for word in words:
            lemma = getattr(word, "lemma", None) or getattr(word, "string", None)
            if lemma is None:
                continue
            lemma = str(lemma).strip()
            if lemma:
                out.append(lemma)
        return out
    if isinstance(analysis, str):
        return [part for part in analysis.split() if part]
    return []


def _resolve_hf_repo_name(preferred: Optional[str]) -> str:
    candidate = (preferred or "").strip()
    if candidate:
        if "/" in candidate and ":" not in candidate.partition("/")[0]:
            return candidate
        try:
            registry = model_cfg.get_registry()
            entry = registry.get(candidate)
            meta = getattr(entry, "metadata", {}) or {}
            for key in ("hf_repo", "huggingface_repo", "hf_model", "huggingface_id"):
                repo = meta.get(key)
                if isinstance(repo, str) and repo.strip():
                    return repo.strip()
        except Exception:
            pass
    return HF_DEFAULT_MODEL

try:
    import pypdf

    _PDF_OK = True
except Exception:
    _PDF_OK = False

try:
    from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

    VADER_OK = True
except Exception:
    VADER_OK = False

try:
    from .ollama_client import chat_stream, generate_json, resolve_available_model_tag
except Exception:
    st.error(
        "Cannot import ollama_client. Make sure src/ollama_client.py exists and is importable."
    )
    raise


def dtm_cb():
    DOC_TERM_MATRIX = main_settings["DOC_TERM_MATRIX"]
    VOCABULARY = main_settings["VOCABULARY"]
    sorted_vocab = sorted(list(VOCABULARY.keys()))

    # display data
    if DOC_TERM_MATRIX is None:
        st.warning(
            body="WARNING (DTM CALLBACK): Cannot perform analysis on empty data."
        )
        return

    st.caption(body="Figure 1. Document-term matrix.")
    st.dataframe(data=DOC_TERM_MATRIX)
    st.caption(body="Figure 2. Sample subset of sorted and lemmatized vocabulary.")
    st.write(sorted_vocab[100:110])

    with st.expander(label="Download", expanded=False):
        # download document-term matrix
        with io.BytesIO() as buffer:
            np.save(file=buffer, arr=DOC_TERM_MATRIX)
            st.download_button(
                label="Download DTM",
                data=buffer,
                file_name="doc-term-matrix.npy",
                mime="text/npy",
                help="Download document-term matrix as Numpy file.",
            )

        # download vocabulary
        if st.button(
            label="Download Vocabulary",
            help="Save list of all unique stem words of corpus as text file.",
        ):
            if DEBUG:
                st.write(sorted_vocab[:10])
                print(sorted_vocab[:10])

            with open(file="./vocabulary.txt", mode="a", encoding="utf-8") as f:
                prog = st.progress(value=0.0)
                for index, vocab in tqdm.tqdm(enumerate(sorted_vocab)):
                    prog.progress(value=float(index + 1) / len(sorted_vocab))
                    f.write(f"{vocab}\n")


def dir_path_cb():
    global HISTORY
    global PREPROCESS_CHECKPOINT
    FULL_TEXTS_PATH = main_settings["FULL_TEXTS_PATH"]
    PREPROCESSED_TEXTS_PATH = main_settings["PREPROCESSED_TEXTS_PATH"]
    dir_path = os.path.abspath(path=main_settings["dir_path_input"])

    # debugging
    if DEBUG:
        st.write(FULL_TEXTS_PATH)
        st.write(dir_path)
        st.write(HISTORY)

    # check for valid path
    if os.path.exists(path=dir_path):
        # check existence of only .txt files
        if not np.all(
            a=list(
                [
                    os.path.splitext(p=path)[1] == ".txt"
                    for path in os.listdir(path=dir_path)
                ]
            )
        ):
            st.error(
                body="ERROR (DIRECTORY PATH CALLBACK): Directory path contains nested directories."
            )
            return

        # check for different data source than last load
        source_changed = False
        if len(HISTORY) == 0 or (
            HISTORY[0] != dir_path if len(HISTORY) == 1 else HISTORY[-2] != dir_path
        ):
            source_changed = True
            HISTORY.append(dir_path)
            shutil.rmtree(path=PREPROCESSED_TEXTS_PATH, ignore_errors=True)
            os.makedirs(name=PREPROCESSED_TEXTS_PATH, exist_ok=True)

        if len(os.listdir(path=dir_path)) == 0:
            st.warning(
                body="WARNING (DIRECTORY PATH CALLBACK): No files detected in directory path:"
            )

        main_settings["FULL_TEXTS_PATH"] = dir_path
        main_settings["UPLOADED_DATA_NAME"] = dir_path
        PREPROCESS_CHECKPOINT = True
        st.success(
            body=f'SUCCESS (DIRECTORY PATH CALLBACK): Confirmed directory path. {"Path has changed since last load." if source_changed else "Same path as last load."}'
        )
    else:
        st.error(body="ERROR (DIRECTORY PATH CALLBACK): The path does not exist.")


def csv_upload_cb():
    global PREPROCESS_CHECKPOINT
    FULL_TEXTS_PATH = main_settings["FULL_TEXTS_PATH"] = "./full_texts/"
    PREPROCESSED_TEXTS_PATH = main_settings["PREPROCESSED_TEXTS_PATH"]
    csv_file = main_settings["csv_file"]

    # check for different data source than last load
    source_changed = False
    if main_settings["UPLOADED_DATA_NAME"] != csv_file.name:
        source_changed = True

        # resetting temporary directories
        shutil.rmtree(path=FULL_TEXTS_PATH, ignore_errors=True)
        shutil.rmtree(path=PREPROCESSED_TEXTS_PATH, ignore_errors=True)
        os.makedirs(name=FULL_TEXTS_PATH, exist_ok=True)
        os.makedirs(name=PREPROCESSED_TEXTS_PATH, exist_ok=True)

        csv_data = csv_file.getValue()
        pd.read_csv(file_path_or_buffer=csv_data)
        st.dataframe(data=csv_data)

    main_settings["UPLOADED_DATA_NAME"] = csv_file.name
    PREPROCESS_CHECKPOINT = True
    st.success(
        body=f'SUCCESS: Confirmed directory path. {"CSV has changed since last load." if source_changed else "Same CSV as last load."}'
    )


def load_cb():
    preprocess_texts()
    DOC_TERM_MATRIX = doc_term_matrix()
    main_settings["DOC_TERM_MATRIX"] = DOC_TERM_MATRIX


def query_cb():
    DOC_TERM_MATRIX = main_settings["DOC_TERM_MATRIX"]
    VOCABULARY = main_settings["VOCABULARY"]
    query_input = main_settings["query_input"]
    kws = _extract_lemmas(nlp.analyze(cltk_normalize(query_input)))

    if not VOCABULARY:
        st.error("No vocabulary is available yet. Load and preprocess a dataset first.")
        return

    vocab_indexes = np.asarray(
        a=sorted(
            list(filter(lambda x: x is not None, [VOCABULARY.get(kw) for kw in kws]))
        )
    )

    if DEBUG:
        st.write(f"vocab_indexes:\n{vocab_indexes}")

    dtm_df = pd.DataFrame(data=DOC_TERM_MATRIX)

    if DEBUG:
        st.write("Column-reduced DTM")
        st.dataframe(data=dtm_df.iloc[:, vocab_indexes].any(axis=1))


def doc_term_matrix():
    global DTM_CHECKPOINT
    PREPROCESSED_TEXTS_PATH = main_settings["PREPROCESSED_TEXTS_PATH"]

    # validity checks
    if not DTM_CHECKPOINT:
        return

    # check for existence of required directories
    if not os.path.exists(path=PREPROCESSED_TEXTS_PATH):
        st.error(
            body="ERROR (DOC_TERM_MATRIX): Directory containing preprocessed files does not exist."
        )
        return

    if len(os.listdir(path=PREPROCESSED_TEXTS_PATH)) == 0:
        st.warning(
            body="WARNING (DOC_TERM_MATRIX): No documents have been preprcessed yet."
        )

    preprocessed_txt_paths = [
        PREPROCESSED_TEXTS_PATH + file_name
        for file_name in os.listdir(path=PREPROCESSED_TEXTS_PATH)
    ]
    vectorizer = CountVectorizer(input="filename")
    X = vectorizer.fit_transform(raw_documents=preprocessed_txt_paths)
    main_settings["VOCABULARY"] = vectorizer.vocabulary_  # dict
    st.text(f"Vocabulary size: {len(vectorizer.vocabulary_)}")
    return X.toarray()


def preprocess_texts():
    global PREPROCESS_CHECKPOINT
    global DTM_CHECKPOINT
    DTM_CHECKPOINT = False
    FULL_TEXTS_PATH = main_settings["FULL_TEXTS_PATH"]
    PREPROCESSED_TEXTS_PATH = main_settings["PREPROCESSED_TEXTS_PATH"]

    # validity checks
    if not PREPROCESS_CHECKPOINT:
        return

    if FULL_TEXTS_PATH is None or not os.path.exists(path=FULL_TEXTS_PATH):
        st.error(body="ERROR (PREPROCESS): Directory path for dataset does not exist.")
        return

    os.makedirs(name=PREPROCESSED_TEXTS_PATH, exist_ok=True)
    prog = st.progress(value=0.0)
    file_list = os.listdir(path=FULL_TEXTS_PATH)[:10]
    for index, filename in tqdm.tqdm(enumerate(file_list)):
        # extract text
        prog.progress(value=float(index + 1) / len(file_list))
        text = open(file=os.path.join(FULL_TEXTS_PATH, filename), mode="r").read()
        text = cltk_normalize(text=text)

        # lemmatize text and save as single text blob with no punctuation or marks
        lemmatized_blob = " ".join(_extract_lemmas(nlp.analyze(text)))
        with open(
            file=os.path.join(
                PREPROCESSED_TEXTS_PATH,
                filename.split(sep=".txt")[0] + "_preprocessed.txt",
            ),
            mode="w",
        ) as preprocessed_file:
            preprocessed_file.write(lemmatized_blob)

    PREPROCESS_CHECKPOINT = False
    DTM_CHECKPOINT = True
    # dill.dump(file=)


def read_uploaded_file(upload) -> str:
    """
    Read a Streamlit UploadedFile into plain text.
    Supports .txt/.md/.csv/.tsv directly; PDFs if pypdf is available.
    Otherwise we try a best-effort UTF-8 decode.
    """
    name = (upload.name or "").lower()
    data = upload.read()

    # simple text-ish
    if name.endswith((".txt", ".md", ".csv", ".tsv")):
        try:
            return data.decode("utf-8", errors="ignore")
        except Exception:
            return data.decode("latin-1", errors="ignore")

    # pdf
    if name.endswith(".pdf"):
        if not _PDF_OK:
            st.warning(
                "PDF support requires `pypdf` (install with `poetry add pypdf`)."
            )
            return ""
        try:
            reader = pypdf.PdfReader(io.BytesIO(data))
            return "\n\n".join((p.extract_text() or "") for p in reader.pages)
        except Exception as e:
            st.error(f"Failed to read PDF: {e}")
            return ""
    try:
        return data.decode("utf-8", errors="ignore")
    except Exception:
        return data.decode("latin-1", errors="ignore")


def builtin_sentiment(text: str) -> Optional[dict]:
    """
    Run a quick VADER sentiment on the provided text.
    Returns dict with {label, confidence, scores} or None if unavailable.
    """
    if not VADER_OK:
        return None
    analyzer = SentimentIntensityAnalyzer()
    scores = analyzer.polarity_scores(text or "")
    compound = scores.get("compound", 0.0)
    if compound >= 0.05:
        label = "positive"
    elif compound <= -0.05:
        label = "negative"
    else:
        label = "neutral"
    conf = min(1.0, max(0.0, abs(compound)))
    return {"label": label, "confidence": round(conf, 3), "scores": scores}


def llm_sentiment(text: str, model_name: str) -> str:
    """
    Ask the LLM to classify sentiment. Returns a JSON string.

    Uses deterministic `LEXICON_PRIORS` (when DATABASE_URL is configured) and
    prefers `/api/generate` with `raw:true` + `format:"json"` to avoid paying the
    Modelfile prompt tax on every request.
    """
    # keep text reasonable for prompt size
    MAX = 6000
    clip = text[:MAX] + ("\n\n[...truncated...]" if len(text) > MAX else "")

    priors = None
    dsn = (os.getenv("DATABASE_URL") or "").strip()
    if dsn:
        try:
            annotator = _latin_lexicon_annotator(dsn)
            priors = annotator.build_llm_payload(clip)
        except Exception:
            priors = None

    priors_json = (
        json.dumps(priors, ensure_ascii=False, separators=(",", ":")) + "\n\n"
        if isinstance(priors, dict)
        else ""
    )

    prompt = (
        "Return ONLY JSON with exactly these keys:\n"
        '{"label":"positive|negative|neutral","confidence":number,"analysis":{"rationale":string}}.\n'
        "No extra keys. No prose outside JSON.\n"
        "You are classifying sentiment for LATIN text.\n"
        "If lexicon priors are present, rely on them for matching lemmas only; coverage is partial.\n\n"
        f"{priors_json}"
        f"Text:\n{clip}"
    )

    model_tag = resolve_available_model_tag(model_name)
    parsed, _raw = asyncio.run(
        generate_json(
            model_tag,
            prompt,
            num_predict=384,
            retries=1,
            raw=True,
            out_format="json",
        )
    )
    return json.dumps(parsed, ensure_ascii=False)


def _clip_latin_text(text: str, *, max_chars: int = 6000) -> str:
    t = cltk_normalize(text or "")
    if len(t) <= max_chars:
        return t
    return t[:max_chars] + "\n\n[...truncated...]"


def _latin_lexicon_priors_json(clip: str) -> str:
    """
    Best-effort lexicon priors JSON for injection. Returns "" when unavailable.
    """
    dsn = resolve_database_url()
    if not dsn:
        return ""
    try:
        annotator = _latin_lexicon_annotator(dsn)
        priors = annotator.build_llm_payload(clip)
        if not isinstance(priors, dict):
            return ""
        return json.dumps(priors, ensure_ascii=False, separators=(",", ":")) + "\n\n"
    except Exception:
        return ""


def latin_llm_analyze(
    text: str,
    model_name: str,
    *,
    mode: int,
    period: str = "",
    genre: str = "",
    output_length: str = "medium",
    include_lexicon_priors: bool = True,
) -> str:
    """
    Mode-driven Latin analysis. UI owns mode selection; we keep prompts small.
    """
    clip = _clip_latin_text(text)
    priors_json = _latin_lexicon_priors_json(clip) if include_lexicon_priors else ""

    meta = []
    if period.strip():
        meta.append(f"Period: {period.strip()}")
    if genre.strip():
        meta.append(f"Genre/Context: {genre.strip()}")
    meta_block = ("\n".join(meta) + "\n\n") if meta else ""

    if str(output_length).lower().startswith("short"):
        num_predict = 320
    elif str(output_length).lower().startswith("long"):
        num_predict = 1200
    else:
        num_predict = 700

    if mode == 1:
        task = (
            "Provide a faithful English translation of the Latin text. "
            "Then give 3–6 short translation notes for any tricky phrases."
        )
    elif mode == 2:
        task = (
            "Give a word/lemma-focused sentiment analysis. "
            "List the key sentiment-bearing Latin words/lemmas (5–15 items) with a brief explanation each, "
            "and explain negation/intensifiers if present. Include a one-paragraph overall sentiment summary."
        )
    elif mode == 3:
        task = (
            "Give a document-level sentiment assessment: label (positive/negative/neutral/mixed), "
            "confidence (0–1), and a concise rationale grounded in the text."
        )
    elif mode == 4:
        task = (
            "Do aspect-based sentiment: identify 3–6 aspects/entities/themes, and for each give sentiment + evidence. "
            "Finish with a short comparison of aspects."
        )
    elif mode == 5:
        task = (
            "Do sentence/paragraph-level sentiment: pick 5–10 representative units (sentences or short segments), "
            "translate each briefly, label sentiment, and summarize progression across the text."
        )
    elif mode == 6:
        task = (
            "Provide all analyses in this order with clear headings: "
            "1) Translation  2) Word/Lemma Sentiment  3) Document-Level Sentiment  "
            "4) Aspect-Based Sentiment  5) Sentence/Paragraph-Level Sentiment."
        )
    else:
        raise ValueError("mode must be an integer 1–6")

    prompt = (
        "You are a Latin text analysis assistant.\n"
        "Answer using the provided Latin text; do not ask the user to paste it.\n"
        "If lexicon priors are present, rely on them for matching lemmas only; coverage is partial.\n\n"
        f"{priors_json}"
        f"{meta_block}"
        f"Task:\n{task}\n\n"
        f"Latin text:\n{clip}\n"
    )

    from .ollama_client import generate_text, resolve_available_model_tag

    model_tag = resolve_available_model_tag(model_name)
    return asyncio.run(
        generate_text(
            model_tag,
            prompt,
            temperature=0.2,
            num_predict=num_predict,
        )
    )


def build_latin_chat_system_prompt(
    text: str,
    *,
    period: str = "",
    genre: str = "",
    include_lexicon_priors: bool = True,
) -> str:
    clip = _clip_latin_text(text)
    priors_json = _latin_lexicon_priors_json(clip) if include_lexicon_priors else ""
    meta = []
    if period.strip():
        meta.append(f"Period: {period.strip()}")
    if genre.strip():
        meta.append(f"Genre/Context: {genre.strip()}")
    meta_block = ("\n".join(meta) + "\n\n") if meta else ""
    return (
        "You are a Latin text analysis assistant.\n"
        "The user will ask questions about the provided Latin text.\n"
        "Do not ask the user to paste the text; it is included below.\n"
        "If the question cannot be answered from the text, say what is missing.\n"
        "If lexicon priors are present, rely on them for matching lemmas only; coverage is partial.\n\n"
        f"{priors_json}"
        f"{meta_block}"
        f"Latin text:\n{clip}\n"
    )


@lru_cache(maxsize=1)
def _latin_lexicon_import_root() -> Optional[Path]:
    root = BASE_DIR / "src" / "Lemmatizer-LTN-LiLa"
    return root if root.exists() else None


@lru_cache(maxsize=1)
def _latin_lexicon_annotator(dsn: str):
    lex_root = _latin_lexicon_import_root()
    if lex_root is None:
        raise RuntimeError("Missing src/Lemmatizer-LTN-LiLa; cannot import lexicon annotator.")
    if str(lex_root) not in sys.path:
        sys.path.insert(0, str(lex_root))

    from rag.latin_lexicon_annotator import LatinLexiconAnnotator, LatinLexiconAnnotatorConfig

    return LatinLexiconAnnotator(
        dsn=dsn,
        config=LatinLexiconAnnotatorConfig(top_k=12),
    )

def hf_sentiment(text: str, hf_classifier_params: Dict[str, Any]):
    """
    Run a Hugging Face text-classification pipeline for sentiment analysis.
    """
    if not TRANSFORMERS_OK or pipeline is None:
        raise RuntimeError(
            "transformers is not installed. Install it to enable Hugging Face sentiment."
        )
    model = hf_classifier_params.get("model", None)
    task = hf_classifier_params.get("task", None)
    if not model or not task:
        raise Exception("model and task cannot be blank in model registry for hugging face models")
    classifier = pipeline(task=task, model=model)

    res = []

    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]

    for s in sentences:
        sentence_result = classifier(s)
        sentence_result[0]["sentence"] = s
        res.append(sentence_result)

    if len(res) > 100:
        tmp_dir = os.path.abspath(os.path.join(os.getcwd(), "tmp"))
        os.makedirs(tmp_dir, exist_ok=True)
        filename = f"hf_sentiment_results_{uuid.uuid4().hex}.csv"
        path = os.path.join(tmp_dir, filename)
        try:
            try:
                df = pd.json_normalize(res)
            except Exception:
                df = pd.DataFrame(res)
            df.to_csv(path, index=False)
        except Exception as e:
            return {"error": f"Failed to write CSV: {e}", "count": len(res)}
        return {"preview": res[:100], "csv_path": path, "count": len(res)}
    return res

def parse_llm_json(s: str) -> Optional[dict]:
    """Try to parse the model output as JSON; be forgiving if there's noise."""
    # first try a straight parse
    try:
        return json.loads(s)
    except Exception:
        pass

    # extract the first {...} block if present
    m = re.search(r"\{.*\}", s, flags=re.DOTALL)
    if m:
        try:
            return json.loads(m.group(0))
        except Exception:
            pass

    # heuristic fallback: look for a label word and a float
    low = s.lower()
    label = None
    for key in ("positive", "negative", "neutral"):
        if key in low:
            label = key
            break
    conf = None
    nums = re.findall(r"\b0?\.\d+|\b1(?:\.0+)?\b", s)  # 0.xxx .. 1(.0)
    if label or nums:
        if nums:
            try:
                conf = float(nums[0])
                conf = max(0.0, min(1.0, conf))
            except Exception:
                conf = None
        return {"label": label or "unknown", "confidence": conf}
    return None
