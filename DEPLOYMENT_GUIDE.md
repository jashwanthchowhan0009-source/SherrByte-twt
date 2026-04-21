# SherrByte — Complete Deployment Guide

**Read this document top to bottom before touching anything.** It covers every single step from extracting the zip to seeing your app running on your mobile phone. Follow it in order — every step depends on the previous one.

This guide assumes you're on Windows, macOS, or Linux. You need a laptop/desktop for deployment; the final app runs on mobile via PWA (Progressive Web App — no app store needed).

---

## Table of Contents

1. [What you've been given](#1-what-youve-been-given)
2. [What this deployment gets you](#2-what-this-deployment-gets-you)
3. [Prerequisites — install these tools](#3-prerequisites)
4. [Sign up for services — accounts and API keys](#4-accounts--api-keys)
5. [Stage 1 — Extract and install locally](#5-stage-1--extract-and-install-locally)
6. [Stage 2 — Configure your .env file](#6-stage-2--configure-your-env-file)
7. [Stage 3 — Initialize the database](#7-stage-3--initialize-the-database)
8. [Stage 4 — Seed data (sources and taxonomy)](#8-stage-4--seed-data)
9. [Stage 5 — Run your first ingestion](#9-stage-5--first-ingestion)
10. [Stage 6 — Run your first AI enrichment](#10-stage-6--first-ai-enrichment)
11. [Stage 7 — Test the API locally](#11-stage-7--test-the-api-locally)
12. [Stage 8 — Deploy to Fly.io (cloud)](#12-stage-8--deploy-to-flyio)
13. [Stage 9 — Push to GitHub and enable cron automation](#13-stage-9--github--automation)
14. [Stage 10 — Access the API from your mobile](#14-stage-10--access-from-mobile)
15. [Troubleshooting](#15-troubleshooting)
16. [File-by-file reference](#16-file-by-file-reference)
17. [Daily operation and what to do next](#17-daily-operation)

---

## 1. What you've been given

This zip contains **67 files** organized as a production-ready FastAPI backend. You do NOT need to write any code — everything is done. Your job is:

1. Extract the zip
2. Sign up for a few free services (all have generous free tiers)
3. Copy/paste API keys into one `.env` file
4. Run a few commands
5. Push to GitHub and Fly.io

That's it. Total time: **2–4 hours for first-time setup**.

### What's in the zip

```
sherrbyte/
├── SETUP_GUIDE.md              ← Detailed reference (you don't need to read this; this file is enough)
├── README.md                   ← Short project overview
├── DEPLOYMENT_GUIDE.md         ← THIS FILE — your step-by-step
├── .env.example                ← Template — you'll copy this to .env
├── .gitignore                  ← Ignores secrets and caches
├── Dockerfile                  ← How to build the production image
├── fly.toml                    ← Fly.io deployment config
├── alembic.ini                 ← Database migration config
├── pyproject.toml              ← Python dependencies
├── scripts/dev.sh              ← One-liner to run the app locally
├── app/                        ← Main application code (27 Python files)
├── migrations/                 ← Database schema (3 versions)
├── tests/                      ← 44 automated tests (all passing)
└── .github/workflows/          ← CI + scheduled cron jobs (4 workflows)
```

**You will never edit any file inside `app/` for this deployment.** The only file you need to create is `.env`.

---

## 2. What this deployment gets you

After following this guide, you'll have:

- **A live backend** at `https://sherrbyte-api.fly.dev` (or your custom domain)
- **24 Indian RSS sources** auto-ingesting articles every 30 minutes
- **AI-written headlines + 60-word summaries + WWWW structured facts** on every article
- **Zero-shot categorization** across 9 pillars and ~50 microtopics
- **Semantic embeddings** for future recommendation
- **User registration and JWT login** (argon2id hashing, theft-protected refresh tokens)
- **Rate limiting, Sentry error tracking, structured logs**
- **Automated everything** — ingestion and AI enrichment run on cron without you lifting a finger

**Monthly cost: $0** if you stay under the free tiers (plenty for 10K-50K users).

**What you WON'T have yet:**
- Personalized feed ("For You") — that's Phase E, coming next
- Frontend hooked up — your existing v21 HTML still needs wiring in Phase F

That's fine — you'll have real articles flowing in and real users can register. We'll add personalization on top later.

---

## 3. Prerequisites

Install these tools on your laptop. Skip any you already have.

### All platforms

| Tool | Why | How to install |
|---|---|---|
| **Python 3.12+** | Runs the app | mac: `brew install python@3.12` / windows: python.org / linux: `apt install python3.12` |
| **Git** | Version control | mac: built-in / windows: git-scm.com / linux: `apt install git` |
| **A text editor** | View/edit `.env` | VS Code (code.visualstudio.com) — free, works everywhere |

### Verify installation

Open a terminal (Terminal app on Mac/Linux, PowerShell on Windows) and run:

```bash
python3.12 --version    # should show "Python 3.12.x"
git --version           # should show "git version ..."
```

If either fails, install the missing tool before continuing.

### Install uv (Python package manager — optional but much faster than pip)

Mac/Linux:
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Windows PowerShell:
```powershell
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Verify: `uv --version`

### Install Fly CLI (needed in Stage 8)

Mac/Linux:
```bash
curl -L https://fly.io/install.sh | sh
```

Windows PowerShell:
```powershell
iwr https://fly.io/install.ps1 -useb | iex
```

Verify: `fly version`

---

## 4. Accounts & API keys

Sign up for these services. **All are free and require no credit card at the free tier** (except Fly.io, which requires a card but doesn't charge).

Go through them **in this exact order** — copy every key/URL into a scratch notepad file as you go. You'll paste them into `.env` in Stage 2.

### 4.1 GitHub — account (required)

Go to **github.com** → sign up if you don't have one. Free unlimited private repos.

### 4.2 Supabase — your database (required)

Go to **supabase.com** → "Start your project" → sign in with GitHub.

1. Click **"New Project"**
2. Name: `sherrbyte`
3. Database password: **click Generate a password → copy it somewhere safe**
4. Region: **Mumbai (ap-south-1)** (closest to India)
5. Plan: **Free**
6. Click Create Project (takes ~2 minutes to provision)

Once it's ready:
- Go to **Project Settings → Database → Connection string → URI**
- Copy the connection string — it looks like: `postgresql://postgres:[YOUR-PASSWORD]@db.xxxxxxxx.supabase.co:5432/postgres`
- **Replace `postgres://` at the start with `postgresql+asyncpg://`**
- **Replace `[YOUR-PASSWORD]` with your actual password**
- Save as **`DATABASE_URL`** in your scratch notepad

Also enable the **vector extension**:
- Dashboard → Database → Extensions → search "vector" → toggle ON

### 4.3 Upstash — Redis cache (required)

Go to **upstash.com** → sign in with GitHub.

1. Click **"Create Database"**
2. Name: `sherrbyte-cache`
3. Type: **Regional**
4. Region: **Mumbai (ap-south-1)** or **Singapore** (closest)
5. Plan: **Free**

Once created, click the database → **"Details" tab** → copy:
- **Endpoint** + **Port** + **Password** combined into a URL like: `rediss://default:YOUR_PASSWORD@xxxxx.upstash.io:6379`
- Save as **`REDIS_URL`** in your scratch notepad

### 4.4 Google AI Studio — Gemini (primary LLM, required)

Go to **aistudio.google.com** → sign in with Google.

1. Click **"Get API key"** in the left sidebar
2. Click **"Create API key"** → select a Google Cloud project (or create new)
3. Copy the key (starts with `AIzaSy...`)
4. Save as **`GEMINI_API_KEY`** in your scratch notepad

**Free tier**: 1000 requests/day on Gemini 2.5 Flash-Lite.

### 4.5 Groq — Llama 3.3 70B (fallback LLM, required)

Go to **console.groq.com** → sign up.

1. Click **"API Keys"** in the sidebar
2. Click **"Create API Key"**
3. Copy the key (starts with `gsk_...`)
4. Save as **`GROQ_API_KEY`** in your scratch notepad

**Free tier**: 30 requests/min, ~14,400 requests/day.

### 4.6 Sentry — error tracking (optional but recommended)

Go to **sentry.io** → sign up.

1. Create project → Platform: **Python** → Framework: **FastAPI**
2. Copy the **DSN** (starts with `https://xxxxx@xxxxx.ingest.sentry.io/...`)
3. Save as **`SENTRY_DSN`** in your scratch notepad

**Free tier**: 5,000 errors/month.

### 4.7 Fly.io — hosting (required for Stage 8)

Go to **fly.io** → sign up.

- Credit card required (no charge on free tier, but it's their anti-abuse check)
- No API key needed yet; you'll authenticate via `fly` CLI in Stage 8

### 4.8 Generate a JWT secret

Open your terminal and run:

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(48))"
```

Copy the output. Save as **`JWT_SECRET`** in your scratch notepad.

### Your scratch notepad should now have 6–7 lines

```
DATABASE_URL=postgresql+asyncpg://postgres:xxx@db.xxx.supabase.co:5432/postgres
REDIS_URL=rediss://default:xxx@xxx.upstash.io:6379
GEMINI_API_KEY=AIzaSy...
GROQ_API_KEY=gsk_...
SENTRY_DSN=https://xxx@xxx.ingest.sentry.io/xxx
JWT_SECRET=<whatever that python command gave you>
```

Keep this file safe — **never commit it to GitHub**. You'll paste these into `.env` in the next stage.

---

## 5. Stage 1 — Extract and install locally

### 5.1 Extract the zip

Mac/Linux:
```bash
cd ~/Desktop     # or wherever you want the project
tar xzf sherrbyte-complete.tar.gz
cd sherrbyte
```

Windows (PowerShell):
```powershell
cd $HOME\Desktop
tar -xf sherrbyte-complete.tar.gz
cd sherrbyte
```

You should see `Dockerfile`, `README.md`, `app/`, `migrations/`, etc.

### 5.2 Create a virtual environment and install dependencies

Using `uv` (faster):
```bash
uv venv
source .venv/bin/activate           # mac/linux
# OR on Windows PowerShell:
.venv\Scripts\activate

uv pip install -e ".[dev]"
```

If `uv` is not available, use pip:
```bash
python3.12 -m venv .venv
source .venv/bin/activate           # mac/linux
# OR on Windows:
.venv\Scripts\activate

pip install -e ".[dev]"
```

This downloads ~40 Python packages (FastAPI, SQLAlchemy, etc.) — takes 1–3 minutes.

### 5.3 Verify installation

```bash
pytest -q
```

You should see: **`44 passed`**. If not, stop and check the error message — something in installation failed.

---

## 6. Stage 2 — Configure your .env file

### 6.1 Create .env from the template

```bash
cp .env.example .env    # mac/linux
copy .env.example .env  # windows
```

### 6.2 Open .env in a text editor

Open the new `.env` file in VS Code (or any text editor). You'll see a long file with lots of comments and blank values.

### 6.3 Paste in your values

Fill in these variables using what you collected in Stage 4:

```bash
# These are the minimum required to boot
DATABASE_URL=postgresql+asyncpg://postgres:YOUR_PASSWORD@db.xxxxxxxx.supabase.co:5432/postgres
JWT_SECRET=<your generated token>
REDIS_URL=rediss://default:YOUR_PASSWORD@xxxxx.upstash.io:6379

# LLM keys
GEMINI_API_KEY=AIzaSy...
GROQ_API_KEY=gsk_...

# Optional but recommended
SENTRY_DSN=https://xxx@xxx.ingest.sentry.io/xxx

# Leave APP_ENV as "dev" for local testing
APP_ENV=dev
LOG_FORMAT=console
LOG_LEVEL=INFO
```

### 6.4 Save the file

**Double-check**: open `.env` again and make sure there are no quotes around values, no extra spaces, and no leftover `CHANGEME` placeholders.

---

## 7. Stage 3 — Initialize the database

This creates all the tables in your Supabase project.

### 7.1 Run migrations

```bash
alembic upgrade head
```

Expected output:
```
INFO  [alembic.runtime.migration] Running upgrade  -> 0001_users_sessions
INFO  [alembic.runtime.migration] Running upgrade 0001_users_sessions -> 0002_sources_articles
INFO  [alembic.runtime.migration] Running upgrade 0002_sources_articles -> 0003_ai_tables
```

### 7.2 If it fails with "could not open extension control file"

This means pgvector isn't enabled in Supabase yet. Fix:
- Go to Supabase dashboard → Database → Extensions → search "vector" → toggle ON
- Re-run `alembic upgrade head`

### 7.3 Verify

Go to Supabase dashboard → Database → Tables. You should see 10 new tables:
`users, sessions, sources, articles, pillars, microtopics, article_ai, article_tags, article_embeddings` (plus `alembic_version`).

---

## 8. Stage 4 — Seed data

### 8.1 Seed RSS sources (24 Indian publishers)

```bash
python -m app.workers.seed_sources
```

Expected: ~24 log lines ending with `seed_complete total=24`.

### 8.2 Seed taxonomy (9 pillars + ~50 microtopics)

```bash
python -m app.workers.seed_taxonomy
```

Expected: ends with `taxonomy_seeded pillars=9 microtopics=50`.

### 8.3 Verify in Supabase

- `sources` table → should show 24 rows (NDTV, The Hindu, etc.)
- `pillars` table → should show 9 rows (Politics, Business, Tech, etc.)
- `microtopics` table → should show ~50 rows

---

## 9. Stage 5 — First ingestion

This pulls fresh articles from all 24 RSS feeds and deduplicates them.

```bash
python -m app.workers.ingest_rss
```

You'll see streaming JSON logs per source:
```
{"event":"source_stats","source":"ndtv-top","fetched":30,"inserted":12,"skipped_url":15,...}
{"event":"source_stats","source":"thehindu","fetched":50,"inserted":28,...}
...
{"event":"ingestion_complete","sources":24,"fetched":620,"inserted":180,"errors":1}
```

**Takes 2–5 minutes.** If you see errors from 1–2 sources, that's normal — publisher URLs occasionally drift.

Verify: `articles` table in Supabase should now have 100–400 rows.

---

## 10. Stage 6 — First AI enrichment

This adds AI summaries, WWWW facts, and categories to the articles.

```bash
python -m app.workers.enrich_ai --limit=20
```

**First run downloads an 80MB ML model** (MiniLM embedder) — takes ~30 seconds the first time, then instant.

Expected output:
```
{"event":"embed_model_loading","model":"all-MiniLM-L6-v2"}
{"event":"embed_model_ready","model":"all-MiniLM-L6-v2","dim":384}
{"event":"gloss_matrix_built","microtopics":50}
{"event":"enrich_batch_complete","processed":20,"enriched":19,"cache_hits":0,"embedded":20,"tagged":18}
```

**Takes 1–2 minutes.** Each article = 1 Gemini call + 1 local embedding + category match.

### 10.1 Scale up to process more

```bash
python -m app.workers.enrich_ai --limit=200
```

Processes up to 200 articles. Gemini free tier is 1000 requests/day, so you can enrich ~800 articles per day for free.

---

## 11. Stage 7 — Test the API locally

### 11.1 Start the server

```bash
uvicorn app.main:app --reload --port 8000
```

You'll see: `Uvicorn running on http://0.0.0.0:8000`.

### 11.2 Open the interactive docs

In your browser: **http://localhost:8000/docs**

This is auto-generated Swagger UI with every endpoint documented and testable.

### 11.3 Test endpoints from another terminal

Open a new terminal (keep the first one running `uvicorn`).

```bash
# Health check
curl http://localhost:8000/healthz

# Register a user
curl -X POST http://localhost:8000/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@sherrbyte.com","password":"testpass1234","display_name":"Test"}'

# List recent articles with AI enrichment
curl "http://localhost:8000/v1/articles?limit=3" | python3 -m json.tool

# List articles in the Tech pillar
curl "http://localhost:8000/v1/articles?pillar=tech&limit=3" | python3 -m json.tool

# View the full taxonomy
curl http://localhost:8000/v1/taxonomy | python3 -m json.tool
```

You should see real article titles with AI-written `headline_rewrite`, `summary_60w`, and category `tags`.

### 11.4 Stop the server

In the terminal running `uvicorn`, press **Ctrl+C**.

**If everything worked up to here, your backend is fully functional locally.** Now we deploy it to the cloud.

---

## 12. Stage 8 — Deploy to Fly.io

Fly.io hosts your API in Mumbai so Indian users get fast responses. Free tier gives you 3 small machines.

### 12.1 Log in to Fly

```bash
fly auth login
```

Opens a browser → sign in.

### 12.2 Launch the app (one-time setup)

From inside the `sherrbyte/` directory:

```bash
fly launch --no-deploy
```

You'll be asked questions. Answer:
- **App name**: `sherrbyte-api` (or pick your own — must be globally unique)
- **Region**: `bom` (Mumbai)
- **Would you like to set up a Postgresql database?**: **No** (we use Supabase)
- **Would you like to set up an Upstash Redis database?**: **No** (we already have Upstash)
- **Create .dockerignore?**: Yes

This reads `fly.toml` and creates the app. **Don't deploy yet** — we need to set secrets first.

### 12.3 Set all secrets on Fly

Copy every value from your `.env` to Fly via the `fly secrets` command. Run these one at a time, pasting your actual values:

```bash
fly secrets set DATABASE_URL="postgresql+asyncpg://postgres:xxx@db.xxx.supabase.co:5432/postgres"
fly secrets set JWT_SECRET="<your generated token>"
fly secrets set REDIS_URL="rediss://default:xxx@xxx.upstash.io:6379"
fly secrets set GEMINI_API_KEY="AIzaSy..."
fly secrets set GROQ_API_KEY="gsk_..."
fly secrets set SENTRY_DSN="https://xxx@xxx.ingest.sentry.io/xxx"
```

### 12.4 Deploy

```bash
fly deploy
```

Takes 3–5 minutes. Watches Docker build the image, upload to Fly, run migrations automatically (the `release_command = "alembic upgrade head"` in `fly.toml`), and boot up.

When you see `Machine ... is now in state started`, you're live.

### 12.5 Verify deployment

```bash
fly status                # see your machine
fly logs                  # tail logs
```

In a browser:
```
https://sherrbyte-api.fly.dev/healthz
```

Should return `{"status":"ok"}`.

```
https://sherrbyte-api.fly.dev/v1/articles?limit=3
```

Should return articles JSON.

---

## 13. Stage 9 — GitHub & automation

Now we put the code on GitHub so auto-cron workflows can run every 30 minutes.

### 13.1 Create a GitHub repository

Go to **github.com** → **+ New repository**:
- Name: `sherrbyte-api`
- Private: yes
- **Do NOT** initialize with README (we already have one)
- Click Create

### 13.2 Push your code

In the `sherrbyte/` directory:

```bash
git init
git add .
git commit -m "Initial commit — Phase A through D"
git branch -M main
git remote add origin https://github.com/YOUR-USERNAME/sherrbyte-api.git
git push -u origin main
```

**Check your commit didn't include `.env`** — it shouldn't have, because `.gitignore` excludes it. Verify by looking at the commit on GitHub and confirming `.env` is not listed.

### 13.3 Add secrets to GitHub

Repo → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**.

Add each of these (same values as your `.env`):

| Name | Value |
|---|---|
| `DATABASE_URL` | `postgresql+asyncpg://...` |
| `JWT_SECRET` | your generated token |
| `REDIS_URL` | `rediss://default:...` |
| `GEMINI_API_KEY` | `AIzaSy...` |
| `GROQ_API_KEY` | `gsk_...` |

### 13.4 Verify CI runs

Go to your repo → **Actions** tab. You should see the "CI" workflow running on your first push. It will:
- Lint with ruff
- Type-check with mypy
- Run all 44 tests

Should complete in ~2 minutes with a green checkmark.

### 13.5 Enable auto-ingestion

**No action needed** — the `ingest.yml` and `enrich.yml` workflows are already in `.github/workflows/`. They run automatically:
- **RSS ingestion** every 30 min (`:00` and `:30`)
- **AI enrichment** every 30 min, offset 15 min (`:15` and `:45`)

After 1 hour, check Actions tab — you should see green runs.

### 13.6 Enable auto-deploy on push (optional)

Edit `.github/workflows/ci.yml` and uncomment the `deploy` job at the bottom. Also add a Fly deploy token:

```bash
fly tokens create deploy -x 999999h
```

Copy the output. Add it as a GitHub secret named `FLY_API_TOKEN`.

Now every push to `main` auto-deploys to Fly.io.

---

## 14. Stage 10 — Access from mobile

You have **two options** to use this on your phone. Right now, since the frontend isn't hooked up yet (Phase F), both involve the API directly.

### Option A — Swagger UI on mobile (easiest, for testing)

1. On your phone, open Chrome/Safari
2. Visit: `https://sherrbyte-api.fly.dev/docs`
3. You can register, log in, and view articles right there

Not pretty but fully functional.

### Option B — Test with REST client app

Install **"HTTP Client"** or **"RESTer"** or **"Bruno"** (free) from Play Store / App Store. Create requests:

- POST `https://sherrbyte-api.fly.dev/v1/auth/register` with JSON body
- GET `https://sherrbyte-api.fly.dev/v1/articles`

### Option C — Wait for Phase F (coming next)

Phase F wires your existing v21 HTML frontend (currently on Firebase) to this new API, then installs it as a PWA on your home screen. Phase F will:

1. Fix the API_URL constant in your v21 HTML to point at `https://sherrbyte-api.fly.dev`
2. Update the data-fetching code to use the new endpoints
3. Add PWA manifest + service worker so "Add to Home Screen" gives you a real app icon
4. Add gesture support, skeleton loaders, and offline caching

After Phase F, you'll have a real installable app on your phone.

---

## 15. Troubleshooting

### "alembic upgrade head" fails

| Error | Cause | Fix |
|---|---|---|
| `could not open extension control file` | pgvector not enabled | Supabase dashboard → Database → Extensions → enable `vector` |
| `password authentication failed` | Wrong DB password in DATABASE_URL | Regenerate in Supabase, update .env |
| `must start with postgresql+asyncpg://` | Wrong driver prefix | Change `postgres://` to `postgresql+asyncpg://` |
| `connection refused` | Wrong host in DATABASE_URL | Copy connection string again from Supabase |

### "uvicorn app.main:app" fails with `ModuleNotFoundError`

You're not in the virtualenv. Run:
```bash
source .venv/bin/activate
```

### Ingestion: "errors": 20+

Most likely your Supabase free tier is rate-limiting, or network is slow. Wait 5 minutes and re-run. Some feeds genuinely break — if one source errors repeatedly, check the `sources` table's `last_error` column.

### AI enrichment: "llm_unavailable"

Either `GEMINI_API_KEY` or `GROQ_API_KEY` is missing/invalid. Double-check `.env`.

### AI enrichment: "rate limited"

You've exhausted the Gemini free tier (1000 RPD). The code automatically falls back to Groq. If Groq also 429s, you've used ~15K requests today — just wait for tomorrow's reset.

### Fly deploy: "out of memory"

256MB is tight during cold start. Upgrade:
```bash
fly scale memory 512
```
Costs ~$2/month.

### Fly deploy: "release command failed"

The `alembic upgrade head` inside Fly failed. Check:
```bash
fly logs
```
Likely the `DATABASE_URL` secret has a typo. Re-set it.

### Mobile can't reach the API

1. Check `/healthz` in desktop browser first
2. On mobile, make sure you're using `https://` not `http://`
3. If still fails, the Fly machine may have auto-stopped. Hit any endpoint — it wakes in ~2 seconds.

---

## 16. File-by-file reference

Only read this section if something breaks. Your deployment doesn't require understanding any of it.

### Top-level files

| File | What it does |
|---|---|
| `Dockerfile` | Builds the production Python 3.12 image |
| `fly.toml` | Fly.io deployment config (region, machine size, health checks) |
| `pyproject.toml` | Lists all Python dependencies |
| `alembic.ini` | Database migration tool config |
| `.env.example` | Template for your .env file |
| `.gitignore` | Excludes .env, .venv, __pycache__ from git |

### `app/` — application code

| Path | Purpose |
|---|---|
| `app/main.py` | FastAPI app factory, wires everything together |
| `app/config.py` | Loads and validates .env variables |
| `app/deps.py` | Dependency injection (DB session, current user, rate limiter) |
| `app/api/v1/auth.py` | `/v1/auth/register`, `/login`, `/refresh`, `/logout`, `/me` |
| `app/api/v1/articles.py` | `/v1/articles`, `/v1/sources`, `/v1/taxonomy` |
| `app/api/v1/health.py` | `/healthz`, `/readyz` |
| `app/core/security.py` | Argon2 password hashing, JWT access/refresh tokens |
| `app/core/errors.py` | Typed error hierarchy + HTTP exception handlers |
| `app/core/logging.py` | Structured logging with request correlation IDs |
| `app/core/cache.py` | Redis client (for LLM response cache) |
| `app/core/text.py` | Normalize, content hash (SHA-256), simhash for dedup |
| `app/db/session.py` | Async SQLAlchemy engine + session factory |
| `app/models/user.py` | User, Session ORM |
| `app/models/article.py` | Article ORM with dedup fingerprints |
| `app/models/source.py` | Source (publisher) ORM |
| `app/models/ai.py` | ArticleAI, ArticleTag, ArticleEmbedding, Pillar, Microtopic |
| `app/services/auth_service.py` | Register/login/refresh orchestration |
| `app/services/rss_fetcher.py` | Pulls RSS feeds + extracts article bodies |
| `app/services/ingestion_service.py` | 3-layer dedup + insert pipeline |
| `app/services/llm_router.py` | Gemini → Groq cascade with retries |
| `app/services/embedding.py` | Local MiniLM sentence-transformer |
| `app/services/ai_service.py` | Summarize + categorize + embed pipeline |
| `app/services/prompts.py` | WWWW summary prompt template |
| `app/repos/*.py` | Data access layer (one file per domain) |
| `app/schemas/*.py` | Pydantic request/response models |
| `app/workers/seed_sources.py` | Populate sources table (run once) |
| `app/workers/seed_taxonomy.py` | Populate pillars + microtopics (run once) |
| `app/workers/ingest_rss.py` | Pull all RSS feeds (cron every 30 min) |
| `app/workers/enrich_ai.py` | AI enrich un-enriched articles (cron every 30 min) |

### `migrations/versions/` — database schema history

| File | Tables it creates |
|---|---|
| `0001_users_sessions.py` | `users`, `sessions` |
| `0002_sources_articles.py` | `sources`, `articles` |
| `0003_ai_tables.py` | `pillars`, `microtopics`, `article_ai`, `article_tags`, `article_embeddings` + pgvector HNSW index |

### `.github/workflows/` — automation

| File | Trigger | What it does |
|---|---|---|
| `ci.yml` | push, PR | Lint + typecheck + run 44 tests |
| `ingest.yml` | cron `:00`, `:30` | Pulls 24 RSS feeds, dedups, inserts articles |
| `enrich.yml` | cron `:15`, `:45` | AI summarizes + categorizes + embeds new articles |
| `seed.yml` | manual only | One-shot seed of sources table |

### `tests/` — automated tests

| File | What it covers |
|---|---|
| `test_health.py` | 5 tests — app boots, /healthz, error envelope, request IDs |
| `test_security.py` | 12 tests — argon2, JWT encode/decode/expire, refresh tokens |
| `test_text.py` | 15 tests — normalize, content hash, simhash, Hamming distance |
| `test_ai.py` | 12 tests — prompt template, cache key, cosine categorization |

Run all: `pytest -v` → 44 pass.

---

## 17. Daily operation

### What happens automatically (you do nothing)

- Every 30 min: GitHub Actions pulls 24 RSS feeds → dedups → inserts new articles
- Every 30 min (offset 15): GitHub Actions enriches new articles with AI
- Both produce JSON logs in GitHub → Actions tab
- Fly.io keeps the API warm (auto-wakes in 2s when cold)
- Supabase backs up DB daily

### What to check weekly

1. **GitHub Actions tab** — are ingest/enrich runs green?
2. **Sentry dashboard** — any spiked errors?
3. **Supabase dashboard** — are you nearing 500MB DB limit?
4. **Fly.io dashboard** — is the machine healthy?

### What to do when something breaks

1. Check `fly logs` for API errors
2. Check GitHub Actions logs for cron errors
3. Check Sentry for exceptions
4. If stuck: revert to last known good deploy: `fly deploy --image <previous-image-tag>`

### Cost status

At 500 articles/day, 30% cache hit rate, 100 users:

| Service | Usage | Free tier | Status |
|---|---|---|---|
| Supabase DB | ~50MB | 500MB | ✅ 10% |
| Upstash Redis | ~500 cmd/day | 10K/day | ✅ 5% |
| Gemini Flash-Lite | ~350 req/day | 1000/day | ✅ 35% |
| Groq (fallback) | ~50 req/day | 14K/day | ✅ 0.4% |
| Fly.io | 1 machine | 3 machines | ✅ 33% |
| GitHub Actions | ~90 min/day | 2000 min/month | ✅ 45% |

**You can scale to 10K-50K users before hitting any paid tier.**

### When you're ready for more

Come back and say **"continue"** to trigger Phase E — the personalized recommender feed. Once you have a week or two of article data flowing, the recommender has something to train on.

---

**That's it.** Follow this guide top to bottom and you'll have SherrByte live on your phone within 4 hours. Good luck.
