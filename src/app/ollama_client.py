from __future__ import annotations
from typing import Dict, Iterable, List, Optional
import os

try:
    import ollama
except Exception as e:
    raise RuntimeError(
        "The 'ollama' Python package is not installed. "
        "Install with 'poetry add ollama' or 'pip install ollama'."
    ) from e


try:
    import model_registry as model_cfg
except Exception:
    model_cfg = None


def _determine_default_model() -> str:
    env_override = os.getenv("TP_MODEL")
    if env_override:
        return env_override
    if model_cfg is not None and hasattr(model_cfg, "get_registry"):
        try:
            return model_cfg.get_registry().default_model_id
        except getattr(model_cfg, "ModelRegistryError", Exception):
            pass
    return "latin_model:1.0.0"

DEFAULT_MODEL = _determine_default_model()

def ping(host: Optional[str] = None) -> bool:
    """
    health check against Ollama server.
    Returns True if the server responds
    """
    try:
        _ = ollama.list()
        return True
    except Exception:
        return False


def ensure_model(model: str) -> None:
    """
    Ensure a model is available locally.
    For hub models this will `pull` if missing.
    For local Modelfile builds, you must have run `ollama create` already.
    """
    try:
        tags = {m["model"] for m in ollama.list().get("models", [])}
        if model not in tags:
            ollama.pull(model)
    except Exception:
        pass


def chat_once(
    prompt: str,
    *,
    model: str = DEFAULT_MODEL,
    system: Optional[str] = None,
    temperature: Optional[float] = None,
) -> str:
    """
    Simple, non-streaming convenience wrapper.
    """
    messages: List[Dict[str, str]] = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    kwargs = {"model": model, "messages": messages}
    if temperature is not None:
        kwargs["options"] = {"temperature": temperature}

    try:
        ensure_model(model)
        resp = ollama.chat(**kwargs)
        return resp["message"]["content"]
    except Exception as e:
        raise RuntimeError(
            f"Ollama chat failed. Is 'ollama serve' running and is the model '{model}' available?\n{e}"
        ) from e


def chat_stream(
    messages: List[Dict[str, str]],
    *,
    model: str = DEFAULT_MODEL,
    temperature: Optional[float] = None,
) -> Iterable[str]:
    """
    Generator that yields tokens incrementally.
    messages: [{"role": "system"|"user"|"assistant", "content": "..."}]
    """
    kwargs = {"model": model, "messages": messages, "stream": True}
    if temperature is not None:
        kwargs["options"] = {"temperature": temperature}

    ensure_model(model)
    try:
        for chunk in ollama.chat(**kwargs):
            yield chunk["message"]["content"]
    except Exception as e:
        raise RuntimeError(
            f"Ollama streaming failed. Check that the daemon is running (`ollama serve`) "
            f"and that the model '{model}' exists.\n{e}"
        ) from e
