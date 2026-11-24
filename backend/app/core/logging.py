"""backend/app/core/logging.py — Structured Logging."""

import sys
from loguru import logger
from typing import Optional


def configure_logging(level: str = "INFO", log_level: Optional[str] = None) -> None:
    """Configure Loguru structured sink with unified format."""
    effective_level = log_level if log_level is not None else level
    logger.remove()
    logger.add(
        sys.stderr,
        format="<green>{time:HH:mm:ss}</green> [<level>{level}</level>] <cyan>{name}</cyan>: {message}",
        level=effective_level,
        colorize=True,
    )


def setup_logging(level: str = "INFO", log_level: Optional[str] = None) -> None:
    """Backwards-compatible alias for configure_logging."""
    configure_logging(level=level, log_level=log_level)


__all__ = ["logger", "configure_logging", "setup_logging"]
