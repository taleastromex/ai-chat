"""Persistent chat history, backed by SQLite via SQLAlchemy.

Every read/write goes through a single `threading.Lock`, mirroring the
pattern already used by `AppState`: FastAPI runs sync route handlers in a
thread pool, so concurrent requests can genuinely race on the underlying
SQLite connection without one.
"""

from __future__ import annotations

import threading

from sqlalchemy.orm import Session, sessionmaker

from app.db import ChatORM, MessageORM, utcnow
from app.schemas import ChatSummary, MessageOut

_DEFAULT_TITLE = "New chat"
_TITLE_MAX_LEN = 60


def _make_title(first_message: str) -> str:
    text = " ".join(first_message.split())
    if len(text) <= _TITLE_MAX_LEN:
        return text or _DEFAULT_TITLE
    return text[: _TITLE_MAX_LEN - 1].rstrip() + "…"


def _chat_summary(chat: ChatORM) -> ChatSummary:
    return ChatSummary(
        id=chat.id, title=chat.title, created_at=chat.created_at, updated_at=chat.updated_at
    )


def _message_out(message: MessageORM) -> MessageOut:
    return MessageOut(role=message.role, content=message.content, created_at=message.created_at)


class ChatNotFoundError(LookupError):
    """Raised when an operation targets a chat id that doesn't exist."""


class ChatStore:
    """CRUD + context-window access for persisted chats and their messages."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory
        self._lock = threading.Lock()

    def create_chat(self) -> ChatSummary:
        with self._lock, self._session_factory() as session:
            chat = ChatORM()
            session.add(chat)
            session.commit()
            session.refresh(chat)
            return _chat_summary(chat)

    def list_chats(self) -> list[ChatSummary]:
        with self._lock, self._session_factory() as session:
            chats = session.query(ChatORM).order_by(ChatORM.updated_at.desc()).all()
            return [_chat_summary(chat) for chat in chats]

    def get_chat(self, chat_id: str) -> ChatSummary | None:
        with self._lock, self._session_factory() as session:
            chat = session.get(ChatORM, chat_id)
            return _chat_summary(chat) if chat else None

    def get_messages(self, chat_id: str) -> list[MessageOut]:
        """Full message history for a chat, oldest first."""
        with self._lock, self._session_factory() as session:
            chat = session.get(ChatORM, chat_id)
            if chat is None:
                return []
            return [_message_out(m) for m in chat.messages]

    def get_context(self, chat_id: str, limit: int) -> list[MessageOut]:
        """Messages to actually send to the model: the system prompt (if any,
        always included so long-running chats never lose their instructions)
        plus the most recent `limit` non-system messages, oldest first.
        """
        with self._lock, self._session_factory() as session:
            chat = session.get(ChatORM, chat_id)
            if chat is None:
                return []

            system_messages = [m for m in chat.messages if m.role == "system"]
            other_messages = [m for m in chat.messages if m.role != "system"]
            recent = other_messages[-limit:] if limit > 0 else other_messages

            ordered = system_messages[:1] + recent
            return [_message_out(m) for m in ordered]

    def append_message(self, chat_id: str, role: str, content: str) -> MessageOut:
        with self._lock, self._session_factory() as session:
            chat = session.get(ChatORM, chat_id)
            if chat is None:
                raise ChatNotFoundError(chat_id)

            message = MessageORM(chat_id=chat_id, role=role, content=content)
            session.add(message)

            if role == "user" and chat.title == _DEFAULT_TITLE:
                chat.title = _make_title(content)
            chat.updated_at = utcnow()

            session.commit()
            session.refresh(message)
            return _message_out(message)

    def delete_chat(self, chat_id: str) -> bool:
        with self._lock, self._session_factory() as session:
            chat = session.get(ChatORM, chat_id)
            if chat is None:
                return False
            session.delete(chat)
            session.commit()
            return True
