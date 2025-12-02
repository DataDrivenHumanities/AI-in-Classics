from __future__ import annotations
from typing import Dict, Iterable, List, Optional, Tuple, Any
import os
import json
import re
import asyncio
import httpx

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")

try:
    import ollama
except Exception as e:
    raise RuntimeError(
        "The 'ollama' Python package is not installed. "
        "Install with 'poetry add ollama' or 'pip install ollama'."
    ) from e

try:
    import app.model_registry as model_cfg
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


def _coerce_result(obj: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "label": obj.get("label") or "neutral",
        "confidence": float(obj.get("confidence") or 0.5),
        "scores": {
            "positive": float(obj.get("scores", {}).get("positive", 0.25)),
            "negative": float(obj.get("scores", {}).get("negative", 0.25)),
            "neutral": float(obj.get("scores", {}).get("neutral", 0.5)),
        },
        "translation": obj.get("translation"),
        "analysis": obj.get("analysis") or {},
    }


async def generate_analysis_only(model: str, text: str, timeout_s: float = 45.0) -> Dict[str, Any]:
    prompt = (
        "Return ONLY JSON with a single key 'analysis' whose value is an object that explains the sentiment.\n"
        "Structure the 'analysis' object with keys: 'parts_of_speech' (array of {word, tag}), "
        "'notable_words' (array of {word, note}), 'rationale' (string), and 'score_explanation' (string).\n"
        "No extra keys. No prose outside JSON.\n\n"
        f"Text:\n{text}"
    )
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "format": "json",
        "raw": True,
        "options": {
            "temperature": 0.0,
            "num_predict": 512,
            "top_p": 0.9,
            "stop": [],
            "mirostat": 0,
            "repeat_penalty": 1.1,
        },
    }
    async with _make_client(timeout_s) as client:
        r = await client.post(f"{OLLAMA_HOST}/api/generate", json=payload)
        r.raise_for_status()
        data = r.json()
    raw = data.get("response") or ""
    try:
        parsed = json.loads(raw)
    except Exception:
        m = re.search(r"\{.*\}", raw, re.S)
        parsed = json.loads(m.group(0)) if m else {"analysis": {}}
    a = parsed.get("analysis") or {}
    if not isinstance(a, dict):
        a = {"rationale": str(a)}
    return {"analysis": a}


def ping(host: Optional[str] = None) -> bool:
    try:
        _ = ollama.list()
        return True
    except Exception:
        return False


def ensure_model(model: str) -> None:
    try:
        tags = {m["model"] for m in ollama.list().get("models", [])}
        if model not in tags:
            ollama.pull(model)
    except Exception:
        pass


def _make_client(timeout_s: float) -> httpx.AsyncClient:
    return httpx.AsyncClient(
        timeout=httpx.Timeout(connect=5.0, read=timeout_s, write=timeout_s, pool=5.0),
        limits=httpx.Limits(max_keepalive_connections=10, max_connections=10),
    )


async def _repair_json_via_model(
    raw_text: str,
    model: str,
    timeout_s: float,
) -> Optional[Dict[str, Any]]:
    prompt = (
        "You are a JSON linter. Given the following text, output ONLY a valid JSON object with exactly these keys: "
        '{"label":"positive|negative|neutral","confidence":number,'
        '"scores":{"positive":number,"negative":number,"neutral":number},'
        '"translation":string|null,"analysis":object|null}. '
        "If keys are missing, fill reasonable defaults. No extra keys. No prose.\n\n"
        f"Text:\n{raw_text}\n"
    )
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "format": "json",
        "raw": True,
        "options": {
            "temperature": 0.0,
            "num_predict": 768,
            "top_p": 0.9,
            "stop": [],
            "mirostat": 0,
        },
    }
    async with _make_client(timeout_s) as client:
        r = await client.post(f"{OLLAMA_HOST}/api/generate", json=payload)
        r.raise_for_status()
        data = r.json()
    repaired = data.get("response") or ""
    try:
        return json.loads(repaired)
    except Exception:
        m = re.search(r"\{.*\}", repaired, re.S)
        if m:
            try:
                return json.loads(m.group(0))
            except Exception:
                return None
        return None


def chat_once(
    prompt: str,
    *,
    model: str = DEFAULT_MODEL,
    system: Optional[str] = None,
    temperature: Optional[float] = None,
) -> str:
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


