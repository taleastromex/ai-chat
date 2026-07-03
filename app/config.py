"""Application configuration, loaded from environment variables / `.env`."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration for AI-FABLE.

    Field names map to environment variables case-insensitively (e.g.
    `ollama_host` <- `OLLAMA_HOST`), matching the variables already used by
    docker-compose.yml and run_local.sh.
    """

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    ollama_host: str = "http://localhost:11434"
    ollama_model: str = (
        "hf.co/mradermacher/Huihui-gemma-4-12B-coder-fable5-composer2.5-v1-abliterated-GGUF:Q4_K_M"
    )
    host: str = "0.0.0.0"
    port: int = 8080
    log_level: str = "INFO"

    # Persistent chat history. `chat_db_path` accepts a filesystem path (parent
    # directories are created automatically) or the special value ":memory:"
    # (used by the test suite for a throwaway, per-process database).
    chat_db_path: str = "data/chats.db"
    # How many of the most recent non-system messages to resend to Ollama on
    # every turn, so the model keeps seeing prior context. The chat's system
    # prompt (if any) is always included on top of this, regardless of limit.
    chat_history_limit: int = 20


@lru_cache
def get_settings() -> Settings:
    """Return a cached `Settings` instance (env vars are read once)."""
    return Settings()
