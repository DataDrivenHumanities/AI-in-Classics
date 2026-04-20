# src/eval_single.py
import torch
from transformers import AutoModelForSequenceClassification
from bert_utils.tokenizer import LatinHFTokenizer

MODEL_PATH = "output/final_models/latin_bert_2026_04_07_06_29_14"
TOKENIZER_PATH = "models/bert_models/subword_tokenizer_latin/latin.subword.encoder"

LABEL_MAP = {0: "NEG", 1: "POS", 2: "NEU"}


def load_model():
    """Load and return the tokenizer, model, and device. Call once and reuse."""
    tokenizer = LatinHFTokenizer(TOKENIZER_PATH)
    model = AutoModelForSequenceClassification.from_pretrained(MODEL_PATH, num_labels=3)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.to(device)
    model.eval()
    return tokenizer, model, device


def predict(sentence: str, tokenizer, model, device) -> str:
    """Run inference on a single Latin sentence and return the predicted label."""
    inputs = tokenizer(
        sentence, padding="max_length", max_length=128, return_tensors="pt"
    )
    input_ids = inputs["input_ids"].to(device)
    attention_mask = inputs["attention_mask"].to(device)

    with torch.no_grad():
        outputs = model(input_ids=input_ids, attention_mask=attention_mask)

    pred_idx = torch.argmax(outputs.logits, dim=-1).item()
    return LABEL_MAP[pred_idx]


if __name__ == "__main__":
    tokenizer, model, device = load_model()

    test_sentence = "Vita eius erat nimis brevis."
    result = predict(test_sentence, tokenizer, model, device)
    print(f"Input:     {test_sentence}")
    print(f"Predicted: {result}")
