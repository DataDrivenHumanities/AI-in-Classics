# tests/test_greek_sentiment.py
import pytest
from conftest import generate_ollama

PROMPT_TEMPLATE = """You are a sentiment classifier for Ancient Greek.
Reply with exactly one word: positive, negative, or neutral.
Sentence: {s}
Answer:"""

GREEK_DATA = [
    "Ὁ οὐρανὸς καλός ἐστιν.",      # positive
    "Ὁ παῖς κακὸς μαθητής ἐστιν.",  # negative
    "Οὐ μέλει μοι.",                # negative
    "Οἱ πολῖται χαίρουσιν.",        # positive
    "Οὔτε καλόν οὔτε κακόν ἐστιν.",  # neutral
]


@pytest.mark.parametrize("s", GREEK_DATA, ids=GREEK_DATA)
def test_greek_sentences(greek_model_name, greek_ready, s):
    if not greek_ready:
        pytest.xfail(
            f"Greek model '{greek_model_name}' not available. "
            f"Set GREEK_TAG or create the model and re-run."
        )
    res = generate_ollama(greek_model_name, PROMPT_TEMPLATE.format(s=s))
    if not res["ok"]:
        pytest.xfail(f"Ollama request failed: {res['raw']}")
    assert res["sentiment"] in {"positive", "negative", "neutral"}
