# SherrByte Build Guide — Zero to Production

This is your operating manual. Keep it open. Every account you need, every key you collect, every command you run — it's all in here.

---

## Part 1: Local developer environment

Install once, use forever.

| Tool | Why | Install |
|---|---|---|
| **Python 3.12** | Backend runtime | `brew install python@3.12` (mac) / `apt install python3.12` (linux) / python.org (windows) |
| **Git** | Version control | `brew install git` / already on most systems |
| **Docker Desktop** | Run Postgres/Redis locally, build production images | docker.com/products/docker-desktop |
| **VS Code** | Editor (or whatever you prefer) | code.visualstudio.com + extensions: Python, Pylance, Ruff, Docker |
| **uv** (recommended) | Fast Python package manager, replaces pip+venv | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| **Fly CLI** | Backend deployment | `curl -L https://fly.io/install.sh \| sh` |
| **Supabase CLI** (optional) | DB migrations, local studio | `brew install supabase/tap/supabase` |

Verify: `python3.12 --version && git --version && docker --version && fly version && uv --version`

---

## Part 2: Accounts to create

Sign up to these **before you write any code**. All are free tier. Order matters — do them top to bottom.

### Core infrastructure (must-have for Phase A–B)

| Service | Purpose | Signup | Free tier |
|---|---|---|---|
| **GitHub** | Code hosting, CI, secrets | github.com | Unlimited private repos |
| **Supabase** | Postgres + Auth + Storage + pgvector | supabase.com → sign in with GitHub | 500MB DB, 1GB storage, 50K MAU |
| **Upstash** | Redis for caching + event streams | upstash.com → sign in with GitHub | 10K commands/day |
| **Fly.io** | Backend container hosting | fly.io → sign up (credit card required but no charge on free) | 3 shared-cpu-1x 256MB machines |
| **Cloudflare** | DNS, CDN, DDoS, R2 object storage | cloudflare.com | Unlimited bandwidth, 10GB R2 |
| **Sentry** | Error tracking | sentry.io → sign up | 5K errors/month |

### AI / content (must-have for Phase D)

| Service | Purpose | Signup | Free tier |
|---|---|---|---|
| **Google AI Studio** | Gemini 2.5 Flash-Lite (primary LLM) | aistudio.google.com → "Get API key" | 1000 RPD Flash-Lite |
| **Groq** | Llama 3.3 70B (fallback LLM, fastest) | console.groq.com → sign up | 30 RPM, ~14K RPD |
| **OpenRouter** (optional) | Fallback router for many models | openrouter.ai | 50 RPD free, 1000 RPD after $10 credit |

### Supporting services (nice-to-have, can add later)

| Service | Purpose | Signup | Free tier |
|---|---|---|---|
| **Resend** | Transactional email | resend.com | 3K emails/month |
| **OneSignal** | Push notifications (web) | onesignal.com | Unlimited web push |
| **PostHog** | Product analytics + feature flags + A/B | posthog.com (use EU for India users) | 1M events/month |
| **BetterStack** | Uptime monitoring | betterstack.com | 10 monitors |
| **Axiom** | Log aggregation | axiom.co | 500GB/month ingest |
| **OpenWeatherMap** | Weather for markets/at-a-glance | openweathermap.org/api | 60 calls/min, 1M/month |

### Frontend hosting (already have Firebase; migrate later)

| Service | Purpose | Signup | Free tier |
|---|---|---|---|
| **Firebase Hosting** (keep for now) | Static HTML/JS | Already configured | 10GB/month |
| **Vercel** (Phase 3 migration target) | Next.js hosting | vercel.com | 100GB/month |

---

## Part 3: API keys to collect (the `.env` checklist)

Walk through each service's dashboard and collect these. Paste them into a scratch file first, then into `.env`.

### From Supabase (Project Settings → API & Database)

```
SUPABASE_URL=https://xxxxxxxx.supabase.co
SUPABASE_ANON_KEY=eyJhbGci...       # public, safe to expose to client
SUPABASE_SERVICE_KEY=eyJhbGci...    # SECRET, server-only
DATABASE_URL=postgresql+asyncpg://postgres:[YOUR-PASSWORD]@db.xxxxxxxx.supabase.co:5432/postgres
```

**Connection string tip:** In Supabase dashboard, go to *Project Settings → Database → Connection string → URI*. Replace `postgres://` with `postgresql+asyncpg://` for async SQLAlchemy.

### From Upstash (Redis dashboard → Details tab)

