# src/app/sentiment_router.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional, Protocol, TypedDict, Any


class SentimentResult(TypedDict, total=False):
    engine: str
    label: str
    confidence: float
    scores: Dict[str, float]
    raw_model_output: str
    translation: Optional[str]
    analysis: Optional[Dict[str, Any]]


class SentimentProvider(Protocol):
    def analyze(
        self, text: str, *, model_id: Optional[str] = None
    ) -> SentimentResult: ...


class VADERSentimentProvider:
    """Uses vaderSentiment (fast)."""

    def __init__(self):
        try:
            from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer  # type: ignore
        except Exception as e:
            raise RuntimeError(
                "vaderSentiment is required for the 'builtin' engine. "
                "Install with: `poetry add vaderSentiment`"
            ) from e
        self._analyzer = SentimentIntensityAnalyzer()

    def analyze(self, text: str, *, model_id: Optional[str] = None) -> SentimentResult:
        vs = self._analyzer.polarity_scores(text or "")
        # Map VADER 'compound' to confidence-ish number in [0,1]
        compound = vs.get("compound", 0.0)
        label = (
            "positive"
            if compound >= 0.05
            else "negative" if compound <= -0.05 else "neutral"
        )
        confidence = abs(compound) + 0.0  # simple heuristic
        return {
            "engine": "builtin",
            "label": label,
            "confidence": round(confidence, 3),
            "scores": {
                "compound": compound,
                "pos": vs.get("pos", 0.0),
                "neu": vs.get("neu", 0.0),
                "neg": vs.get("neg", 0.0),
            },
            "translation": None,
            "analysis": {
                "heuristic": "vader",
                "thresholds": {"pos": 0.05, "neg": -0.05},
            },
        }


class LLMSentimentProvider:
    """
    Current providers ollama greek and latin.
    """

    def __init__(self):
        # robust import whether app_functions is under app/ or /src on path
        try:
            from app import app_functions as app_func  # type: ignore
        except Exception:
            import app_functions as app_func  # type: ignore
        self._f = app_func

    def analyze(self, text: str, *, model_id: Optional[str] = None) -> SentimentResult:
        if not model_id:
            model_id = "llama3.1"  # sensible default; override in API call or settings
        raw = self._f.llm_sentiment(text, model_id)
        parsed = self._f.parse_llm_json(raw) or {}
        label = str(parsed.get("label") or "unknown").lower()
        conf = parsed.get("confidence")
        try:
            confidence = float(conf) if conf is not None else 0.0
        except Exception:
            confidence = 0.0
        out: SentimentResult = {
            "engine": "model",
            "label": label,
            "confidence": confidence,
            "raw_model_output": raw,
            "translation": parsed.get("translation"),
            "analysis": parsed.get("analysis"),
        }
        # if the model returns scores, pass them through
        if isinstance(parsed.get("scores"), dict):
            out["scores"] = {
                k: float(v)
                for k, v in parsed["scores"].items()
                if isinstance(v, (int, float))
            }
        return out


@dataclass
class SentimentRouter:
    """Routes to builtin (VADER) or model (LLM)."""

    builtin_provider: Optional[VADERSentimentProvider] = None
    model_provider: Optional[LLMSentimentProvider] = None

    def analyze(
        self,
        text: str,
        *,
        engine: str = "builtin",
        model_id: Optional[str] = None,
    ) -> SentimentResult:
        engine = (engine or "builtin").lower()
        if engine == "builtin":
            if not self.builtin_provider:
                self.builtin_provider = VADERSentimentProvider()
            return self.builtin_provider.analyze(text, model_id=model_id)
        elif engine == "model":
            if not self.model_provider:
                self.model_provider = LLMSentimentProvider()
            return self.model_provider.analyze(text, model_id=model_id)
        else:
            raise ValueError(f"Unknown engine '{engine}'. Use 'builtin' or 'model'.")


def make_default_sentiment_router() -> SentimentRouter:
    return SentimentRouter()
