import os
import json
from pathlib import Path

import pytest

pytestmark = pytest.mark.no_ollama


def _load_fixture() -> dict:
    p = Path(__file__).with_name("LatinRagLexiconPassages.json")
    data = json.loads(p.read_text(encoding="utf-8"))
    assert isinstance(data, list) and data, "fixture must be a non-empty list"
    return data[0]


def test_latin_lexicon_annotator_smoke():
    repo_root = Path(__file__).resolve().parents[1]
    lila_root = repo_root / "src" / "Lemmatizer-LTN-LiLa"

    import sys

    sys.path.insert(0, str(lila_root))

    from rag.latin_lexicon_annotator import LatinLexiconAnnotator  # type: ignore

    fx = _load_fixture()
    text = str(fx["text"])
    expect = fx.get("expect") or {}

    try:
        with LatinLexiconAnnotator() as ann:
            res = ann.annotate(text)
    except ValueError as e:
        pytest.skip(str(e))

    cov = res.get("coverage") or {}
    token_count = cov.get("raw_token_count", cov.get("token_count", 0))
    assert token_count >= int(expect.get("min_token_count") or 0)

    neg = res.get("negators") or {}
    for w in expect.get("must_have_negators", []):
        assert neg.get(w, 0) > 0
