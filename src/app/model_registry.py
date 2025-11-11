"""Utilities for managing configured language models.

The app historically hard-coded the available Ollama model tags. This module
provides a small registry abstraction backed by ``model_registry.json`` so that
new models can be added without touching application code. The registry is
lightweight, pure-Python, and has no third-party dependencies so it can be used
both inside Streamlit callbacks and in utility scripts.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence
import json
import os

REGISTRY_ENV_VAR = "TP_MODEL_REGISTRY"
_REGISTRY_FILENAME = "model_registry.json"
_REG_PATH = Path(__file__).with_name("model_registry.json")


class ModelRegistryError(RuntimeError):
    """Raised when the model registry configuration is invalid."""


@dataclass
class ModelInfo:
    """Description of a single language model entry."""

    model_id: str
    name: str
    description: str = ""
    provider: str = "ollama"
    available: bool = True
    tags: Sequence[str] = field(default_factory=tuple)
    metadata: Dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        # Normalise to tuples/dicts so downstream code can rely on immutability-like
        # behaviour even though the dataclass itself isn't frozen.
        self.tags = tuple(self.tags)
        self.metadata = dict(self.metadata)

    @property
    def display_label(self) -> str:
        """Return a human-friendly label suitable for UI widgets."""

        label = self.name or self.model_id
        if not self.available:
            label = f"{label} (coming soon)"
        return label


class ModelRegistry:
    """Container for all configured models."""

    def __init__(
        self, models: Sequence[ModelInfo], default: Optional[str] = None
    ) -> None:
        if not models:
            raise ModelRegistryError(
                "Model registry is empty; add at least one model entry."
            )

        self._ordered: List[ModelInfo] = list(models)
        self._models_by_id: Dict[str, ModelInfo] = {m.model_id: m for m in models}
        if len(self._models_by_id) != len(self._ordered):
            raise ModelRegistryError(
                "Duplicate model identifiers detected in registry."
            )

        default_id = default
        if default_id not in self._models_by_id:
            default_id = None
        if default_id is None:
            default_id = next((m.model_id for m in self._ordered if m.available), None)
        if default_id is None:
            # If everything is marked unavailable, fall back to the first configured
            # item so the UI can still render and show a warning to the user.
            default_id = self._ordered[0].model_id
        self._default_id = default_id

    def all_models(self) -> List[ModelInfo]:
        """Return every configured model in declaration order."""

        return list(self._ordered)

    def available_models(self) -> List[ModelInfo]:
        """Return models flagged as available."""

        return [m for m in self._ordered if m.available]

    def upcoming_models(self) -> List[ModelInfo]:
        """Return models that are configured but not yet available."""

        return [m for m in self._ordered if not m.available]

    @property
    def default_model_id(self) -> str:
        return self._default_id

    def default_model(self) -> ModelInfo:
        return self._models_by_id[self._default_id]

    def get(self, model_id: str) -> ModelInfo:
        try:
            return self._models_by_id[model_id]
        except KeyError as exc:  # pragma: no cover - defensive programming
            raise ModelRegistryError(
                f"Model '{model_id}' is not defined in the registry."
            ) from exc

    @staticmethod
    def index_for(model_id: str, pool: Sequence[ModelInfo]) -> int:
        for idx, model in enumerate(pool):
            if model.model_id == model_id:
                return idx
        return 0


def _resolve_registry_path(path: Optional[str] = None) -> Path:
    if path:
        return Path(path).expanduser().resolve()
    env_path = os.getenv(REGISTRY_ENV_VAR)
    if env_path:
        return Path(env_path).expanduser().resolve()
    return Path(__file__).resolve().with_name(_REGISTRY_FILENAME)


def _load_registry_from_path(path: Path) -> ModelRegistry:
    if not path.exists():
        raise ModelRegistryError(f"Registry file not found: {path}")
    with path.open("r", encoding="utf-8") as fh:
        raw = json.load(fh)

    entries = raw.get("models") or []
    models = [
        ModelInfo(
            model_id=item.get("id") or item.get("model_id") or "",
            name=item.get("name") or item.get("label") or "",
            description=item.get("description", ""),
            provider=item.get("provider", "ollama"),
            available=bool(item.get("available", True)),
            tags=item.get("tags", ()),
            metadata=item.get("metadata", {}),
        )
        for item in entries
    ]

    models = [m for m in models if m.model_id]
    if not models:
        raise ModelRegistryError(
            "Registry file is present but does not define any models."
        )

    default = raw.get("default")
    return ModelRegistry(models, default)


@lru_cache(maxsize=4)
def _cached_registry(path: str) -> ModelRegistry:
    return _load_registry_from_path(Path(path))


def get_registry(path: Optional[str] = None) -> ModelRegistry:
    """Return the shared :class:`ModelRegistry` instance."""

    resolved = _resolve_registry_path(path)
    try:
        return _cached_registry(str(resolved))
    except ModelRegistryError:
        raise
    except Exception as exc:  # pragma: no cover - unexpected failure
        raise ModelRegistryError(
            f"Failed to load model registry at {resolved}: {exc}"
        ) from exc


def refresh_registry(path: Optional[str] = None) -> ModelRegistry:
    """Force reloading the registry (e.g., after editing the JSON file)."""

    resolved = _resolve_registry_path(path)
    _cached_registry.cache_clear()
    return get_registry(str(resolved))


def available_model_ids() -> Iterable[str]:
    """Convenience helper used by callers that only need the model identifiers."""

    registry = get_registry()
    return [model.model_id for model in registry.available_models()]


def resolve_model(preferred: Optional[str]) -> str:
    data = json.loads(_REG_PATH.read_text(encoding="utf-8"))
    default_id = data.get("default") or "latin_model:1.0.0"
    models = {m["id"]: m for m in data.get("models", [])}
    if preferred and preferred in models and models[preferred].get("available", False):
        return preferred
    if default_id in models and models[default_id].get("available", False):
        return default_id
    for m in data.get("models", []):
        if m.get("available", False):
            return m["id"]
    return default_id
