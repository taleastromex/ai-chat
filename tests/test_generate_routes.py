"""Tests for /generate and /generate/vision."""

from unittest.mock import AsyncMock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.dependencies import get_ollama_client, get_state
from app.enums import ModelStatus
from app.state import AppState


def test_generate_returns_503_when_model_not_ready(client: TestClient) -> None:
    response = client.post("/generate", json={"prompt": "hello"})
    assert response.status_code == 503


def test_generate_returns_generated_text_when_ready(
    app: FastAPI, client: TestClient, state: AppState
) -> None:
    state.set(ModelStatus.READY)
    app.dependency_overrides[get_state] = lambda: state

    mock_client = AsyncMock()
    mock_client.chat.return_value = ("Hello, world!", 4)
    mock_client.model = "test-model:latest"
    app.dependency_overrides[get_ollama_client] = lambda: mock_client

    response = client.post("/generate", json={"prompt": "say hi", "max_new_tokens": 32})

    assert response.status_code == 200
    body = response.json()
    assert body["generated_text"] == "Hello, world!"
    assert body["tokens_generated"] == 4
    assert body["model"] == "test-model:latest"

    mock_client.chat.assert_awaited_once()
    _, kwargs = mock_client.chat.call_args
    assert kwargs["max_tokens"] == 32


def test_generate_forwards_system_prompt(app: FastAPI, client: TestClient, state: AppState) -> None:
    state.set(ModelStatus.READY)
    app.dependency_overrides[get_state] = lambda: state

    mock_client = AsyncMock()
    mock_client.chat.return_value = ("ok", 1)
    mock_client.model = "test-model:latest"
    app.dependency_overrides[get_ollama_client] = lambda: mock_client

    client.post(
        "/generate",
        json={"prompt": "hi", "system_prompt": "You are terse."},
    )

    messages = mock_client.chat.call_args.args[0]
    assert messages[0] == {"role": "system", "content": "You are terse."}
    assert messages[1] == {"role": "user", "content": "hi"}


def test_generate_vision_returns_503_when_model_not_ready(client: TestClient) -> None:
    response = client.post("/generate/vision", json={"prompt": "what is this?"})
    assert response.status_code == 503


def test_generate_vision_rejects_bad_image_url(
    app: FastAPI, client: TestClient, state: AppState
) -> None:
    state.set(ModelStatus.READY)
    app.dependency_overrides[get_state] = lambda: state
    app.dependency_overrides[get_ollama_client] = lambda: AsyncMock()

    response = client.post(
        "/generate/vision",
        json={"prompt": "describe", "image_url": "http://this-host-does-not-exist.invalid/x.png"},
    )

    assert response.status_code == 400
