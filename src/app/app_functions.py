import io
import os
import shutil
import json
import re
from typing import Optional
import numpy as np
import pandas as pd
import tqdm

from cltk.alphabet.text_normalization import cltk_normalize
from cltk.data.fetch import FetchCorpus
from cltk.lemmatize.grc import GreekBackoffLemmatizer
from sklearn.feature_extraction.text import CountVectorizer

import streamlit as st
from app.globals import globals
import dill
import multiprocessing as mp

grc_corpus = FetchCorpus(language="grc")
grc_corpus.import_corpus(corpus_name="grc_models_cltk")
lemmatizer = GreekBackoffLemmatizer()

PREPROCESS_CHECKPOINT = False
DTM_CHECKPOINT = False
DEBUG = True
HISTORY = list()

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
    from app.ollama_client import chat_stream
except Exception:
    st.error(
        "Cannot import ollama_client. Make sure src/ollama_client.py exists and is importable."
    )
    raise


def dtm_cb():
    DOC_TERM_MATRIX = globals["DOC_TERM_MATRIX"]
    VOCABULARY = globals["VOCABULARY"]
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
    FULL_TEXTS_PATH = globals["FULL_TEXTS_PATH"]
    PREPROCESSED_TEXTS_PATH = globals["PREPROCESSED_TEXTS_PATH"]
    dir_path = os.path.abspath(path=globals["dir_path_input"])

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

        globals["FULL_TEXTS_PATH"] = dir_path
        globals["UPLOADED_DATA_NAME"] = dir_path
        PREPROCESS_CHECKPOINT = True
        st.success(
            body=f'SUCCESS (DIRECTORY PATH CALLBACK): Confirmed directory path. {"Path has changed since last load." if source_changed else "Same path as last load."}'
        )
    else:
        st.error(body="ERROR (DIRECTORY PATH CALLBACK): The path does not exist.")


def csv_upload_cb():
    global PREPROCESS_CHECKPOINT
    FULL_TEXTS_PATH = globals["FULL_TEXTS_PATH"] = "./full_texts/"
    PREPROCESSED_TEXTS_PATH = globals["PREPROCESSED_TEXTS_PATH"]
    csv_file = globals["csv_file"]

    # check for different data source than last load
    source_changed = False
    if globals["UPLOADED_DATA_NAME"] != csv_file.name:
        source_changed = True

        # resetting temporary directories
        shutil.rmtree(path=FULL_TEXTS_PATH, ignore_errors=True)
        shutil.rmtree(path=PREPROCESSED_TEXTS_PATH, ignore_errors=True)
        os.makedirs(name=FULL_TEXTS_PATH, exist_ok=True)
        os.makedirs(name=PREPROCESSED_TEXTS_PATH, exist_ok=True)

        csv_data = csv_file.getValue()
        pd.read_csv(file_path_or_buffer=csv_data)
        st.dataframe(data=csv_data)

    globals["UPLOADED_DATA_NAME"] = csv_file.name
    PREPROCESS_CHECKPOINT = True
    st.success(
        body=f'SUCCESS: Confirmed directory path. {"CSV has changed since last load." if source_changed else "Same CSV as last load."}'
    )


def load_cb():
    preprocess_texts()
    DOC_TERM_MATRIX = doc_term_matrix()
    globals["DOC_TERM_MATRIX"] = DOC_TERM_MATRIX


def query_cb():
    DOC_TERM_MATRIX = globals["DOC_TERM_MATRIX"]
    VOCABULARY = globals["VOCABULARY"]
    query_input = globals["query_input"]
    kws = lemmatizer.lemmatize(
        tokens=list([token for token in cltk_normalize(text=query_input).split()])
    )
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
    PREPROCESSED_TEXTS_PATH = globals["PREPROCESSED_TEXTS_PATH"]

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
    globals["VOCABULARY"] = vectorizer.vocabulary_  # dict
    st.text(f"Vocabulary size: {len(vectorizer.vocabulary_)}")
    return X.toarray()


def preprocess_texts():
    global PREPROCESS_CHECKPOINT
    global DTM_CHECKPOINT
    DTM_CHECKPOINT = False
    FULL_TEXTS_PATH = globals["FULL_TEXTS_PATH"]
    PREPROCESSED_TEXTS_PATH = globals["PREPROCESSED_TEXTS_PATH"]

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
        lemmatized_blob = " ".join(
            list([pair[1] for pair in lemmatizer.lemmatize(tokens=text.split())])
        )
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
    Ask the LLM to classify sentiment. We request strict JSON:
      {"label": "positive|neutral|negative", "confidence": 0.0-1.0}
    Streams output and returns the final collected string (may be JSON or text).
    """
    # keep text reasonable for prompt size
    MAX = 6000
    clip = text[:MAX] + ("\n\n[...truncated...]" if len(text) > MAX else "")

    system = (
        "You are a strict sentiment classifier for classical text. "
        "Return EXACT JSON with keys 'label' and 'confidence'. "
        "Label must be one of: positive, neutral, negative. "
        "Confidence is a float in [0,1]. No extra text."
    )
    user = f"TEXT:\n<<<\n{clip}\n>>>"

    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]

    buf = []
    for tok in chat_stream(messages, model=model_name):
        buf.append(tok)
    return "".join(buf)


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
