"""Pydantic request/response models for the public API."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class TextRequest(BaseModel):
    """Payload for `POST /generate`."""

    prompt: str
    max_new_tokens: int = 512
    temperature: float = 0.7
    top_p: float = 0.9
    system_prompt: str | None = None
    chat_id: str | None = None
    """Continue an existing chat. Omit to start a new one."""


class VisionRequest(BaseModel):
    """Payload for `POST /generate/vision`. Provide exactly one image source."""

    prompt: str
    image_url: str | None = None
    image_b64: str | None = None
    max_new_tokens: int = 512
    temperature: float = 0.7
    top_p: float = 0.9


class GenerateResponse(BaseModel):
    """Response shape shared by all `/generate*` endpoints."""

    generated_text: str
    model: str
    tokens_generated: int
    chat_id: str | None = None
    """The chat this exchange was appended to (None for endpoints that don't
    persist history, e.g. the vision endpoints for now)."""


class MessageOut(BaseModel):
    """A single stored chat message."""

    role: str
    content: str
    created_at: datetime


class ChatSummary(BaseModel):
    """A chat without its messages — used for the sidebar list."""

    id: str
    title: str
    created_at: datetime
    updated_at: datetime


class ChatDetail(ChatSummary):
    """A chat including its full message history."""

    messages: list[MessageOut]


class HealthResponse(BaseModel):
    """Response shape for `GET /health`."""

    status: str
    model_loaded: bool
    model_status: str
    progress: str | None = None
    error: str | None = None


class InfoResponse(BaseModel):
    """Response shape for `GET /info`."""

    model_id: str
    backend: str = "ollama"
    ollama_host: str
    model_status: str
    progress: str | None = None
