"""src/core/logging.py — Enterprise structured logging configuration."""

import logging
import sys
from typing import Union


def configure_logging(level: Union[int, str] = logging.INFO) -> None:
    """Configure unified logging format for console and cloud run runtime."""
    if isinstance(level, str):
        level = getattr(logging, level.upper(), logging.INFO)

    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
        handlers=[logging.StreamHandler(sys.stdout)],
        force=True,
    )
    # Suppress verbose third-party loggers
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("qdrant_client").setLevel(logging.WARNING)


setup_logging = configure_logging


def get_logger(name: str) -> logging.Logger:
    """Provide a namespaced logger instance."""
    return logging.getLogger(name)
