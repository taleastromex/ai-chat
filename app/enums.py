"""Shared enums for the AI-FABLE application."""

from enum import Enum


class ModelStatus(str, Enum):
    """Lifecycle states of the backing Ollama model.

    Inherits from `str` so it serializes cleanly to JSON via Pydantic/FastAPI
    without needing a custom encoder, while still being a real enum for
    exhaustiveness checks and comparisons elsewhere in the code.
    """

    STARTING = "starting"
    WAITING_FOR_OLLAMA = "waiting_for_ollama"
    PULLING = "pulling"
    READY = "ready"
    ERROR = "error"
