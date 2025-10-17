import pytest
from conftest import generate_ollama

PROMPT = """You are a sentiment classifier for Ancient Greek.
Reply with exactly one word: positive, negative, or neutral.
Sentence: Ὁ οὐρανὸς καλός ἐστιν.
Answer:"""

def test_greek_single(greek_model_name, greek_ready):
    if not greek_ready:
        pytest.xfail(
            f"Greek model '{greek_model_name}' not available. "
            f"Try: `ollama pull {greek_model_name}` and re-run."
        )
    res = generate_ollama(greek_model_name, PROMPT)
    if not res["ok"]:
        pytest.xfail(f"Ollama request failed: {res['raw']}")
    assert res["sentiment"] in {"positive", "negative", "neutral"}
