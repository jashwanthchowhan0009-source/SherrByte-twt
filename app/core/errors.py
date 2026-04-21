"""Domain errors and global exception handlers.

Every error the API returns flows through here. The shape is always:

    { "error": { "code": "snake_case_code", "message": "human-readable" } }

Which makes client error handling trivial: check `error.code`, show message.
"""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.logging import get_logger

log = get_logger(__name__)


# -------- Domain exceptions --------


class AppError(Exception):
    """Base class for all expected application errors."""

    code: str = "internal_error"
    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    message: str = "An unexpected error occurred."

    def __init__(self, message: str | None = None, **extra: Any) -> None:
        self.message = message or self.message
        self.extra = extra
        super().__init__(self.message)


class NotFoundError(AppError):
    code = "not_found"
    status_code = status.HTTP_404_NOT_FOUND
    message = "Resource not found."


class UnauthorizedError(AppError):
    code = "unauthorized"
    status_code = status.HTTP_401_UNAUTHORIZED
    message = "Authentication required."


class ForbiddenError(AppError):
    code = "forbidden"
    status_code = status.HTTP_403_FORBIDDEN
    message = "You don't have permission to do that."


class ConflictError(AppError):
    code = "conflict"
    status_code = status.HTTP_409_CONFLICT
    message = "Resource already exists or is in an unexpected state."


class ValidationError(AppError):
    code = "validation_error"
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    message = "Invalid input."


class RateLimitError(AppError):
    code = "rate_limited"
    status_code = status.HTTP_429_TOO_MANY_REQUESTS
    message = "Too many requests."


# -------- Response helper --------


def _error_response(code: str, message: str, status_code: int) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"error": {"code": code, "message": message}},
    )


# -------- Handlers --------


async def app_error_handler(_req: Request, exc: AppError) -> JSONResponse:
    log.warning("app_error", code=exc.code, message=exc.message, **exc.extra)
    return _error_response(exc.code, exc.message, exc.status_code)


async def http_exception_handler(
    _req: Request, exc: StarletteHTTPException
) -> JSONResponse:
    # Map FastAPI/Starlette HTTPException to our envelope
    code = {
        401: "unauthorized",
        403: "forbidden",
        404: "not_found",
        405: "method_not_allowed",
        409: "conflict",
        422: "validation_error",
        429: "rate_limited",
    }.get(exc.status_code, "http_error")
    message = exc.detail if isinstance(exc.detail, str) else "Request failed."
    return _error_response(code, message, exc.status_code)


async def validation_exception_handler(
    _req: Request, exc: RequestValidationError
) -> JSONResponse:
    # Pydantic validation errors — surface a concise summary
    errors = exc.errors()
    message = "Invalid request payload."
    if errors:
        first = errors[0]
        loc = ".".join(str(p) for p in first.get("loc", []) if p != "body")
        message = f"{loc}: {first.get('msg', 'invalid')}" if loc else first.get("msg", message)
    log.info("validation_error", errors=errors)
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": {
                "code": "validation_error",
                "message": message,
                "details": errors,
            }
        },
    )


async def unhandled_exception_handler(_req: Request, exc: Exception) -> JSONResponse:
    log.exception("unhandled_exception", exc_type=type(exc).__name__)
    return _error_response(
        "internal_error",
        "Something went wrong on our end.",
        status.HTTP_500_INTERNAL_SERVER_ERROR,
    )


def register_error_handlers(app: FastAPI) -> None:
    """Wire all handlers to the FastAPI app. Called from main.py."""
    app.add_exception_handler(AppError, app_error_handler)  # type: ignore[arg-type]
    app.add_exception_handler(HTTPException, http_exception_handler)  # type: ignore[arg-type]
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)  # type: ignore[arg-type]
    app.add_exception_handler(RequestValidationError, validation_exception_handler)  # type: ignore[arg-type]
    app.add_exception_handler(Exception, unhandled_exception_handler)
