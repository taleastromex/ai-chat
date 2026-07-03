"""Tests for the /chats CRUD endpoints."""

from fastapi.testclient import TestClient


def test_create_and_get_chat(client: TestClient) -> None:
    created = client.post("/chats")
    assert created.status_code == 201
    chat_id = created.json()["id"]

    fetched = client.get(f"/chats/{chat_id}")
    assert fetched.status_code == 200
    body = fetched.json()
    assert body["id"] == chat_id
    assert body["messages"] == []


def test_get_unknown_chat_returns_404(client: TestClient) -> None:
    response = client.get("/chats/does-not-exist")
    assert response.status_code == 404


def test_list_chats_includes_created_chat(client: TestClient) -> None:
    created = client.post("/chats").json()

    listed = client.get("/chats").json()

    assert any(c["id"] == created["id"] for c in listed)


def test_delete_chat(client: TestClient) -> None:
    created = client.post("/chats").json()

    deleted = client.delete(f"/chats/{created['id']}")
    assert deleted.status_code == 204

    assert client.get(f"/chats/{created['id']}").status_code == 404


def test_delete_unknown_chat_returns_404(client: TestClient) -> None:
    response = client.delete("/chats/does-not-exist")
    assert response.status_code == 404
