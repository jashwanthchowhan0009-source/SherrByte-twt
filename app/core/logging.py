"""Structured logging setup.

- Dev mode: pretty console output via rich.
- Prod mode: line-delimited JSON suitable for Axiom / Grafana Loki / CloudWatch.
- Every log entry can carry a correlation ID (request_id, user_id) via contextvars,
  so a single request's logs can be grepped across layers.
"""

from __future__ import annotations

import logging
import sys
from contextvars import ContextVar
from typing import Any

import structlog

from app.config import settings

# Context variables set by middleware; included in every log line.
request_id_ctx: ContextVar[str | None] = ContextVar("request_id", default=None)
user_id_ctx: ContextVar[str | None] = ContextVar("user_id", default=None)


def _add_context(
    _logger: logging.Logger, _method_name: str, event_dict: dict[str, Any]
) -> dict[str, Any]:
    """Inject request_id + user_id from contextvars into every log record."""
    if (rid := request_id_ctx.get()) is not None:
        event_dict["request_id"] = rid
    if (uid := user_id_ctx.get()) is not None:
        event_dict["user_id"] = uid
    return event_dict


def configure_logging() -> None:
    """Set up structlog + stdlib logging. Call once at application startup."""
    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        
structlog.processors.TimeStamper(fmt="iso", utc=True),
        _add_context,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    if settings.log_format == "json":
        final_processor: structlog.types.Processor = structlog.processors.JSONRenderer()
    else:
        final_processor = structlog.dev.ConsoleRenderer(colors=True)

    structlog.configure(
        processors=[*shared_processors, final_processor],
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, settings.log_level)
        ),
        logger_factory=structlog.PrintLoggerFactory(file=sys.stdout),
        cache_logger_on_first_use=True,
    )

    # Quiet noisy third-party loggers in dev
    for noisy in ("uvicorn.access", "httpx", "httpcore"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """Get a logger. Use module `__name__` by convention."""
    return structlog.get_logger(name)
