"""System endpoints: health, model info, the loading-page redirect, and the
static web UI entrypoint."""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse

from app.dependencies import get_ollama_client, get_state
from app.enums import ModelStatus
from app.schemas import HealthResponse, InfoResponse
from app.services.ollama_client import OllamaClient
from app.state import AppState

router = APIRouter(tags=["system"])


@router.get("/", include_in_schema=False)
def serve_ui(state: AppState = Depends(get_state)) -> FileResponse:
    """Serve the loading page until the model is ready, then the chat UI."""
    if state.status is not ModelStatus.READY:
        return FileResponse("static/loading.html")
    return FileResponse("static/index.html")


@router.get("/ready", include_in_schema=False)
def ready(state: AppState = Depends(get_state)) -> dict[str, bool]:
    """Polled by the loading page; 200 once ready, 503 while loading, 500 on error."""
    if state.status is ModelStatus.READY:
        return {"ready": True}
    if state.status is ModelStatus.ERROR:
        raise HTTPException(status_code=500, detail=state.error)
    raise HTTPException(status_code=503, detail=state.progress or state.status.value)


@router.get("/health", response_model=HealthResponse)
def health(state: AppState = Depends(get_state)) -> HealthResponse:
    is_ready = state.status is ModelStatus.READY
    return HealthResponse(
        status="ok" if is_ready else state.status.value,
        model_loaded=is_ready,
        model_status=state.status.value,
        progress=state.progress or None,
        error=state.error or None,
    )


@router.get("/info", response_model=InfoResponse)
def info(
    state: AppState = Depends(get_state),
    client: OllamaClient = Depends(get_ollama_client),
) -> InfoResponse:
    return InfoResponse(
        model_id=client.model,
        ollama_host=client.host,
        model_status=state.status.value,
        progress=state.progress or None,
    )
