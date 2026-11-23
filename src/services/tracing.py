"""LangSmith tracing verification module."""

import logging

from hr_assistant import config

logger = logging.getLogger(__name__)


def check_langsmith_tracing() -> None:
    """Log whether LangSmith tracing is enabled for this run."""
    tracing_on = str(config.LANGSMITH_TRACING).lower() == "true"

    if tracing_on and config.LANGSMITH_API_KEY:
        logger.info(
            "LangSmith tracing ENABLED - project '%s', traces at https://smith.langchain.com",
            config.LANGSMITH_PROJECT,
        )
    else:
        logger.info("LangSmith tracing is OFF (set LANGSMITH_TRACING=true in .env to enable)")


if __name__ == "__main__":
    from hr_assistant.logging_config import configure_logging

    configure_logging()
    check_langsmith_tracing()