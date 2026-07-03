"""Text and vision generation endpoints, proxied through Ollama."""

from __future__ import annotations

import base64

import requests
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from loguru import logger

from app.config import Settings
from app.dependencies import get_chat_store, get_ollama_client, get_settings_dep, get_state
from app.enums import ModelStatus
from app.schemas import GenerateResponse, TextRequest, VisionRequest
from app.services.chat_store import ChatStore
from app.services.ollama_client import OllamaClient
from app.state import AppState

router = APIRouter(tags=["generation"])


def _ensure_ready(state: AppState) -> None:
    if state.status is not ModelStatus.READY:
        raise HTTPException(status_code=503, detail=f"Model not ready ({state.status.value})")


def _fetch_image_as_b64(url: str) -> str:
    response = requests.get(url, timeout=15)
    response.raise_for_status()
    return base64.b64encode(response.content).decode()


def _normalize_b64(data: str) -> str:
    if data.strip().startswith("data:") and "," in data:
        return data.split(",", 1)[1]
    return data


@router.post("/generate", response_model=GenerateResponse)
async def generate_text(
    request: TextRequest,
    state: AppState = Depends(get_state),
    client: OllamaClient = Depends(get_ollama_client),
    store: ChatStore = Depends(get_chat_store),
    settings: Settings = Depends(get_settings_dep),
) -> GenerateResponse:
    _ensure_ready(state)

    chat_id = request.chat_id or store.create_chat().id
    if store.get_chat(chat_id) is None:
        raise HTTPException(status_code=404, detail=f"Chat not found: {chat_id}")

    if request.system_prompt and not any(m.role == "system" for m in store.get_messages(chat_id)):
        store.append_message(chat_id, "system", request.system_prompt)

    store.append_message(chat_id, "user", request.prompt)
    logger.info(f"Text generation request — chat={chat_id} max_new_tokens={request.max_new_tokens}")

    context = store.get_context(chat_id, limit=settings.chat_history_limit)
    messages = [{"role": m.role, "content": m.content} for m in context]

    text, tokens = await client.chat(
        messages,
        max_tokens=request.max_new_tokens,
        temperature=request.temperature,
        top_p=request.top_p,
    )
    store.append_message(chat_id, "assistant", text)

    return GenerateResponse(
        generated_text=text, model=client.model, tokens_generated=tokens, chat_id=chat_id
    )


@router.post("/generate/vision", response_model=GenerateResponse)
async def generate_vision(
    request: VisionRequest,
    state: AppState = Depends(get_state),
    client: OllamaClient = Depends(get_ollama_client),
) -> GenerateResponse:
    _ensure_ready(state)

    image_b64: str | None = None
    if request.image_url:
        try:
            image_b64 = _fetch_image_as_b64(request.image_url)
        except requests.RequestException as exc:
            raise HTTPException(
                status_code=400, detail=f"Failed to fetch image URL: {exc}"
            ) from exc
    elif request.image_b64:
        image_b64 = _normalize_b64(request.image_b64)

    logger.info(f"Vision generation request — image={'yes' if image_b64 else 'no'}")

    message: dict[str, object] = {"role": "user", "content": request.prompt}
    if image_b64:
        message["images"] = [image_b64]

    text, tokens = await client.chat(
        [message],
        max_tokens=request.max_new_tokens,
        temperature=request.temperature,
        top_p=request.top_p,
    )
    return GenerateResponse(generated_text=text, model=client.model, tokens_generated=tokens)


@router.post("/generate/vision/upload", response_model=GenerateResponse)
async def generate_vision_upload(
    prompt: str = Form(...),
    max_new_tokens: int = Form(512),
    temperature: float = Form(0.7),
    file: UploadFile = File(...),
    state: AppState = Depends(get_state),
    client: OllamaClient = Depends(get_ollama_client),
) -> GenerateResponse:
    _ensure_ready(state)

    raw = await file.read()
    image_b64 = base64.b64encode(raw).decode()
    message = {"role": "user", "content": prompt, "images": [image_b64]}

    text, tokens = await client.chat(
        [message],
        max_tokens=max_new_tokens,
        temperature=temperature,
        top_p=0.9,
    )
    return GenerateResponse(generated_text=text, model=client.model, tokens_generated=tokens)
