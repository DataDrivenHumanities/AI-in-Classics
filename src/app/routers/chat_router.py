# src/app/chat_router.py
from __future__ import annotations

from dataclasses import dataclass
from typing import (
    Dict,
    Generator,
    Iterable,
    List,
    Literal,
    Optional,
    Protocol,
    Tuple,
    Union,
)


Role = Literal["system", "user", "assistant"]
Message = Dict[str, str]


# ---------- Provider Protocols ----------


class ChatProvider(Protocol):
    """interface for chat providers."""

    def complete(
        self,
        messages: List[Message],
        *,
        temperature: float = 0.2,
        max_tokens: Optional[int] = None,
        **kwargs,
    ) -> str: ...

    def stream(
        self,
        messages: List[Message],
        *,
        temperature: float = 0.2,
        max_tokens: Optional[int] = None,
        **kwargs,
    ) -> Iterable[str]: ...


# ---------- Concrete Providers ----------


class OllamaProvider(ChatProvider):
    """
    Wraps the ollama client.
    Expects: from app.ollama_client import chat_stream
    """

    def __init__(self, model_id: str):
        self.model_id = model_id
        try:
            from app.ollama_client import chat_stream  # type: ignore
        except Exception:
            from ollama_client import chat_stream  # type: ignore
        self._chat_stream = chat_stream

    def complete(
        self,
        messages: List[Message],
        *,
        temperature: float = 0.2,
        max_tokens: Optional[int] = None,
        **kwargs,
    ) -> str:
        chunks = []
        for token in self.stream(
            messages, temperature=temperature, max_tokens=max_tokens, **kwargs
        ):
            chunks.append(token)
        return "".join(chunks)

    def stream(
        self,
        messages: List[Message],
        *,
        temperature: float = 0.2,
        max_tokens: Optional[int] = None,
        **kwargs,
    ) -> Iterable[str]:
        yield from self._chat_stream(
            messages,
            model=self.model_id,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs,
        )


class OpenAIProvider(ChatProvider):
    def __init__(self, model_id: str, api_key: Optional[str] = None):
        self.model_id = model_id
        self.api_key = api_key

    def complete(
        self,
        messages: List[Message],
        *,
        temperature: float = 0.2,
        max_tokens: Optional[int] = None,
        **kwargs,
    ) -> str:
        raise NotImplementedError("OpenAI provider not configured yet.")

    def stream(
        self,
        messages: List[Message],
        *,
        temperature: float = 0.2,
        max_tokens: Optional[int] = None,
        **kwargs,
    ) -> Iterable[str]:
        raise NotImplementedError("OpenAI provider not configured yet.")


# ---------- Router ----------


@dataclass
class RouteDecision:
    provider_key: str
    model_id: str


class ChatRouter:
    """
    Routes chat to the appropriate provider based on model_id (and optionally prompt).
    Register providers with human-friendly keys (e.g., 'ollama', 'openai').
    """

    def __init__(self):
        self._providers: Dict[str, ChatProvider] = {}
        self._model_to_provider: Dict[str, str] = {}

    # ----- Registration -----

    def register_provider(self, key: str, provider: ChatProvider) -> None:
        """Register a provider by a short key."""
        self._providers[key] = provider

    def bind_model(self, model_id: str, provider_key: str) -> None:
        """Bind a model identifier to a provider key."""
        if provider_key not in self._providers:
            raise KeyError(f"Provider '{provider_key}' has not been registered.")
        self._model_to_provider[model_id] = provider_key

    # ----- Routing policy -----

    def decide(
        self,
        model_id: str,
        messages: List[Message],
        *,
        prompt: Optional[str] = None,
    ) -> RouteDecision:
        """
        Simple policy:
        - If model bound explicitly, use that provider.
        - Else infer by prefix convention.
        """
        if model_id in self._model_to_provider:
            return RouteDecision(self._model_to_provider[model_id], model_id)

        # Heuristics: allow prefixes like "ollama/llama3", "openai/gpt-4o-mini"
        lowered = model_id.lower()
        if lowered.startswith("ollama/") or lowered.startswith("local/"):
            return RouteDecision(
                "ollama", model_id.split("/", 1)[1] if "/" in model_id else model_id
            )
        if lowered.startswith("openai/"):
            return RouteDecision("openai", model_id.split("/", 1)[1])

        # Default fallback (local)
        return RouteDecision("ollama", model_id)

    # ----- Public  -----

    def respond_once(
        self,
        model_id: str,
        messages: List[Message],
        *,
        temperature: float = 0.2,
        max_tokens: Optional[int] = None,
        stream: bool = False,
        **kwargs,
    ) -> Union[str, Iterable[str]]:
        decision = self.decide(model_id, messages)
        provider = self._providers.get(decision.provider_key)
        if provider is None:
            raise KeyError(f"No provider registered for key '{decision.provider_key}'")

        kwargs.setdefault("model", decision.model_id)

        if stream:
            return provider.stream(
                messages, temperature=temperature, max_tokens=max_tokens, **kwargs
            )
        return provider.complete(
            messages, temperature=temperature, max_tokens=max_tokens, **kwargs
        )

    def multi_turn(
        self,
        model_id: str,
        seed_messages: List[Message],
        *,
        rounds: int = 2,
        followup_prompt_fn=None,
        temperature: float = 0.2,
        max_tokens: Optional[int] = None,
        **kwargs,
    ) -> Tuple[str, List[Message]]:
        """
        Simple refinement loop: call the model repeatedly with a generated follow-up prompt.
        Returns final text and the full conversation transcript.
        """
        messages = list(seed_messages)
        text = self.respond_once(
            model_id,
            messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=False,
            **kwargs,
        )
        if not isinstance(text, str):
            text = "".join(list(text))

        messages.append({"role": "assistant", "content": text})

        for _ in range(rounds - 1):
            follow_user = (
                followup_prompt_fn(text, messages)
                if followup_prompt_fn
                else "Refine your last answer."
            )
            messages.append({"role": "user", "content": follow_user})
            text = self.respond_once(
                model_id,
                messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=False,
                **kwargs,
            )
            if not isinstance(text, str):
                text = "".join(list(text))
            messages.append({"role": "assistant", "content": text})

        return text, messages


# ---------- Factory ----------


def make_default_router(default_ollama_model: str) -> ChatRouter:
    """
    Create a router with an Ollama provider and bind a default local model.
    """
    router = ChatRouter()
    # Register a single Ollama provider keyed as 'ollama'. The model is passed per-call.
    router.register_provider("ollama", OllamaProvider(model_id=default_ollama_model))
    # Bind common ids you use in the UI/registry to 'ollama'
    router.bind_model(default_ollama_model, "ollama")
    # You can add more binds like:
    # router.bind_model("ollama/llama3.1", "ollama")
    # router.register_provider("openai", OpenAIProvider("gpt-4o-mini", api_key=os.getenv("OPENAI_API_KEY")))
    return router
