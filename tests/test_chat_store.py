"""Tests for the persistent chat store (SQLite via SQLAlchemy)."""

import time

import pytest

from app.services.chat_store import ChatNotFoundError, ChatStore


def test_create_chat_has_default_title(chat_store: ChatStore) -> None:
    chat = chat_store.create_chat()
    assert chat.title == "New chat"
    assert chat.id


def test_get_chat_returns_none_for_unknown_id(chat_store: ChatStore) -> None:
    assert chat_store.get_chat("does-not-exist") is None


def test_list_chats_orders_by_most_recently_updated(chat_store: ChatStore) -> None:
    first = chat_store.create_chat()
    second = chat_store.create_chat()
    time.sleep(0.01)  # ensure a strictly later `updated_at` than `second`
    chat_store.append_message(first.id, "user", "hello again")

    chats = chat_store.list_chats()

    assert [c.id for c in chats] == [first.id, second.id]


def test_append_message_sets_title_from_first_user_message(chat_store: ChatStore) -> None:
    chat = chat_store.create_chat()
    chat_store.append_message(chat.id, "user", "  What is   the capital of France?  ")

    updated = chat_store.get_chat(chat.id)

    assert updated is not None
    assert updated.title == "What is the capital of France?"


def test_append_message_truncates_long_titles(chat_store: ChatStore) -> None:
    chat = chat_store.create_chat()
    long_prompt = "x" * 200
    chat_store.append_message(chat.id, "user", long_prompt)

    updated = chat_store.get_chat(chat.id)

    assert updated is not None
    assert len(updated.title) <= 60
    assert updated.title.endswith("…")


def test_append_message_to_unknown_chat_raises(chat_store: ChatStore) -> None:
    with pytest.raises(ChatNotFoundError):
        chat_store.append_message("does-not-exist", "user", "hi")


def test_get_messages_returns_full_history_in_order(chat_store: ChatStore) -> None:
    chat = chat_store.create_chat()
    chat_store.append_message(chat.id, "user", "one")
    chat_store.append_message(chat.id, "assistant", "two")
    chat_store.append_message(chat.id, "user", "three")

    messages = chat_store.get_messages(chat.id)

    assert [m.content for m in messages] == ["one", "two", "three"]


def test_get_context_always_includes_system_message(chat_store: ChatStore) -> None:
    chat = chat_store.create_chat()
    chat_store.append_message(chat.id, "system", "Be terse.")
    for i in range(5):
        chat_store.append_message(chat.id, "user", f"msg {i}")

    context = chat_store.get_context(chat.id, limit=2)

    assert context[0].role == "system"
    assert [m.content for m in context[1:]] == ["msg 3", "msg 4"]


def test_get_context_respects_limit_without_system_message(chat_store: ChatStore) -> None:
    chat = chat_store.create_chat()
    for i in range(5):
        chat_store.append_message(chat.id, "user", f"msg {i}")

    context = chat_store.get_context(chat.id, limit=2)

    assert [m.content for m in context] == ["msg 3", "msg 4"]


def test_delete_chat_removes_it_and_its_messages(chat_store: ChatStore) -> None:
    chat = chat_store.create_chat()
    chat_store.append_message(chat.id, "user", "hello")

    assert chat_store.delete_chat(chat.id) is True
    assert chat_store.get_chat(chat.id) is None
    assert chat_store.get_messages(chat.id) == []


def test_delete_chat_returns_false_for_unknown_id(chat_store: ChatStore) -> None:
    assert chat_store.delete_chat("does-not-exist") is False
