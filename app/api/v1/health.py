"""Health and readiness endpoints.

- /healthz   — liveness: is the process up? Always returns 200 if the app is running.
- /readyz    — readiness: is it ready to serve? Checks DB. Returns 503 if not.
- /          — root with app metadata.

Fly.io, Uptime monitors, and Kubernetes probes all hit these.
"""

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

from app import __version__
from app.config import settings
from app.db.session import check_database

router = APIRouter()


@router.get("/", include_in_schema=False)
async def root() -> dict[str, str]:
    return {
        "name": settings.app_name,
        "version": __version__,
        "env": settings.app_env,
        "docs": "/docs" if not settings.is_prod else "disabled",
    }


@router.get("/healthz", tags=["health"])
async def healthz() -> dict[str, str]:
    """Liveness probe — cheap, always 200 if the app is up."""
    return {"status": "ok"}


@router.get("/readyz", tags=["health"])
async def readyz() -> JSONResponse:
    """Readiness probe — verifies the app can actually serve traffic."""
    db_ok = await check_database()
    body = {
        "status": "ok" if db_ok else "degraded",
        "checks": {"database": "ok" if db_ok else "fail"},
        "version": __version__,
        "env": settings.app_env,
    }
    code = status.HTTP_200_OK if db_ok else status.HTTP_503_SERVICE_UNAVAILABLE
    return JSONResponse(status_code=code, content=body)