async def generate_json(
    model: str,
    prompt: str,
    *,
    temperature: float = 0.0,
    num_predict: int = 1024,
    top_p: float = 0.9,
    extra_options: Optional[Dict[str, Any]] = None,
    timeout_s: float = 60.0,
    retries: int = 1,
    raw: bool = True,
    out_format: str = "json",
) -> Tuple[Dict[str, Any], str]:
    base_payload: Dict[str, Any] = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "format": out_format,
        "raw": raw,
        "options": {
            "temperature": temperature,
            "num_predict": num_predict,
            "top_p": top_p,
            "mirostat": 0,
            "repeat_penalty": 1.0,
            "stop": [],
        },
    }
    if extra_options:
        base_payload["options"].update(extra_options)

    last_raw = ""
    attempt = 0
    async with _make_client(timeout_s) as client:
        while True:
            try:
                payload = dict(base_payload)
                if attempt > 0:
                    shrink = 0.5 ** attempt
                    payload["options"]["num_predict"] = max(256, int(num_predict * shrink))
                print(payload)
                r = await client.post(f"{OLLAMA_HOST}/api/generate", json=payload)
                print(r)
                r.raise_for_status()
                data = r.json()
                raw_text = data.get("response") or ""
                last_raw = raw_text

                try:
                    return _coerce_result(json.loads(raw_text)), raw_text
                except Exception:
                    m = re.search(r"\{.*\}", raw_text, re.S)
                    if m:
                        try:
                            return _coerce_result(json.loads(m.group(0))), raw_text
                        except Exception:
                            pass
                    repaired = await _repair_json_via_model(raw_text, model, timeout_s)
                    if repaired is not None:
                        return _coerce_result(repaired), raw_text
                    if attempt >= retries:
                        break
            except (httpx.ReadTimeout, httpx.ConnectTimeout, httpx.HTTPError):
                if attempt >= retries:
                    break
            attempt += 1
            await asyncio.sleep(0.5 * attempt)

    return _coerce_result({
        "label": "neutral",
        "confidence": 0.5,
        "scores": {"positive": 0.25, "negative": 0.25, "neutral": 0.5},
        "translation": None,
        "analysis": {},
    }), last_raw



async def translate_en(model: str, text: str) -> Optional[str]:
    prompt = (
        "Translate the text to concise English. "
        "Return ONLY the translation as plain text.\n\n"
        f"{text}"
    )
    async with httpx.AsyncClient(timeout=45) as client:
        r = await client.post(
            f"{OLLAMA_HOST}/api/generate",
            json={
                "model": model,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0.0, "num_predict": 256},
            },
        )
        r.raise_for_status()
        data = r.json()
    out = (data.get("response") or "").strip()
    return out or None


async def generate_json_minimal(
    model: str,
    text: str,
) -> Tuple[Dict[str, Any], str]:
    prompt = (
        "Return ONLY JSON with exactly these keys:\n"
        "{"
        '"label":"positive|negative|neutral",'
        '"translation": string|null'
        "}\n"
        f"Text:\n{text}"
    )
    return await generate_json(model, prompt, num_predict=256)


async def generate_text(
    model: str,
    prompt: str,
    *,
    temperature: float = 0.0,
    num_predict: int = 16,
) -> str:
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "raw": True,
        "options": {
            "temperature": temperature,
            "num_predict": num_predict,
            "top_p": 0.9,
            "stop": [],
            "mirostat": 0,
            "repeat_penalty": 1.0,
        },
    }
    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.post(f"{OLLAMA_HOST}/api/generate", json=payload)
        r.raise_for_status()
        data = r.json()
    return (data.get("response") or "").strip()


async def generate_json_with_analysis(
    model: str,
    prompt: str,
    *,
    temperature: float = 0.0,
    num_predict: int = 1024,
    top_p: float = 0.9,
    extra_options: Optional[Dict[str, Any]] = None,
    timeout_s: float = 60.0,
    retries: int = 1,
    force_raw: Optional[bool] = None,
    out_format: Optional[str] = None,
) -> Tuple[Dict[str, Any], str]:
    parsed, raw = await generate_json(
        model,
        prompt,
        temperature=temperature,
        num_predict=num_predict,
        top_p=top_p,
        extra_options=extra_options,
        timeout_s=timeout_s,
        retries=retries,
        raw=(True if force_raw is None else force_raw),
        out_format=(out_format or "json"),
    )

    if not parsed.get("analysis"):
        try:
            text_only = prompt.split("Text:", 1)[-1].strip()
            add = await generate_analysis_only(model, text_only, timeout_s=min(45.0, timeout_s))
            if add.get("analysis"):
                parsed["analysis"] = add["analysis"]
        except Exception:
            parsed.setdefault("analysis", {})
    return parsed, raw
