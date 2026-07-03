"""Tests for the OllamaClient service, using respx to mock the HTTP layer."""

import pytest
import respx
from httpx import ConnectError, Response

from app.services.ollama_client import OllamaClient


@pytest.fixture
def ollama_client() -> OllamaClient:
    return OllamaClient(host="http://ollama.test:11434", model="demo-model")


@respx.mock
def test_is_reachable_true_on_200(ollama_client: OllamaClient) -> None:
    respx.get("http://ollama.test:11434/api/tags").mock(return_value=Response(200, json={}))
    assert ollama_client.is_reachable() is True


@respx.mock
def test_is_reachable_false_on_connection_error(ollama_client: OllamaClient) -> None:
    respx.get("http://ollama.test:11434/api/tags").mock(side_effect=ConnectError("refused"))
    assert ollama_client.is_reachable() is False


@respx.mock
def test_list_models_returns_names(ollama_client: OllamaClient) -> None:
    respx.get("http://ollama.test:11434/api/tags").mock(
        return_value=Response(200, json={"models": [{"name": "a"}, {"name": "b"}]})
    )
    assert ollama_client.list_models() == ["a", "b"]


@pytest.mark.asyncio
@respx.mock
async def test_chat_returns_text_and_token_count(ollama_client: OllamaClient) -> None:
    respx.post("http://ollama.test:11434/api/chat").mock(
        return_value=Response(200, json={"message": {"content": "Hi there!"}, "eval_count": 3})
    )

    text, tokens = await ollama_client.chat(
        [{"role": "user", "content": "hi"}],
        max_tokens=64,
        temperature=0.7,
        top_p=0.9,
    )

    assert text == "Hi there!"
    assert tokens == 3


@pytest.mark.asyncio
@respx.mock
async def test_chat_falls_back_to_word_count_without_eval_count(
    ollama_client: OllamaClient,
) -> None:
    respx.post("http://ollama.test:11434/api/chat").mock(
        return_value=Response(200, json={"message": {"content": "one two three"}})
    )

    _, tokens = await ollama_client.chat(
        [{"role": "user", "content": "hi"}], max_tokens=64, temperature=0.7, top_p=0.9
    )

    assert tokens == 3
