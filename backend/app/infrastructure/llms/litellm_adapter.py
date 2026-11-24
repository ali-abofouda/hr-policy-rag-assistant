"""backend/app/infrastructure/llms/litellm_adapter.py — LiteLLM Router Adapter."""

import logging
from typing import Any, List, Optional
import litellm
from langchain_core.messages import BaseMessage
from langchain_litellm import ChatLiteLLMRouter
from litellm import Router

from backend.app.core.config import settings
from backend.app.domain.ports.llm import LLMPort

logger = logging.getLogger(__name__)
litellm.drop_params = True

_PRIMARY_GROUP = "hr-llm"
_FALLBACK_GROUP = "hr-llm-fallback"


class LiteLLMAdapter(LLMPort):
    """Adapter wrapping in-process LiteLLM Router with Gemini primary and Groq fallback."""

    def __init__(self, temperature: float = 0.0):
        self.temperature = temperature
        self._router: Optional[Router] = None
        self._chat_model: Optional[ChatLiteLLMRouter] = None

    def _get_router(self) -> Router:
        if self._router is None:
            logger.info(
                "Initializing LiteLLM Router: Primary=gemini/%s, Fallback=groq/%s",
                settings.LLM_MODEL_NAME,
                settings.FALLBACK_MODEL_NAME,
            )
            model_list = [
                {
                    "model_name": _PRIMARY_GROUP,
                    "litellm_params": {
                        "model": f"gemini/{settings.LLM_MODEL_NAME}",
                        "api_key": settings.GEMINI_API_KEY,
                    },
                }
            ]
            if settings.GROQ_API_KEY:
                model_list.append(
                    {
                        "model_name": _FALLBACK_GROUP,
                        "litellm_params": {
                            "model": f"groq/{settings.FALLBACK_MODEL_NAME}",
                            "api_key": settings.GROQ_API_KEY,
                        },
                    }
                )
                fallbacks = [{_PRIMARY_GROUP: [_FALLBACK_GROUP]}]
            else:
                fallbacks = []

            self._router = Router(
                model_list=model_list,
                num_retries=2,
                fallbacks=fallbacks,
            )
        return self._router

    def get_chat_model(self) -> ChatLiteLLMRouter:
        """Return the underlying LangChain chat model."""
        if self._chat_model is None:
            self._chat_model = ChatLiteLLMRouter(
                router=self._get_router(),
                model_name=_PRIMARY_GROUP,
                temperature=self.temperature,
            )
        return self._chat_model

    def invoke(self, messages: List[BaseMessage], **kwargs: Any) -> Any:
        return self.get_chat_model().invoke(messages, **kwargs)

    async def ainvoke(self, messages: List[BaseMessage], **kwargs: Any) -> Any:
        return await self.get_chat_model().ainvoke(messages, **kwargs)