```
REDIS_URL=rediss://default:xxxxx@xxxxx.upstash.io:6379
# Also copy REST URL if you want to call Redis from Cloudflare Workers later
UPSTASH_REDIS_REST_URL=https://xxxxx.upstash.io
UPSTASH_REDIS_REST_TOKEN=xxxxx
```

### From Google AI Studio

```
GEMINI_API_KEY=AIzaSy...
# (Optional) Second project for 2x quota
GEMINI_API_KEY_2=AIzaSy...
```

### From Groq Console (API Keys section)

```
GROQ_API_KEY=gsk_...
```

### From Sentry (Project Settings → Client Keys (DSN))

```
SENTRY_DSN=https://xxxxx@xxxxx.ingest.sentry.io/xxxxx
```

### JWT secret (generate yourself)

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(48))"
```

```
JWT_SECRET=<paste output above>
```

### Keep for Phase D–E

```
OPENWEATHER_API_KEY=xxxxx
RESEND_API_KEY=re_xxxxx
ONESIGNAL_APP_ID=xxxxx
ONESIGNAL_REST_KEY=xxxxx
POSTHOG_API_KEY=phc_xxxxx
AXIOM_TOKEN=xaat-xxxxx
AXIOM_DATASET=sherrbyte-prod
```

---

## Part 4: Project layout

```
sherrbyte/
├── SETUP_GUIDE.md            ← this file
├── README.md
├── .env.example              ← checked in (no secrets)
├── .env                      ← your real secrets (gitignored)
├── .gitignore
├── pyproject.toml            ← Python deps + tool config
├── Dockerfile                ← production image
├── fly.toml                  ← Fly.io deploy config
├── alembic.ini               ← migration tool config (Phase B)
├── app/
│   ├── __init__.py
│   ├── main.py               ← FastAPI entrypoint, wires everything
│   ├── config.py             ← pydantic-settings, loads .env
│   ├── deps.py               ← dependency injection (Phase B)
│   ├── api/
│   │   └── v1/
│   │       ├── health.py     ← /healthz, /readyz
│   │       ├── auth.py       ← Phase B
│   │       ├── articles.py   ← Phase C
│   │       ├── feed.py       ← Phase E
│   │       └── ...
│   ├── core/
│   │   ├── logging.py        ← structlog setup
│   │   ├── errors.py         ← exception handlers
│   │   ├── security.py       ← JWT, password hash (Phase B)
│   │   ├── cache.py          ← Redis client (Phase C)
│   │   └── events.py         ← Redis Streams (Phase E)
│   ├── db/
│   │   ├── base.py           ← SQLAlchemy Base
│   │   └── session.py        ← async engine, session maker
│   ├── models/               ← ORM models (Phase B+)
│   ├── schemas/              ← Pydantic request/response (Phase B+)
│   ├── repos/                ← data access layer (Phase B+)
│   ├── services/             ← orchestrators (Phase C+)
│   ├── domain/               ← pure business logic (Phase E)
│   └── workers/              ← cron/queue workers (Phase C+)
├── migrations/               ← alembic versions (Phase B)
├── tests/
└── scripts/
```

---

## Part 5: The build roadmap (6 phases)

Each phase is a conversation with Claude. Ship each one before starting the next.

### Phase A — Foundation (this delivery)
**Goal: `uvicorn app.main:app` boots, `/healthz` returns 200, deploys to Fly.io.**
- Config loading from env with validation
- Structured JSON logging with correlation IDs
- Async Postgres connection pool
- Health + readiness endpoints
- Global error handlers
- Dockerfile + `fly.toml`
- CI skeleton

### Phase B — Auth & users
- Alembic migrations
- `users` + `sessions` tables
- Argon2id password hashing
- JWT access (15min) + refresh token (7d) with rotation
- `/v1/auth/register`, `/login`, `/refresh`, `/logout`, `/me`
- `slowapi` rate limiting (Redis-backed)
- Protected route dependency

### Phase C — Articles & ingestion
- `sources`, `articles`, `article_tags`, `article_entities` tables
- RSS feed ingestion worker (25+ Indian sources)
- `trafilatura` body extraction
- Three-layer dedup: URL → MinHash → semantic
- `/v1/articles/{id}`, `/v1/sources`
- Scheduled job on Fly.io or GitHub Actions

### Phase D — AI content pipeline
- LLM router with Gemini → Groq → OpenRouter cascade
- WWWW summarization with JSON schema enforcement
- Categorization cascade (embedding → NLI → LLM)
- Local embedding generation (MiniLM)
- `article_ai`, `article_embeddings` tables + pgvector HNSW index
- Redis-backed semantic cache

### Phase E — Feed & recommender v1
- `user_interactions` table (partitioned)
- Event ingestion API with Redis Streams buffer
- Hybrid scorer (explicit + implicit + content + freshness)
- MMR re-ranker with source/topic dedup
- `/v1/feed` cursor-paginated
- Onboarding flow API

### Phase F — Frontend integration
- Patch your existing v21 `index.html` to hit the new API
- Fix the field name mismatches (headline/title, source/source_name)
- Add client-side event batching
- Add PWA manifest + service worker
- Glass navigation + skeleton loaders

---

## Part 6: Deployment step-by-step

### Backend → Fly.io

One-time setup:
```bash
fly auth signup         # or 'fly auth login' if you already have an account
fly launch --no-deploy  # in the sherrbyte/ directory
# → answers: name "sherrbyte-api", region "bom" (Mumbai), no postgres (we use Supabase), no redis
```

This creates `fly.toml` (we provide one, just confirm). Then set secrets:
```bash
fly secrets set DATABASE_URL="postgresql+asyncpg://..."
fly secrets set REDIS_URL="rediss://..."
fly secrets set JWT_SECRET="..."
fly secrets set GEMINI_API_KEY="..."
fly secrets set GROQ_API_KEY="..."
fly secrets set SENTRY_DSN="..."
# (add more as phases progress)
```

Deploy:
```bash
fly deploy
```

Monitor:
```bash
fly logs         # tail logs
fly status       # health, regions, machines
fly ssh console  # shell into the container
```

### Database → Supabase

1. **Create project** at supabase.com (choose Mumbai region `ap-south-1`).
2. **Enable pgvector**: Dashboard → Database → Extensions → search "vector" → enable.
3. **Run migrations** locally with `alembic upgrade head` against `DATABASE_URL` (Phase B onwards).
4. **Backups**: Free tier gives 7-day daily backups automatically.

### Secrets → Fly + GitHub

- **Runtime secrets** go in Fly: `fly secrets set KEY=value`
- **CI secrets** go in GitHub: repo Settings → Secrets and variables → Actions
- **Never** commit `.env` — it's already in `.gitignore`.

### DNS → Cloudflare (Phase F / production)

1. Register domain at **Cloudflare Registrar** (at-cost pricing, ~$9/yr .com).
2. Add a CNAME record: `api.sherrbyte.com → sherrbyte-api.fly.dev` (proxied ON).
3. In Fly: `fly certs create api.sherrbyte.com` → follow DNS validation.
4. Frontend: `sherrbyte.com → <firebase/vercel domain>` (proxied ON).

### Frontend → stay on Firebase for Phase A–E, migrate in Phase F

Your existing Firebase Hosting is fine until we do the Next.js migration. Just update `API_URL` in your JS to point at `https://sherrbyte-api.fly.dev` (dev) or `https://api.sherrbyte.com` (prod) once backend is live.

