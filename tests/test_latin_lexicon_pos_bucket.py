from __future__ import annotations

from pathlib import Path

import pytest


pytestmark = pytest.mark.no_ollama


def test_pos_bucket_pronoun_is_not_noun():
    repo_root = Path(__file__).resolve().parents[1]
    lila_root = repo_root / "src" / "Lemmatizer-LTN-LiLa"

    import sys

    sys.path.insert(0, str(lila_root))

    from rag.latin_lexicon_annotator import _pos_bucket_from_scraped  # type: ignore

    assert _pos_bucket_from_scraped("demonstrative pronoun") == "other"
    assert _pos_bucket_from_scraped("relative pronoun") == "other"
    assert _pos_bucket_from_scraped("personal pronoun") == "other"
