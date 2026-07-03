"""FastAPI dependency providers.

Reading shared objects off `request.app.state` (rather than importing module-
level globals) is what makes it possible to override them per-test via
`app.dependency_overrides`, and to run multiple independent `App` instances
in the same process if ever needed.
"""

from fastapi import Request

from app.config import Settings
from app.services.chat_store import ChatStore
from app.services.ollama_client import OllamaClient
from app.state import AppState


def get_settings_dep(request: Request) -> Settings:
    return request.app.state.settings


def get_state(request: Request) -> AppState:
    return request.app.state.model_state


def get_ollama_client(request: Request) -> OllamaClient:
    return request.app.state.ollama_client


def get_chat_store(request: Request) -> ChatStore:
    return request.app.state.chat_store