---

## Part 7: Essential commands

```bash
# Setup
uv venv                         # create .venv
source .venv/bin/activate       # mac/linux
uv pip install -e ".[dev]"      # install deps from pyproject

# Run locally
cp .env.example .env            # fill in secrets
uvicorn app.main:app --reload --port 8000
# then: curl http://localhost:8000/healthz

# Tests
pytest -v
pytest --cov=app

# Lint & format
ruff check .
ruff format .
mypy app

# Migrations (Phase B+)
alembic revision --autogenerate -m "message"
alembic upgrade head
alembic downgrade -1

# Docker local
docker build -t sherrbyte-api .
docker run -p 8000:8000 --env-file .env sherrbyte-api

# Deploy
fly deploy
fly logs
```

---

## Part 8: Daily workflow

1. `git pull`
2. `source .venv/bin/activate`
3. `uvicorn app.main:app --reload` (keep running in one terminal)
4. Write code, save → auto-reload
5. `pytest` before committing
6. `git commit -am "..."` → `git push`
7. GitHub Actions runs CI; on `main` it deploys to Fly.io

---

## Part 9: When something breaks

| Symptom | Likely cause | First check |
|---|---|---|
| `/healthz` returns 500 | DB connection failing | `fly logs` — is `DATABASE_URL` set? Does Supabase see your IP? |
| 401 on every request | JWT secret mismatch | Is `JWT_SECRET` the same in Fly secrets and `.env`? |
| Redis timeouts | Upstash region far from Fly region | Both should be Asia/India |
| LLM 429 errors | Free-tier quota exhausted | Check model fallback config; may need to wait or add a second API key |
| Fly deploy fails with "out of memory" | 256MB too small for current image | `fly scale memory 512` (~$2/mo) |
| Slow cold start | Render's free-tier sleep (if still on Render) | **Switch to Fly.io now**, it stays warm |

