"""Centralized logging setup using loguru."""

import sys
from pathlib import Path

from loguru import logger


def configure_logging(log_level: str, log_dir: str = "logs") -> None:
    """Configure loguru to write to both a rotating file and stdout.

    Idempotent-ish: calling it more than once just re-adds sinks, so callers
    (e.g. tests constructing multiple app instances) should call it once per
    process where possible.
    """
    Path(log_dir).mkdir(exist_ok=True)

    logger.remove()
    logger.add(
        f"{log_dir}/server.log",
        rotation="100 MB",
        retention="7 days",
        level=log_level,
        enqueue=True,
    )
    logger.add(sys.stdout, level=log_level)
