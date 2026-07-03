"""Thread-safe holder for the model-loading state shared across the app."""

import threading

from app.enums import ModelStatus


class AppState:
    """Tracks whether the backing Ollama model is ready to serve requests.

    Mutated from a background thread (see `services.model_loader`) and read
    from request-handling coroutines concurrently, hence the lock guarding
    every read and write.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._status = ModelStatus.STARTING
        self._error = ""
        self._progress = ""

    def set(self, status: ModelStatus, *, error: str = "", progress: str = "") -> None:
        """Update the status, optionally recording an error or progress message."""
        with self._lock:
            self._status = status
            if error:
                self._error = error
            if progress:
                self._progress = progress

    @property
    def status(self) -> ModelStatus:
        with self._lock:
            return self._status

    @property
    def error(self) -> str:
        with self._lock:
            return self._error

    @property
    def progress(self) -> str:
        with self._lock:
            return self._progress

    @property
    def is_ready(self) -> bool:
        return self.status is ModelStatus.READY