---

## Part 10: What "done" looks like for each phase

After Phase A: `curl https://sherrbyte-api.fly.dev/healthz` returns `{"status":"ok","db":"ok","version":"..."}`.

After Phase B: you can register a user via `curl` and get back a JWT, then call `/me` with the token.

After Phase C: `curl /v1/articles` returns freshly-ingested articles from Indian RSS feeds.

After Phase D: each article in the DB has a WWWW summary, category tags, and an embedding.

After Phase E: `curl /v1/feed -H "Authorization: Bearer $TOKEN"` returns a personalized feed in <200ms p95.

After Phase F: your v21 HTML frontend on Firebase is talking to the new backend, events flowing, recommender learning.

You're shipping something real at the end of each phase. That's the whole point.

---

## Part 11: Phase B quick test (auth is live)

Once you've deployed Phase B, here's how to verify auth end-to-end with `curl`:

```bash
# First, run the migration (locally or via `fly deploy` which runs it automatically)
alembic upgrade head

# 1. Register a user
curl -X POST http://localhost:8000/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@sherrbyte.com","password":"testpassword123","display_name":"Test"}'

# Response: {"user": {...}, "tokens": {"access_token": "...", "refresh_token": "...", ...}}
# Save both tokens to env vars for the next calls:
export ACCESS_TOKEN="<paste access_token>"
export REFRESH_TOKEN="<paste refresh_token>"

# 2. Call /me with the access token
curl http://localhost:8000/v1/auth/me -H "Authorization: Bearer $ACCESS_TOKEN"

# 3. Refresh (get a new access + refresh token pair; old refresh is now revoked)
curl -X POST http://localhost:8000/v1/auth/refresh \
  -H "Content-Type: application/json" \
  -d "{\"refresh_token\":\"$REFRESH_TOKEN\"}"

# 4. Log in again
curl -X POST http://localhost:8000/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@sherrbyte.com","password":"testpassword123"}'

# 5. Log out (revoke the refresh token)
curl -X POST http://localhost:8000/v1/auth/logout \
  -H "Content-Type: application/json" \
  -d "{\"refresh_token\":\"$REFRESH_TOKEN\"}"
```

**What Phase B guarantees:**
- Passwords hashed with argon2id (OWASP-recommended).
- Access tokens expire in 15 minutes.
- Refresh tokens expire in 7 days and rotate on every use.
- Reusing a revoked refresh token → all sessions for that user are revoked (theft protection).
- Rate limits: 10/hour on register, 20/min on login, 60/min on refresh.

---

## Part 12: Phase C quick test (articles & RSS ingestion)

After deploying Phase C, populate the database with sources and run your first ingestion.

### Step 1 — Apply migrations

```bash
# Locally (once you've set DATABASE_URL in .env)
alembic upgrade head

# Or via fly (runs automatically on `fly deploy` via release_command)
fly deploy
```

### Step 2 — Seed the sources table

**Locally:**
```bash
python -m app.workers.seed_sources
```

**Or via GitHub Actions:** Go to your repo's Actions tab → "Seed Sources" workflow → "Run workflow" button. Only do this once (it's idempotent, but you don't need to re-run it).

You should now see 24 Indian publishers in your `sources` table. Verify:

```bash
curl http://localhost:8000/v1/sources | jq '.[] | {slug, language}'
```

### Step 3 — Run your first ingestion

**Locally (takes 2–4 minutes):**
```bash
python -m app.workers.ingest_rss
```

**Or via GitHub Actions:** Actions tab → "RSS Ingestion" → "Run workflow". After this, it will run **every 30 minutes automatically**.

You'll see JSON logs per source like:
```json
{"event":"source_stats","source":"ndtv-top","fetched":30,"inserted":12,
 "skipped_url":15,"skipped_hash":0,"skipped_simhash":3,"skipped_short":0,"errors":0}
```

### Step 4 — Query the articles

```bash
# Latest 20 articles, any source
curl http://localhost:8000/v1/articles | jq '.items[] | {title, source: .source.slug}'

# Filter by source slug
curl "http://localhost:8000/v1/articles?source=livemint&limit=10"

# Filter by language
curl "http://localhost:8000/v1/articles?language=hi&limit=10"

# Full article detail (body included)
curl http://localhost:8000/v1/articles/<uuid>
```

### Step 5 — Set up the secrets GitHub Actions needs

Your repo → Settings → Secrets and variables → Actions → New repository secret:

