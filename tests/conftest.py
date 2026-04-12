# tests/conftest.py
import os
import re
import requests
import pytest
from typing import List, Optional  # <-- add this

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
TIMEOUT_SEC = float(os.getenv("OLLAMA_TIMEOUT", "10"))
SENTIMENT_RE = re.compile(r"\b(positive|negative|neutral)\b", re.IGNORECASE)
_OLLAMA_OK = None


def _get(path: str):
    return requests.get(f"{OLLAMA_URL}{path}", timeout=TIMEOUT_SEC)


def _post(path: str, payload: dict):
    return requests.post(f"{OLLAMA_URL}{path}", json=payload, timeout=TIMEOUT_SEC)


def ping_ollama() -> bool:
    try:
        _get("/")
        return True
    except Exception:
        return False


def list_models() -> List[str]:  # <-- List[str] not list[str]
    try:
        r = _get("/api/tags")
        if r.status_code != 200:
            return []
        data = r.json() or {}
        return [m.get("name") for m in data.get("models", []) if m.get("name")]
    except Exception:
        return []


def choose_model(
    env_var: str, keywords: List[str]
) -> Optional[str]:  # <-- Optional[str]
    """1) If ENV is set, use it. 2) else first local model containing any keyword."""
    forced = os.getenv(env_var)
    if forced:
        return forced
    names = [n.lower() for n in list_models()]
    original = list_models()
    for idx, n in enumerate(names):
        if any(k in n for k in keywords):
            return original[idx]
    return None


def generate_ollama(model: str, prompt: str) -> dict:
    payload = {
        "model": model,
        "prompt": prompt.strip(),
        "stream": False,
        "options": {
            "temperature": 0.0,
            "top_p": 0.0,
            "repeat_penalty": 1.0,
            "num_predict": 16,
        },
    }
    try:
        r = _post("/api/generate", payload)
        if r.status_code != 200:
            return {"ok": False, "text": "", "raw": r.text, "sentiment": "neutral"}
        data = r.json()
        text = (data.get("response") or "").strip()
        m = SENTIMENT_RE.search(text)
        return {
            "ok": True,
            "text": text,
            "raw": data,
            "sentiment": m.group(1).lower() if m else "neutral",
        }
    except Exception as e:
        return {"ok": False, "text": "", "raw": str(e), "sentiment": "neutral"}


def _ollama_ok() -> bool:
    global _OLLAMA_OK
    if _OLLAMA_OK is None:
        _OLLAMA_OK = ping_ollama()
    return bool(_OLLAMA_OK)


@pytest.fixture(autouse=True)
def _require_ollama(request):
    """
    Default test suite assumes Ollama is available.

    Tests that don't need it can opt out with:
      @pytest.mark.no_ollama
    """
    if request.node.get_closest_marker("no_ollama") is not None:
        return
    if not _ollama_ok():
        pytest.skip(f"Ollama not reachable at {OLLAMA_URL}. Start it with `ollama serve` and re-run.")


@pytest.fixture(scope="session")
def latin_model_name() -> Optional[str]:  # <-- Optional here too
    return choose_model("LATIN_TAG", ["latin", "lat"])


@pytest.fixture(scope="session")
def greek_model_name() -> Optional[str]:  # <-- Optional here too
    return choose_model("GREEK_TAG", ["greek", "grc", "hellenic"])


@pytest.fixture(scope="session")
def latin_ready(latin_model_name) -> bool:
    return bool(latin_model_name)


@pytest.fixture(scope="session")
def greek_ready(greek_model_name) -> bool:
    return bool(greek_model_name)


def pytest_report_header(config):
    from .conftest import choose_model

    latin = os.getenv("LATIN_TAG") or choose_model("LATIN_TAG", ["latin", "lat"])
    greek = os.getenv("GREEK_TAG") or choose_model(
        "GREEK_TAG", ["greek", "grc", "hellenic"]
    )
    return [
        f"Ollama URL: {OLLAMA_URL}",
        f"Latin model: {latin or 'not found'}",
        f"Greek model: {greek or 'not found'}",
    ]
