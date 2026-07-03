"""Background model-loading workflow, run on a daemon thread at startup.

Why Ollama and not `transformers` directly?
huihui-ai/Huihui-gemma-4-12B-coder-fable5-composer2.5-v1-abliterated declares
architecture "gemma4_unified" / "Gemma4UnifiedForConditionalGeneration". This
is not a real architecture in the `transformers` library (Google has only
ever released Gemma, Gemma2, Gemma3 — there is no "Gemma 4"), and the repo
ships no custom modeling code, so `trust_remote_code` cannot help either.
The only way to actually run this model is via a GGUF quantization through
an inference engine that reads raw tensors + a chat template (Ollama /
llama.cpp), which is architecture-agnostic. Hence this Ollama-backed proxy.
"""

import time

from loguru import logger

from app.enums import ModelStatus
from app.services.ollama_client import OllamaClient
from app.state import AppState

_POLL_INTERVAL_S = 2
_MAX_WAIT_S = 240  # ~4 minutes for the Ollama server itself to come up


def wait_for_ollama_then_pull(
    client: OllamaClient,
    state: AppState,
    *,
    max_wait_s: int = _MAX_WAIT_S,
) -> None:
    """Block (on a background thread) until Ollama is reachable, then pull the model."""
    state.set(ModelStatus.WAITING_FOR_OLLAMA)
    logger.info(f"Waiting for Ollama server at {client.host} ...")

    deadline = time.monotonic() + max_wait_s
    while time.monotonic() < deadline:
        if client.is_reachable():
            logger.success("Ollama server is reachable")
            break
        time.sleep(_POLL_INTERVAL_S)
    else:
        state.set(ModelStatus.ERROR, error=f"Ollama server not reachable at {client.host}")
        logger.error(state.error)
        return

    if _model_already_present(client):
        state.set(ModelStatus.READY, progress="already downloaded")
        logger.success(f"Model {client.model} already present, skipping pull")
        return

    _pull_model(client, state)


def _model_already_present(client: OllamaClient) -> bool:
    try:
        return client.model in client.list_models()
    except Exception as exc:  # noqa: BLE001 - best-effort check, fall through to pull
        logger.warning(f"Could not check existing models: {exc}")
        return False


def _pull_model(client: OllamaClient, state: AppState) -> None:
    state.set(ModelStatus.PULLING)
    logger.info(f"Pulling model {client.model} via Ollama ...")

    try:
        for event in client.pull_stream():
            progress = _format_progress(event)
            state.set(ModelStatus.PULLING, progress=progress)
            logger.info(f"[ollama pull] {progress}")

        state.set(ModelStatus.READY)
        logger.success(f"Model {client.model} is ready")

    except Exception as exc:  # noqa: BLE001 - surfaced to the UI via state.error
        state.set(ModelStatus.ERROR, error=str(exc))
        logger.error(f"Failed to pull model: {exc}")


def _format_progress(event: dict) -> str:
    status = event.get("status", "")
    total = event.get("total")
    completed = event.get("completed")
    if total and completed:
        pct = completed / total * 100
        return f"{status} ({pct:.1f}%)"
    return status