| Name | Value |
|---|---|
| `DATABASE_URL` | Your Supabase pooled connection string starting with `postgresql+asyncpg://` |
| `JWT_SECRET` | Any non-empty string (the worker doesn't actually use JWTs, but config loads it) |

**Why pooled?** Supabase gives you two connection strings: direct (port 5432) and pooled (port 6543). For short-lived GitHub Actions jobs, always use the **pooled** one so you don't exhaust Supabase's connection limit.

**What Phase C guarantees:**
- 24+ Indian RSS sources ingesting every 30 minutes (free via GitHub Actions cron).
- Three-layer dedup: URL → content hash (SHA-256) → simhash (Hamming ≤ 3).
- Body extraction via trafilatura (falls back to RSS summary if extraction fails).
- Per-source isolation: one broken feed doesn't kill the run.
- Language detection + language filtering on the API.
- Cursor pagination on `/v1/articles`.

---

## Part 13: Phase D quick test (AI pipeline)

After deploying Phase D, you'll have AI-written headlines, 60-word summaries, structured WWWW facts, entity extraction, and multi-label categorization on every article.

### Step 1 — Apply the migration

```bash
alembic upgrade head
```

This creates the AI tables and enables the `pgvector` extension. **If this fails with "could not open extension control file"**, go to Supabase dashboard → Database → Extensions and enable `vector` manually, then re-run the migration.

### Step 2 — Seed the taxonomy (one-time)

```bash
python -m app.workers.seed_taxonomy
```

Populates 9 pillars and ~50 launch microtopics. Re-run anytime you edit `app/workers/taxonomy_seed.py`.

Verify:
```bash
curl http://localhost:8000/v1/taxonomy | jq '.pillars'
```

### Step 3 — Collect LLM API keys

| Service | Where | Free tier |
|---|---|---|
| **Google AI Studio** | aistudio.google.com → Get API key | 1000 requests/day on Flash-Lite |
| **Groq** | console.groq.com → API Keys | ~14K RPD on Llama 3.3 70B |

Add them to your `.env`:
```
GEMINI_API_KEY=AIzaSy...
GROQ_API_KEY=gsk_...
REDIS_URL=rediss://default:xxx@xxx.upstash.io:6379
```

For GitHub Actions: repo Settings → Secrets and variables → Actions → add the same three.

### Step 4 — First enrichment run

**Locally** (first run downloads the 80MB MiniLM model — takes ~30s):
```bash
python -m app.workers.enrich_ai --limit=20
```

**Or via GitHub Actions:** Actions tab → "AI Enrichment" → "Run workflow". After this, it runs every 30 min automatically (at :15 and :45 past the hour, offset from the ingestion job at :00 and :30).

You'll see per-article logs like:
```json
{"event":"enrich_batch_complete","processed":20,"enriched":19,
 "cache_hits":3,"embedded":20,"tagged":18,"llm_failures":1}
```

### Step 5 — Query enriched articles

```bash
# Articles in the Tech pillar
curl "http://localhost:8000/v1/articles?pillar=tech&limit=5" | jq '.items[] | {title, summary_60w, tags: [.tags[].microtopic_slug]}'

# Full article with WWWW facts
curl http://localhost:8000/v1/articles/<uuid> | jq '{headline_rewrite, summary_60w, wwww, quality_score, tags}'

# Full taxonomy tree
curl http://localhost:8000/v1/taxonomy
```

### Cost accounting

At 500 articles/day with a 30% cache hit rate, you'll send ~350 unique articles to the LLM per day:
- Gemini Flash-Lite free tier: 1000 RPD → well within budget.
- Groq free tier: ~14,400 RPD → effectively unlimited fallback.
- Upstash Redis: one SET + one GET per article = 700 commands/day → free tier is 10K/day.
- Local embeddings (MiniLM on GitHub Actions runner): CPU-only, free.

**Total monthly AI cost: $0.**

**What Phase D guarantees:**
- AI-rewritten headlines (max 12 words, no clickbait) on every article.
- 60-word neutral-tone summaries.
- Structured WWWW (What/Who/Where/When/Why/How) JSON facts.
- Named entity extraction (PERSON/ORG/LOC/EVENT).
- Multi-label categorization against 50+ microtopics via zero-shot embedding match.
- 384-dim pgvector embeddings for semantic search (used by the Phase E recommender).
- Redis semantic cache keyed on content hash + prompt version — cache hits skip the LLM entirely.
- Cascading LLM fallback (Gemini → Groq) so rate limits on one provider don't stall the pipeline.
- Quality score per article so the Phase E ranker can downweight paywalled/stub articles.
