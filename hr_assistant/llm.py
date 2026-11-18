"""12 · llm — Centralized LLM connector for inference.

Returns a LangChain chat model configured from environment settings.
Supports:
1. Google AI Studio (API Key via GEMINI_API_KEY) — zero-cost default.
2. Google Cloud Vertex AI (via PROJECT_ID and LOCATION ADC credentials).
"""

import logging
import os
from typing import Optional

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_google_genai import ChatGoogleGenerativeAI

from hr_assistant import config

logger = logging.getLogger(__name__)


def get_llm(
    model_name: Optional[str] = None,
    temperature: float = 0.0,
) -> BaseChatModel:
    """Return a LangChain ChatGoogleGenerativeAI model instance.

    Configures temperature 0 for deterministic, grounded policy question answering.
    Prefers GEMINI_API_KEY if configured (Google AI Studio), otherwise falls back
    to Google Cloud Vertex AI Application Default Credentials (ADC).

    Args:
        model_name: Target model identifier (defaults to config.LLM_MODEL_NAME).
        temperature: Sampling temperature (0.0 for factual Q&A).

    Returns:
        Configured BaseChatModel instance.
    """
    selected_model = model_name or config.LLM_MODEL_NAME

    # Check for direct Google AI Studio API key
    gemini_key = os.getenv("GEMINI_API_KEY", "").strip()

    if gemini_key and gemini_key != "your_gemini_api_key_here":
        logger.info("Initializing ChatGoogleGenerativeAI via Google AI Studio API key: %s", selected_model)
        return ChatGoogleGenerativeAI(
            model=selected_model,
            google_api_key=gemini_key,
            temperature=temperature,
        )

    # Fallback to Google Cloud Vertex AI mode
    logger.info(
        "Initializing ChatGoogleGenerativeAI via Vertex AI (Project: %s, Location: %s, Model: %s)",
        config.PROJECT_ID,
        config.LOCATION,
        selected_model,
    )
    return ChatGoogleGenerativeAI(
        model=selected_model,
        vertexai=True,
        project=config.PROJECT_ID,
        location=config.LOCATION,
        temperature=temperature,
    )
