"""Shared pytest fixtures.

The background model-loading thread is always disabled in tests
(`start_background_loader=False`) so the suite never makes real network
calls to an Ollama server — each test injects the exact `AppState` /
`OllamaClient` it needs via `app.dependency_overrides`.
"""

from collections.abc import Iterator

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.config import Settings
from app.db import create_session_factory
from app.main import create_app
from app.services.chat_store import ChatStore
from app.state import AppState


@pytest.fixture
def settings() -> Settings:
    return Settings(
        ollama_host="http://ollama.test:11434",
        ollama_model="test-model:latest",
        chat_db_path=":memory:",
    )


@pytest.fixture
def state() -> AppState:
    return AppState()


@pytest.fixture
def chat_store() -> ChatStore:
    return ChatStore(create_session_factory(":memory:"))


@pytest.fixture
def app(settings: Settings) -> FastAPI:
    return create_app(settings, start_background_loader=False)


@pytest.fixture
def client(app: FastAPI) -> Iterator[TestClient]:
    with TestClient(app) as test_client:
        yield test_client
