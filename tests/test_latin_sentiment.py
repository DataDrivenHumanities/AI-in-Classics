import pytest
from conftest import generate_ollama

PROMPT = """You are a sentiment classifier for Latin.
Reply with exactly one word: positive, negative, or neutral.
Sentence: Caelum pulchrum est.
Answer:"""


def test_latin_single(latin_model_name, latin_ready):
    if not latin_ready:
        pytest.xfail(
            f"Latin model '{latin_model_name}' not available. "
            f"Try: `ollama pull {latin_model_name}` and re-run."
        )
    res = generate_ollama(latin_model_name, PROMPT)
    if not res["ok"]:
        pytest.xfail(f"Ollama request failed: {res['raw']}")
    # We keep the first test forgiving: just ensure the model returns one of the labels
    assert res["sentiment"] in {"positive", "negative", "neutral"}
