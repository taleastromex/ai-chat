"""Thin client around the Ollama REST API.

Deliberately mixes sync and async methods: the pull/readiness checks run on
a background thread at startup (see `model_loader.py`) and are naturally
synchronous, while `chat()` is called from async FastAPI route handlers.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from typing import Any

import httpx


class OllamaClient:
    """Talks to a single Ollama server about a single model."""

    def __init__(self, host: str, model: str) -> None:
        self.host = host.rstrip("/")
        self.model = model

    def is_reachable(self, timeout: float = 3.0) -> bool:
        """Return True if the Ollama server responds to `/api/tags`."""
        try:
            response = httpx.get(f"{self.host}/api/tags", timeout=timeout)
            return response.status_code == 200
        except httpx.HTTPError:
            return False

    def list_models(self, timeout: float = 10.0) -> list[str]:
        """Return the names of models Ollama already has pulled locally."""
        response = httpx.get(f"{self.host}/api/tags", timeout=timeout)
        response.raise_for_status()
        return [entry["name"] for entry in response.json().get("models", [])]

    def pull_stream(self) -> Iterator[dict[str, Any]]:
        """Trigger a model pull, yielding Ollama's progress events as dicts."""
        with httpx.stream(
            "POST",
            f"{self.host}/api/pull",
            json={"model": self.model, "stream": True},
            timeout=None,
        ) as response:
            response.raise_for_status()
            for line in response.iter_lines():
                if line:
                    yield json.loads(line)

    async def chat(
        self,
        messages: list[dict[str, Any]],
        *,
        max_tokens: int,
        temperature: float,
        top_p: float,
    ) -> tuple[str, int]:
        """Send a chat completion request and return (text, tokens_generated)."""
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": temperature,
                "top_p": top_p,
                "num_predict": max_tokens,
            },
        }
        async with httpx.AsyncClient(timeout=600) as client:
            response = await client.post(f"{self.host}/api/chat", json=payload)
            response.raise_for_status()
            data = response.json()

        text: str = data.get("message", {}).get("content", "")
        tokens_generated: int = data.get("eval_count", len(text.split()))
        return text, tokens_generated
