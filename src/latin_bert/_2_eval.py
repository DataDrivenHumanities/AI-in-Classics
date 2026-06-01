import torch
import json
from transformers import AutoModelForSequenceClassification
from bert_utils.tokenizer import LatinHFTokenizer
from pathlib import Path

# 1. SETUP
MODEL_PATH = "output/final_models/latin_bert_2026_04_07_06_29_14"
TOKENIZER_PATH = "models/bert_models/subword_tokenizer_latin/latin.subword.encoder"

LABEL_MAP = {0: "NEG", 1: "POS", 2: "NEU"}
RAW_MAP = {"LABEL_0": 0, "LABEL_1": 1, "LABEL_2": 2}


def run_dataset_eval():
    # Setup logging file in the model directory
    log_file_path = Path(MODEL_PATH) / "eval_results.txt"

    print("Initializing Tokenizer and Model...")
    tokenizer = LatinHFTokenizer(TOKENIZER_PATH)
    model = AutoModelForSequenceClassification.from_pretrained(MODEL_PATH, num_labels=3)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.to(device)
    model.eval()

    # 2. LOAD DATA MANUALLY
    data_path = "data/bert_data/eval2.jsonl"
    samples = []
    with open(data_path, "r", encoding="utf-8") as f:
        for line in f:
            samples.append(json.loads(line))

    # Open the log file for writing
    with open(log_file_path, "w", encoding="utf-8") as log_file:
        header = f"Loaded {len(samples)} samples. Starting inference...\n"
        table_head = f"{'SENTENCE':<55} | {'ACTUAL':<8} | {'PREDICTED':<10}\n"
        divider = "-" * 80 + "\n"

        # Print to console and log file
        print(header, end="")
        print(table_head, end="")
        print(divider, end="")

        log_file.write(header)
        log_file.write(table_head)
        log_file.write(divider)

        correct = 0

        with torch.no_grad():
            for item in samples:
                sentence = item["sentence"]
                actual_label = item["label"]

                inputs = tokenizer(
                    sentence, padding="max_length", max_length=128, return_tensors="pt"
                )

                input_ids = inputs["input_ids"].to(device)
                attention_mask = inputs["attention_mask"].to(device)

                outputs = model(input_ids=input_ids, attention_mask=attention_mask)
                pred_idx = torch.argmax(outputs.logits, dim=-1).item()

                if pred_idx == actual_label:
                    correct += 1

                # Format the output row
                display_text = (
                    (sentence[:52] + "..") if len(sentence) > 52 else sentence
                )
                status = "✓" if actual_label == pred_idx else "✗"
                row = f"{display_text:<55} | {LABEL_MAP[actual_label]:<8} | {LABEL_MAP[pred_idx]:<10} {status}\n"

                print(row, end="")
                log_file.write(row)

        accuracy = (correct / len(samples)) * 100
        footer = f"{divider}Final Accuracy: {accuracy:.2f}%\n"
        footer2 = f"{divider}Ammount Correct: {correct}/{len(samples)}\n"

        print(footer)
        print(footer2)
        log_file.write(footer)
        log_file.write(footer2)

    print(f"\nResults saved to: {log_file_path}")


if __name__ == "__main__":
    run_dataset_eval()
