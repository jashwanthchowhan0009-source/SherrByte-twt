# syntax=docker/dockerfile:1.6

# ---------- Builder: install dependencies ----------
FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /build

# System build deps (only here, not in final image)
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        curl \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./
# Install into a virtualenv we'll copy over to the runtime stage
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN pip install --upgrade pip && pip install -r requirements.txt

# ---------- Runtime: slim, non-root ----------
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH"

# Runtime libs only (libpq for asyncpg is not needed — asyncpg bundles it)
RUN apt-get update && apt-get install -y --no-install-recommends \
        curl \
        tini \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --uid 1000 app

COPY --from=builder /opt/venv /opt/venv

WORKDIR /app
COPY --chown=app:app app ./app
COPY --chown=app:app alembic.ini* ./
COPY --chown=app:app migrations* ./migrations/

USER app

EXPOSE 8000

# tini handles signals cleanly (SIGTERM from Fly → graceful uvicorn shutdown)
ENTRYPOINT ["/usr/bin/tini", "--"]

# Healthcheck hits /healthz (Fly runs its own checks too; this is for docker-local)
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD curl -fsS http://localhost:8000/healthz || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
