# MealForge

Inventory-aware meal planning with AI recipe generation. Set nutrition goals, plan weekly meals with auto-calculated macros, track ingredient inventory, and generate shopping lists from the gap between what a plan needs and what's on hand.

**Live:** https://mealforge.pages.dev · **API docs:** https://mealforge.fly.dev/docs

## Overview

MealForge connects four things most trackers keep separate: nutrition goals, meal plans, ingredient inventory, and shopping. A recipe added to a plan draws down inventory on a first-expiring-first-out basis; the shopping list is computed from remaining demand, not entered by hand; the AI generator proposes recipes from what's already in the fridge.

## Tech stack

**Backend** — Python 3.12, FastAPI, SQLAlchemy 2.0 (async), PostgreSQL, Redis, Alembic
**Frontend** — React 19, Vite, Tailwind CSS, shadcn/ui, React Router
**Auth** — Clerk (JWT verification via JWKS, RS256)
**AI** — Google Gemini with structured output
**Infrastructure** — Docker (multi-stage), Fly.io (backend), Neon (Postgres), Upstash (Redis), Cloudflare Pages (frontend), GitHub Actions (CI/CD)

## Architecture

The frontend is a static SPA on Cloudflare Pages' CDN. It calls the FastAPI backend running on Fly.io, which connects to managed Postgres (Neon) and Redis (Upstash). Authentication is handled by Clerk: the frontend obtains a JWT, the backend verifies it against Clerk's JWKS.

Redis caches computed daily nutrition summaries and is treated as a disposable accelerator — if it is unavailable, requests fall through to Postgres and still succeed. Database schema is managed by Alembic, applied automatically on each deploy via Fly's release command.

CI/CD runs on GitHub Actions: pushing to `main` runs the full test suite against an ephemeral Postgres, and only a passing suite triggers deployment to Fly.io.

## Local development

Requires Docker, [uv](https://github.com/astral-sh/uv), and Node.js.

Start Postgres and Redis:

```bash
docker compose up -d postgres redis
```

Backend (from repo root):

```bash
cp .env.example .env          # fill in CLERK_ISSUER, GEMINI_API_KEY, etc.
uv sync --all-extras --dev
uv run alembic upgrade head
uv run uvicorn app.main:app --reload
```

API is then at http://127.0.0.1:8000 (docs at `/docs`).

Frontend:

```bash
cd frontend
cp .env.example .env.local    # fill in VITE_CLERK_PUBLISHABLE_KEY, VITE_API_URL
npm install
npm run dev
```

## Testing

```bash
uv run pytest
```

93 tests, 86% coverage. The CI gate enforces a minimum coverage threshold and must pass before any deploy.

## License

MIT