"""backend/app/core/exceptions.py — Domain and Infrastructure Custom Exceptions."""


class RAGException(Exception):
    """Base exception for all HR Policy RAG domain and service errors."""
    pass


class GuardrailViolationException(RAGException):
    """Raised when user input or agent output violates safety/compliance guardrails."""

    def __init__(self, message: str, guardrail_type: str = "input"):
        super().__init__(message)
        self.guardrail_type = guardrail_type


class VectorStoreUnavailableException(RAGException):
    """Raised when connection to vector store fails."""
    pass


class LLMGatewayException(RAGException):
    """Raised when both primary and fallback LLMs fail."""
    pass


class DocumentProcessingException(RAGException):
    """Raised when parsing or chunking document fails."""
    pass
