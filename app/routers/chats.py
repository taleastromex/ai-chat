"""CRUD endpoints for persisted chats, backing the sidebar chat list in the UI."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.dependencies import get_chat_store
from app.schemas import ChatDetail, ChatSummary
from app.services.chat_store import ChatStore

router = APIRouter(prefix="/chats", tags=["chats"])


@router.get("", response_model=list[ChatSummary])
def list_chats(store: ChatStore = Depends(get_chat_store)) -> list[ChatSummary]:
    return store.list_chats()


@router.post("", response_model=ChatSummary, status_code=status.HTTP_201_CREATED)
def create_chat(store: ChatStore = Depends(get_chat_store)) -> ChatSummary:
    return store.create_chat()


@router.get("/{chat_id}", response_model=ChatDetail)
def get_chat(chat_id: str, store: ChatStore = Depends(get_chat_store)) -> ChatDetail:
    chat = store.get_chat(chat_id)
    if chat is None:
        raise HTTPException(status_code=404, detail="Chat not found")
    messages = store.get_messages(chat_id)
    return ChatDetail(**chat.model_dump(), messages=messages)


@router.delete("/{chat_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_chat(chat_id: str, store: ChatStore = Depends(get_chat_store)) -> None:
    if not store.delete_chat(chat_id):
        raise HTTPException(status_code=404, detail="Chat not found")
