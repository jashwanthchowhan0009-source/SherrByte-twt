"""FastAPI application factory.

Run locally:
    uvicorn app.main:app --reload --port 8000

The app is built once, at import time, and `app` is what Uvicorn/Gunicorn loads.
Startup and shutdown logic lives in the `lifespan` context manager.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import sentry_sdk
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.starlette import StarletteIntegration
from slowapi.errors import RateLimitExceeded

from app import __version__
from app.api.v1 import api_router
from app.config import settings
from app.core.errors import register_error_handlers
from app.core.logging import configure_logging, get_logger, request_id_ctx
from app.db.session import check_database, dispose_engine
from app.deps import limiter

configure_logging()
log = get_logger(__name__)


# ---------------- Sentry ----------------


def _init_sentry() -> None:
    if not settings.sentry_dsn:
        log.info("sentry_disabled", reason="no_dsn")
        return
    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        environment=settings.app_env,
        release=f"{settings.app_name}@{__version__}",
        traces_sample_rate=0.1 if settings.is_prod else 1.0,
        profiles_sample_rate=0.1 if settings.is_prod else 0.0,
        integrations=[StarletteIntegration(), FastApiIntegration()],
        send_default_pii=False,
    )
    log.info("sentry_initialized", env=settings.app_env)


# ---------------- Lifespan ----------------


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Startup + shutdown hooks."""
    log.info(
        "app_starting",
        name=settings.app_name,
        version=__version__,
        env=settings.app_env,
    )
    _init_sentry()

    db_ok = await check_database()
    if not db_ok and settings.is_prod:
        # In prod we want a hard fail so Fly restarts the machine
        raise RuntimeError("Database unreachable at startup")
    log.info("app_ready", db_ok=db_ok)

    yield

    log.info("app_shutting_down")
    await dispose_engine()
    log.info("app_stopped")


# ---------------- App ----------------


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version=__version__,
        description="SherrByte — AI-powered personalized news for India.",
        docs_url="/docs" if not settings.is_prod else None,
        redoc_url="/redoc" if not settings.is_prod else None,
        openapi_url="/openapi.json" if not settings.is_prod else None,
        lifespan=lifespan,
    )

    # CORS — lock this down as soon as you know your frontend origins
    if settings.cors_origins:
        app.add_middleware(
            CORSMiddleware,app = create_app()
            allow_origins=settings.cors_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
            expose_headers=["X-Request-ID"],
        )

    # Request-ID middleware: every request gets a UUID; logs carry it.
    @app.middleware("http")
    async def request_id_middleware(request: Request, call_next):  # type: ignore[no-untyped-def]
        rid = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        token = request_id_ctx.set(rid)
        try:
            response: Response = await call_next(request)
        finally:
            request_id_ctx.reset(token)
        response.headers["X-Request-ID"] = rid
        return response

    register_error_handlers(app)

    # Rate limiter (slowapi)
    app.state.limiter = limiter

    async def _rate_limit_handler(_req: Request, exc: RateLimitExceeded) -> Response:
        from fastapi.responses import JSONResponse

        return JSONResponse(
            status_code=429,
            content={
                "error": {
                    "code": "rate_limited",
                    "message": f"Rate limit exceeded: {exc.detail}",
                }
            },
        )

    app.add_exception_handler(RateLimitExceeded, _rate_limit_handler)  # type: ignore[arg-type]

    app.include_router(api_router)

    # Root endpoint outside /v1 for quick reachability checks
    from app.api.v1.health import root as _root

    app.add_api_route("/", _root, include_in_schema=False)

    return app


app = create_app()
if __name__ == "__main__":
    import uvicorn
    import os
    # Pull port from Render's environment, default to 10000 if not found
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)
