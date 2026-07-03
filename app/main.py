"""FastAPI application factory for AI-FABLE."""

import threading
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from loguru import logger

from app.config import Settings, get_settings
from app.logging_config import configure_logging
from app.routers import generate, system
from app.services.model_loader import wait_for_ollama_then_pull
from app.services.ollama_client import OllamaClient
from app.state import AppState


def create_app(
    settings: Settings | None = None,
    *,
    start_background_loader: bool = True,
) -> FastAPI:
    """Build and configure the FastAPI application.

    Parameters allow tests to inject custom settings and skip the background
    model-loading thread (which otherwise makes real network calls to
    Ollama) so the app can be exercised in isolation.
    """
    settings = settings or get_settings()
    configure_logging(settings.log_level)

    model_state = AppState()
    ollama_client = OllamaClient(host=settings.ollama_host, model=settings.ollama_model)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        if start_background_loader:
            thread = threading.Thread(
                target=wait_for_ollama_then_pull,
                args=(ollama_client, model_state),
                daemon=True,
            )
            thread.start()
        yield
        logger.info("Shutting down AI-FABLE server")

    app = FastAPI(
        title="AI-FABLE",
        description=(
            "Inference API for Huihui-gemma-4-12B-coder-fable5 (abliterated), served via Ollama"
        ),
        version="2.1.0",
        lifespan=lifespan,
    )

    app.state.settings = settings
    app.state.model_state = model_state
    app.state.ollama_client = ollama_client

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.mount("/static", StaticFiles(directory="static"), name="static")
    app.include_router(system.router)
    app.include_router(generate.router)

    return app


app = create_app()
