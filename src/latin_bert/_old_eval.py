import sys

sys.stdout.reconfigure(line_buffering=True)

import torch
from datasets import load_dataset
from transformers import pipeline
import evaluate
from transformers import AutoTokenizer, AutoModelForSequenceClassification
from bert_utils.tokenizer import LatinHFTokenizer
from tensor2tensor.data_generators import text_encoder
from pathlib import Path
import time


def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


# --- Device check ---
log("Checking device...")
print(torch.cuda.is_available())
print(torch.cuda.get_device_name(0) if torch.cuda.is_available() else "No GPU")
DEVICE = 0 if torch.cuda.is_available() else -1
log(f"Using device: {'GPU (cuda:0)' if DEVICE == 0 else 'CPU'}")

# --- Model/tokenizer config ---
if False:
    MODEL_PATH = (
        "output_models/bert-base-multilingual-cased_2026_02_18_23_38_1771475883"
    )
    TOKENIZER_PATH = "bert-base-multilingual-cased"
    log(f"Loading mBERT tokenizer from {TOKENIZER_PATH}...")
    TOKENIZER = AutoTokenizer.from_pretrained(TOKENIZER_PATH)
else:
    MODEL_PATH = "output/final_models/latin_bert_2026_04_07_03_19_1775546384"
    TOKENIZER_PATH = "models/subword_tokenizer_latin/latin.subword.encoder"
    log(f"Loading LatinHFTokenizer from {TOKENIZER_PATH}...")
    TOKENIZER = LatinHFTokenizer(TOKENIZER_PATH)

log("Tokenizer loaded.")

# --- Sanity check tokenizer ---
log("Running tokenizer sanity check...")
test_out = TOKENIZER("arma virumque cano")
log(f"Tokenizer output keys: {list(test_out.keys())}")
log(f"Sample input_ids: {test_out['input_ids'][:10]}")

# --- Load dataset ---
DATA_PATH = "data/bert_data/eval.jsonl"
log(f"Loading dataset from {DATA_PATH}...")
dataset = load_dataset("json", data_files=DATA_PATH, split="train")
log(f"Dataset loaded. {len(dataset)} examples.")
log(f"Columns: {dataset.column_names}")
log(f"First example: {dataset[0]}")

# --- Load model ---
log(f"Loading model from {MODEL_PATH} (this may take a while)...")
t0 = time.time()
model = AutoModelForSequenceClassification.from_pretrained(MODEL_PATH, num_labels=3)
log(f"Model loaded in {time.time() - t0:.1f}s.")

log("Setting model to eval mode...")
model.eval()
log("Model in eval mode.")

# --- Build pipeline ---
log("Building pipeline...")
t0 = time.time()
pipe = pipeline(
    "text-classification",
    model=model,
    tokenizer=TOKENIZER,
    device=DEVICE,
)
log(f"Pipeline ready in {time.time() - t0:.1f}s.")

# --- Sanity check pipeline ---
log("Running pipeline sanity check...")
test_result = pipe("arma virumque cano")
log(f"Pipeline sanity check output: {test_result}")

# --- Metrics and label map ---
accuracy_metric = evaluate.load("accuracy")
label_map = {"LABEL_0": 0, "LABEL_1": 1, "LABEL_2": 2}

batch_count = [0]  # list so the closure can mutate it


def evaluate_model(examples):
    results = pipe(examples["sentence"])
    predictions = [label_map[res["label"]] for res in results]
    batch_count[0] += 1
    if batch_count[0] % 10 == 0:
        log(f"  ...processed {batch_count[0] * 8} examples so far")
    return {"predictions": predictions}


# --- Run inference ---
log("Starting inference...")
t0 = time.time()
results_ds = dataset.map(evaluate_model, batched=True, batch_size=8)
log(f"Inference complete in {time.time() - t0:.1f}s.")

# --- Compute metrics ---
log("Computing accuracy...")
final_score = accuracy_metric.compute(
    predictions=results_ds["predictions"],
    references=results_ds["label"],
)
log(f"Accuracy computed: {final_score}")

# --- Print results table ---
human_labels = {0: "NEG", 1: "POS", 2: "NEU"}

print(f"\n{'#'*20} DATASET PREDICTIONS {'#'*20}")
print(f"{Path(MODEL_PATH).name}")
print(f"{'SENTENCE':<55} | {'ACTUAL':<8} | {'PREDICTED':<10}")
print("-" * 80)

for row in results_ds:
    sentence = row["sentence"]
    actual = row["label"]
    predicted = row["predictions"]

    display_text = (sentence[:52] + "..") if len(sentence) > 52 else sentence
    actual_str = human_labels.get(actual, str(actual))
    pred_str = human_labels.get(predicted, str(predicted))
    status = "✓" if actual == predicted else "✗"

    print(f"{display_text:<55} | {actual_str:<8} | {pred_str:<10} {status}")

print("-" * 80)
print(f"Total processed: {len(results_ds)}")
print(f"Final Accuracy on Dataset: {final_score['accuracy'] * 100:.2f}%\n")
