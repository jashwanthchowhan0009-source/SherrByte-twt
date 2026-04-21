# SherrByte API

AI-powered hyper-personalized news backend for India. FastAPI · async SQLAlchemy · Supabase Postgres · pgvector · Groq/Gemini.

See **[SETUP_GUIDE.md](./SETUP_GUIDE.md)** for the full zero-to-production walkthrough. This file is the quick-start.

## Prerequisites

- Python 3.12+
- A Supabase project with `DATABASE_URL` handy
- `uv` (recommended) or `pip`

## Quick start

```bash
# 1. Clone and enter
git clone <your-repo-url> sherrbyte
cd sherrbyte

# 2. Virtualenv + dependencies
uv venv
source .venv/bin/activate       # Windows: .venv\Scripts\activate
uv pip install -e ".[dev]"

# 3. Environment
cp .env.example .env
# Edit .env — at minimum set DATABASE_URL and JWT_SECRET

# 4. Run
uvicorn app.main:app --reload --port 8000
```

Hit `http://localhost:8000/healthz` — should return `{"status":"ok"}`.
Hit `http://localhost:8000/docs` — interactive API explorer.

## Project structure

```
app/
├── main.py            # FastAPI app factory
├── config.py          # pydantic-settings
├── api/v1/            # HTTP routes
├── core/              # logging, errors, security
├── db/                # SQLAlchemy engine/session
├── models/            # ORM models (Phase B+)
├── schemas/           # Pydantic request/response (Phase B+)
├── repos/             # Data access (Phase B+)
├── services/          # Orchestration (Phase C+)
├── domain/            # Pure business logic (Phase E)
└── workers/           # Cron/queue workers (Phase C+)
```

## Common commands

```bash
# Tests
pytest -v
pytest --cov=app

# Lint + format
ruff check .
ruff format .
mypy app

# Local Docker
docker build -t sherrbyte-api .
docker run -p 8000:8000 --env-file .env sherrbyte-api

# Deploy
fly deploy
fly logs
```

## Build phases

| Phase | Status | Focus |
|---|---|---|
| **A** | ✅ Foundation | App boots, /healthz passes, deploys to Fly |
| **B** | ✅ Auth | Users, sessions, JWT, argon2 |
| **C** | ✅ Articles | RSS ingestion (24 sources), 3-layer dedup, cursor API |
| **D** | ✅ AI pipeline | WWWW summary, embeddings, zero-shot categorization |
| **E** | ⏳ Feed | Hybrid recommender, events |
| **F** | ⏳ Frontend | v21 HTML → new API |

## License

Proprietary. © 2026 Jashwanth.
