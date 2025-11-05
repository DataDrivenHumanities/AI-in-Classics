from __future__ import annotations

import os
import json
import time
import asyncio
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx
from fastapi import APIRouter


class ProbingRouter:
    def __init__(
        self,
        *,
        ollama_host: Optional[str] = None,
        registry_path: Optional[Path] = None,
        max_concurrency: int = 3,
        probe_timeout_s: float = 8.0,
        tags_timeout_s: float = 5.0,
    ) -> None:
        self.ollama_host = ollama_host or os.getenv(
            "OLLAMA_HOST", "http://localhost:11434"
        )
        self.registry_path = registry_path or self._default_registry_path()
        self.max_concurrency = max_concurrency
        self.probe_timeout_s = probe_timeout_s
        self.tags_timeout_s = tags_timeout_s

        self.router = APIRouter()
        self.router.add_api_route(
            "/models/registry", self.get_models_registry, methods=["GET"]
        )
        self.router.add_api_route(
            "/models/status", self.get_models_status, methods=["GET"]
        )

    def _default_registry_path(self) -> Path:
        here = Path(__file__).resolve()
        candidates = [
            here.parent.parent / "model_registry.json",
            here.parent / "model_registry.json",
            Path.cwd() / "model_registry.json",
        ]
        for p in candidates:
            if p.exists():
                return p
        return candidates[0]

    def _load_registry(self) -> Dict[str, Any]:
        try:
            if self.registry_path.exists():
                return json.loads(self.registry_path.read_text(encoding="utf-8"))
        except Exception:
            pass
        return {"models": [], "default": None}

    async def _ollama_tags(self, client: httpx.AsyncClient) -> List[str]:
        try:
            r = await client.get(
                f"{self.ollama_host}/api/tags", timeout=self.tags_timeout_s
            )
            r.raise_for_status()
            data = r.json() or {}
            return [m.get("name") for m in data.get("models", []) if m.get("name")]
        except Exception:
            return []

    async def _probe_model(
        self, client: httpx.AsyncClient, model_id: str
    ) -> Dict[str, Any]:
        start = time.monotonic()
        try:
            payload = {
                "model": model_id,
                "prompt": "ok",
                "stream": False,
                "raw": True,
                "options": {"num_predict": 1, "temperature": 0.0, "stop": []},
            }
            r = await client.post(
                f"{self.ollama_host}/api/generate",
                json=payload,
                timeout=self.probe_timeout_s,
            )
            r.raise_for_status()
            _ = r.json()
            latency = int((time.monotonic() - start) * 1000)
            return {"available": True, "latency_ms": latency}
        except Exception:
            return {"available": False, "latency_ms": None}

    async def get_models_registry(self) -> Dict[str, Any]:
        reg = self._load_registry()
        return reg

    async def get_models_status(self) -> Dict[str, Any]:
        reg = self._load_registry()
        models = reg.get("models", [])
        default_id = reg.get("default")

        results: List[Dict[str, Any]] = []
        async with httpx.AsyncClient() as client:
            tags = await self._ollama_tags(client)
            tagset = set(tags)

            sem = asyncio.Semaphore(self.max_concurrency)

            async def check(m: Dict[str, Any]) -> Dict[str, Any]:
                mid = m.get("id") or m.get("name")
                name = m.get("name") or mid
                provider = m.get("provider") or "ollama"
                host = m.get("host") or self.ollama_host
                baseline_available = bool(mid in tagset or m.get("available"))

                async with sem:
                    probe = (
                        await self._probe_model(client, mid)
                        if mid
                        else {"available": False, "latency_ms": None}
                    )

                available = bool(probe["available"] or baseline_available)
                return {
                    "id": mid,
                    "name": name,
                    "provider": provider,
                    "available": available,
                    "latency_ms": probe["latency_ms"] if available else None,
                    "host": host,
                    "meta": {"default": mid == default_id, "in_tags": mid in tagset},
                }

            checks = [check(m) for m in models if (m.get("id") or m.get("name"))]
            results = await asyncio.gather(*checks)

        if not results:
            async with httpx.AsyncClient() as client:
                tags = await self._ollama_tags(client)
            results = [
                {
                    "id": t,
                    "name": t,
                    "provider": "ollama",
                    "available": True,
                    "latency_ms": None,
                    "host": self.ollama_host,
                    "meta": {"default": False, "in_tags": True},
                }
                for t in tags
            ]

        return {"models": results, "default": default_id}
