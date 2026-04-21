#!/usr/bin/env bash
# Dev convenience: activate venv + run the API with reload.
# Usage: ./scripts/dev.sh [port]

set -euo pipefail
PORT="${1:-8000}"

if [ ! -d ".venv" ]; then
  echo "→ No .venv found. Creating one with uv..."
  if command -v uv >/dev/null 2>&1; then
    uv venv
    # shellcheck disable=SC1091
    source .venv/bin/activate
    uv pip install -e ".[dev]"
  else
    python3.12 -m venv .venv
    # shellcheck disable=SC1091
    source .venv/bin/activate
    pip install -e ".[dev]"
  fi
else
  # shellcheck disable=SC1091
  source .venv/bin/activate
fi

if [ ! -f ".env" ]; then
  echo "→ No .env found. Copying from .env.example..."
  cp .env.example .env
  echo "⚠ Edit .env and set DATABASE_URL + JWT_SECRET before running."
  exit 1
fi

echo "→ Starting uvicorn on port $PORT (auto-reload)..."
exec uvicorn app.main:app --reload --host 0.0.0.0 --port "$PORT"
