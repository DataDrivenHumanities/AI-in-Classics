# src/latin_bert/bert_service.py
# Wraps eval_single.py for use by the FastAPI backend.
# Lazy-loads the model on first call and reuses it across requests (singleton).
# Returns a dict shaped to match the "hugging face" engine response that
# renderHfTable() in the frontend already knows how to display.
#
# Lives alongside eval_single.py inside src/latin_bert/ so the relative
# import below is valid when FastAPI imports this as part of the app package.

from __future__ import annotations

import re
import threading
from typing import Any, Dict, List, Tuple

import torch
import torch.nn.functional as F

# Label index -> short string, matches LABEL_MAP in eval_single.py
LABEL_MAP = {0: "NEG", 1: "POS", 2: "NEU"}

# Singleton state -- lock protects concurrent first-calls
_lock = threading.Lock()
_tokenizer = None
_model = None
_device = None


def _get_model():
    global _tokenizer, _model, _device

    if _model is not None:
        return _tokenizer, _model, _device

    with _lock:
        if _model is not None:
            return _tokenizer, _model, _device

        import sys
        from pathlib import Path

        # _2_eval_single.py imports bert_utils as a top-level module,
        # which only resolves if src/latin_bert/ is on sys.path directly
        latin_bert_dir = str(Path(__file__).parent)
        if latin_bert_dir not in sys.path:
            sys.path.insert(0, latin_bert_dir)

        from latin_bert._2_eval_single import load_model  # type: ignore

        _tokenizer, _model, _device = load_model()

    return _tokenizer, _model, _device


def _split_sentences(text: str) -> List[str]:
    """Split on .!? boundaries, filtering empty strings."""
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    return [s.strip() for s in parts if s.strip()]


def _predict_with_scores(
    sentence: str,
    tokenizer,
    model,
    device,
) -> Tuple[str, float, Dict[str, float]]:
    """
    Run inference on a single sentence.

    LatinHFTokenizer.__call__ always returns batched tensors of shape
    [batch_size, max_length] even for a single string input, so logits
    come out as [1, num_labels]. squeeze(0) reduces to [num_labels] before softmax.
    """
    inputs = tokenizer(
        sentence, padding="max_length", max_length=128, return_tensors="pt"
    )
    input_ids = inputs["input_ids"].to(device)  # [1, 128]
    attention_mask = inputs["attention_mask"].to(device)  # [1, 128]

    with torch.no_grad():
        outputs = model(input_ids=input_ids, attention_mask=attention_mask)

    # logits: [1, 3] -> squeeze to [3] before softmax
    logits = outputs.logits.squeeze(0)  # [3]
    probs = F.softmax(logits, dim=-1)  # [3]

    pred_idx = int(torch.argmax(probs).item())
    label = LABEL_MAP[pred_idx]
    confidence = float(probs[pred_idx].item())
    scores_by_label = {LABEL_MAP[i]: float(p.item()) for i, p in enumerate(probs)}

    return label, confidence, scores_by_label


def run_bert_sentiment(text: str) -> Dict[str, Any]:
    """
    Run the Latin BERT model over every sentence in `text`.

    Returns a dict with engine="hugging face" so the frontend routes it
    through renderHfTable without any frontend changes:

        {
          "engine": "hugging face",
          "labels and scores by sentence": [
            {"sentence": "...", "label": "POS", "score": 0.92, "all_scores": {...}},
            ...
          ]
        }
    """
    tokenizer, model, device = _get_model()

    sentences = _split_sentences(text)
    if not sentences:
        # Fallback: treat the whole input as one item if splitting yields nothing
        sentences = [text.strip()]

    results: List[Dict[str, Any]] = []
    for sent in sentences:
        label, confidence, all_scores = _predict_with_scores(
            sent, tokenizer, model, device
        )
        results.append(
            {
                "sentence": sent,
                "label": label,
                "score": confidence,
                # Full softmax distribution -- available for future display/export
                "all_scores": all_scores,
            }
        )

    return {
        "engine": "hugging face",
        "labels and scores by sentence": results,
    }
