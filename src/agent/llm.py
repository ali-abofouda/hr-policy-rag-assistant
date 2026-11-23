"""12 · llm — connect to the model via LiteLLM Gateway Router.

Every model call in the app goes through one place: get_llm(). It returns a
LangChain chat model backed by a LiteLLM Router running in-process:

    primary   -> Gemini (config.LLM_MODEL_NAME) via Google AI Studio API
    fallback  -> Groq (config.FALLBACK_MODEL_NAME), used automatically if primary errors

The app asks for logical model 'hr-llm'; the Router decides what serves it.
"""

import logging
from typing import Optional

import litellm
from langchain_litellm import ChatLiteLLMRouter
from litellm import Router

from src.core import config

logger = logging.getLogger(__name__)

# Drop unsupported params (e.g. Gemini-specific options) when failing over to Groq
litellm.drop_params = True

_PRIMARY_GROUP = "hr-llm"
_FALLBACK_GROUP = "hr-llm-fallback"

# One Router for the whole process (Singleton)
_router: Optional[Router] = None


def _get_router() -> Router:
    global _router
    if _router is None:
        logger.info(
            "Initializing LiteLLM Router: Primary=gemini/%s, Fallback=groq/%s",
            config.LLM_MODEL_NAME,
            config.FALLBACK_MODEL_NAME,
        )
        model_list = [
            {
                "model_name": _PRIMARY_GROUP,
                "litellm_params": {
                    "model": f"gemini/{config.LLM_MODEL_NAME}",
                    "api_key": config.GEMINI_API_KEY,
                },
            }
        ]

        if config.GROQ_API_KEY:
            model_list.append(
                {
                    "model_name": _FALLBACK_GROUP,
                    "litellm_params": {
                        "model": f"groq/{config.FALLBACK_MODEL_NAME}",
                        "api_key": config.GROQ_API_KEY,
                    },
                }
            )
            fallbacks = [{_PRIMARY_GROUP: [_FALLBACK_GROUP]}]
        else:
            logger.warning("GROQ_API_KEY is not set; running without automated fallback router.")
            fallbacks = []

        _router = Router(
            model_list=model_list,
            num_retries=2,
            fallbacks=fallbacks,
        )
    return _router


def get_llm():
    """Return the app's chat model: Gemini primary, Groq fallback, automatic retries.

    Returns a LangChain-compatible chat model managed by the LiteLLM Router.
    """
    return ChatLiteLLMRouter(
        router=_get_router(),
        model_name=_PRIMARY_GROUP,
        temperature=0.0,
    )
