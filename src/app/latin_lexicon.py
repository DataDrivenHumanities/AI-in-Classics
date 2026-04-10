from __future__ import annotations

import os
import sys
from functools import lru_cache
from pathlib import Path
from typing import Optional, Any


BASE_DIR = Path(__file__).resolve().parents[2]


@lru_cache(maxsize=1)
def latin_lexicon_import_root() -> Optional[Path]:
    root = BASE_DIR / "src" / "Lemmatizer-LTN-LiLa"
    return root if root.exists() else None


def resolve_database_url() -> str:
    """
    Resolve DATABASE_URL in a Streamlit-free way.

    FastAPI typically relies on environment variables; we also best-effort load
    `.env` from cwd or repo root for local dev ergonomics.
    """
    try:
        from dotenv import load_dotenv  # type: ignore

        for env_path in (Path.cwd() / ".env", BASE_DIR / ".env"):
            if env_path.exists():
                load_dotenv(env_path)
                break
    except Exception:
        pass
    return (os.getenv("DATABASE_URL") or "").strip()


def make_latin_lexicon_annotator(dsn: str) -> Any:
    lex_root = latin_lexicon_import_root()
    if lex_root is None:
        raise RuntimeError(
            "Missing src/Lemmatizer-LTN-LiLa; cannot import LatinLexiconAnnotator."
        )
    if str(lex_root) not in sys.path:
        sys.path.insert(0, str(lex_root))

    from rag.latin_lexicon_annotator import (  # type: ignore
        LatinLexiconAnnotator,
        LatinLexiconAnnotatorConfig,
    )

    return LatinLexiconAnnotator(
        dsn=dsn,
        config=LatinLexiconAnnotatorConfig(top_k=12),
    )

