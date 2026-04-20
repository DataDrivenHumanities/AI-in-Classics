import gdown
from pathlib import Path

# --- output directories -----------------------------------------------------

BERT_DATA_DIR = Path("./data/bert_data")
MODELS_DIR = Path("./models/bert_models")
FINAL_MODELS_DIR = Path("./output/final_models/latin_bert_2026_04_07_06_29_14")

BERT_DATA_DIR.mkdir(parents=True, exist_ok=True)
MODELS_DIR.mkdir(parents=True, exist_ok=True)
FINAL_MODELS_DIR.mkdir(parents=True, exist_ok=True)

# --- downloads --------------------------------------------------------------

# Data
gdown.download_folder(
    url="https://drive.google.com/drive/folders/1iofIaF99-QxkDFMXNPRH3-aQCe1sYRJT",
    output=str(BERT_DATA_DIR),
    quiet=False,
)

# Base models
gdown.download_folder(
    url="https://drive.google.com/drive/folders/1bS-0IG1K9Y4C6P50P0ZHVVVJcESujpA8",
    output=str(MODELS_DIR),
    quiet=False,
)

# Latest trained model
gdown.download_folder(
    url="https://drive.google.com/drive/folders/1UXmSu22G-AaA1FL7tkOIHoMCVmshdJXa",
    output=str(FINAL_MODELS_DIR),
    quiet=False,
)

from cltk.data.fetch import FetchCorpus

FetchCorpus(language="lat").import_corpus("lat_models_cltk")
