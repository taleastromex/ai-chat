"""Entrypoint — run with `python main.py` (used by Docker and run_local.sh).

The actual application lives in the `app` package; this file just wires up
uvicorn using the same `Settings` the app itself uses, so `HOST`/`PORT`/
`LOG_LEVEL` env vars are honored consistently in both places.
"""

import uvicorn

from app.config import get_settings

if __name__ == "__main__":
    settings = get_settings()
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        log_level=settings.log_level.lower(),
    )
