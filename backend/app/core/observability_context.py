"""Request-scoped observability context and structured logging (D2)."""

from __future__ import annotations

import logging
from contextvars import ContextVar, Token
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.schemas.observability import ObservabilityContext

_observability_context: ContextVar[ObservabilityContext | None] = ContextVar(
    "observability_context",
    default=None,
)


def set_observability_context(context: ObservabilityContext) -> Token:
    return _observability_context.set(context)


def get_observability_context() -> ObservabilityContext | None:
    return _observability_context.get()


def reset_observability_context(token: Token) -> None:
    _observability_context.reset(token)


class CorrelationIdLogFilter(logging.Filter):
    """Attach correlation_id to log records for webhook request handling."""

    def filter(self, record: logging.LogRecord) -> bool:
        context = get_observability_context()
        record.correlation_id = (
            str(context.correlation_id) if context is not None else "-"
        )
        return True


def configure_observability_logging() -> None:
    """Register correlation_id on the root logger (idempotent)."""
    root = logging.getLogger()
    if any(isinstance(item, CorrelationIdLogFilter) for item in root.filters):
        return
    root.addFilter(CorrelationIdLogFilter())
