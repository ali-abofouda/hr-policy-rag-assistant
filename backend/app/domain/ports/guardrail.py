"""backend/app/domain/ports/guardrail.py — Guardrail Port Interface."""

from typing import Any, Dict, Protocol, Tuple, runtime_checkable


@runtime_checkable
class GuardrailPort(Protocol):
    """Abstract interface defining safety and prompt-injection screening."""

    def evaluate_input(self, text: str, context: Any = None) -> Tuple[bool, str]:
        """Screen user input; return (is_allowed, reason)."""
        ...

    def evaluate_output(self, text: str, context: Any = None) -> Tuple[bool, str]:
        """Screen agent generated output; return (is_allowed, reason)."""
        ...
