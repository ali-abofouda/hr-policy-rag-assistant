"""03 · logging_config — Centralized console logging configuration.

Library modules emit operational telemetry through Python's standard logging module
at INFO level, ensuring consistent observability across execution pipelines.
"""

import logging
import os
from typing import Union, Optional

_CONFIGURED: bool = False # Flag to ensure logging is configured only once per process


def configure_logging(level: Optional[Union[str, int]] = None) -> None:
    """Attach a standardized formatter to the root logger once per process.
    
    Args:
        level: Optional log level override. Defaults to LOG_LEVEL env var or INFO.
    """
    global _CONFIGURED
    if _CONFIGURED:
        return

    resolved_level = level or os.getenv("LOG_LEVEL", "INFO")

    logging.basicConfig(
        level=resolved_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    logging.getLogger("hr_assistant").setLevel(resolved_level)
    _CONFIGURED = True