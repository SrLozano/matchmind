# Deployment Runbook

Last updated: 2026-05-16

This document records the current MVP deployment decisions for Matchmind. The goal is to keep production reliable enough for real users while keeping fixed costs low and predictable.

## Current Decision

Use a managed, low-ops stack:

```text
Frontend
-> Cloudflare Pages static export

Backend
-> Render Web Service for FastAPI

Database/Auth
-> Supabase Pro with spend cap enabled

Scheduled refreshes
-> GitHub Actions cron first
-> Render Cron Jobs only if tighter match-day timing is needed
```

Vercel Pro remains the fallback if Cloudflare becomes a source of launch friction, but the current frontend is client-rendered enough to deploy as a static export.

## Current Deployed State

As of 2026-05-16:

```text
Backend: Render Web Service
Frontend: Cloudflare Pages
Frontend URL: https://matchmind-web.pages.dev
Database/Auth: Supabase
Payments: Stripe test-mode backend integration
Scheduled refreshes: not configured yet
```

The frontend and backend are connected. The initial Cloudflare deployment failed to call the API because the static bundle had not been built with the production `NEXT_PUBLIC_API_URL`. For static exports, public environment variables are compiled into the JavaScript at build time, so changing Cloudflare variables requires a new deployment.

The most important architectural constraint remains unchanged:

```text
External provider
-> internal refresh endpoint
-> Supabase cache tables
-> short in-memory TTL cache
-> chat/feed/UI endpoint
```

Normal chat, feed, and UI requests must not call API-Football, The Odds API, or Polymarket directly.

## Render FastAPI Service

The backend is deployed as a public Render Web Service.

Recommended settings:

```text
Service type: Web Service
Name: matchmind-api
Language: Python 3
Branch: main
Region: Frankfurt (EU Central), unless Supabase latency suggests otherwise
Root Directory: apps/api
Build Command: pip install -r requirements.txt
Start Command: uvicorn app.main:app --host 0.0.0.0 --port $PORT
Instance Type: Starter
Health Check Path: /health
Auto-Deploy: On Commit
Disk: none
Pre-Deploy Command: empty
Build Filters: empty for now
```

Render workspace plan:

```text
Hobby workspace: $0/mo + compute
```

The intended compute choice is:

```text
Starter web service: about $7/mo
```

Do not use the free web service for production because it can sleep. That is a poor fit for Stripe webhooks and first-request chat latency.

## Render Environment Variables

Backend secrets and provider keys belong only in Render or another backend/server environment. They must never be exposed through frontend public environment variables.

Core backend variables:

```text
SUPABASE_URL
SUPABASE_KEY
OPENAI_API_KEY
OPENAI_MODEL
FREE_DAILY_CHAT_LIMIT
PREMIUM_WEEKLY_CHAT_LIMIT
INTERNAL_API_TOKEN
APP_URL
CORS_ALLOWED_ORIGINS
```

Stripe variables:

```text
STRIPE_SECRET_KEY
STRIPE_WEBHOOK_SECRET
STRIPE_TOURNAMENT_PASS_PRICE_ID
```

Provider variables:

```text
API_FOOTBALL_KEY
API_FOOTBALL_BASE_URL
WORLD_CUP_LEAGUE_ID
WORLD_CUP_SEASON
WORLD_CUP_CACHE_TTL_SECONDS
WORLD_CUP_FIXTURE_REFRESH_HOURS

ODDS_API_KEY
ODDS_API_BASE_URL
ODDS_API_REGIONS
ODDS_API_BOOKMAKERS
ODDS_API_MARKETS
ODDS_API_OUTRIGHT_MARKETS
ODDS_API_ODDS_FORMAT
ODDS_API_CACHE_TTL_SECONDS

POLYMARKET_GAMMA_BASE_URL
POLYMARKET_CLOB_BASE_URL
POLYMARKET_CACHE_TTL_SECONDS
POLYMARKET_REFRESH_CLOB_TOKEN_LIMIT
POLYMARKET_MIN_MATCH_CONFIDENCE
POLYMARKET_MIN_SIGNAL_QUALITY

MATCH_DETECTION_FALLBACK_ENABLED
MATCH_DETECTION_MODEL
```

Local discovery paths should usually be omitted in production unless explicitly using seed-from-discovery endpoints:

```text
ODDS_API_DISCOVERY_PATH
POLYMARKET_DISCOVERY_PATH
```

After the frontend is deployed, update:

```text
APP_URL=https://your-frontend-domain
CORS_ALLOWED_ORIGINS=https://your-frontend-domain,http://localhost:3000,http://127.0.0.1:3000
```

If local development no longer needs to call the production API, remove localhost origins from production CORS.

## Frontend Hosting

The frontend is deployed on Cloudflare Pages as a static Next.js export.

Why this works for the current app:

```text
The app is mostly client-rendered.
The browser calls FastAPI directly through NEXT_PUBLIC_API_URL.
The browser uses Supabase client auth with public Supabase env vars.
No Next.js API routes, server actions, middleware, SSR, or image optimization are required right now.
```

Required Next.js config:

```js
const nextConfig = {
  output: 'export',
  typescript: {
    ignoreBuildErrors: true,
  },
  images: {
    unoptimized: true,
  },
}
```

Cloudflare Pages build settings from the repo root:

```text
Framework preset: Next.js (Static HTML Export)
Production branch: main
Build command: pnpm install --frozen-lockfile && pnpm --filter @matchmind/web build
Build output directory: apps/web/out
Root directory: empty
```

Frontend public variables:

```text
NEXT_PUBLIC_API_URL=https://your-render-api-url.onrender.com
NEXT_PUBLIC_SUPABASE_URL
NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY
NODE_VERSION=22
```

Because this is a static export, `NEXT_PUBLIC_*` values are build-time values. If `NEXT_PUBLIC_API_URL` is wrong or missing during the Cloudflare build, the deployed app can fall back to `http://localhost:8000` and all service calls will fail from the deployed site. Fix the variable in Cloudflare and redeploy.

Never expose:

```text
SUPABASE_KEY
INTERNAL_API_TOKEN
OPENAI_API_KEY
STRIPE_SECRET_KEY
STRIPE_WEBHOOK_SECRET
API_FOOTBALL_KEY
ODDS_API_KEY
```

Current Cloudflare default URL:

```text
https://matchmind-web.pages.dev
```

This URL is acceptable for testing. Before beta users, prefer a custom domain such as `trymatchmind.com` or `matchmind.app` and then update Render `APP_URL`, Render `CORS_ALLOWED_ORIGINS`, Supabase redirect URLs, and Stripe settings as needed.

## Stripe Webhook

Stripe should call the FastAPI backend directly:

```text
POST https://your-render-api-url/payments/webhook
```

Required event for the tournament pass:

```text
checkout.session.completed
```

The webhook endpoint is intentionally public, but it must keep verifying `Stripe-Signature` with `STRIPE_WEBHOOK_SECRET`.

## Scheduled Refresh Jobs

Use scheduled HTTP jobs to call the existing internal refresh endpoints:

```text
POST /world-cup/refresh
POST /odds/refresh
POST /polymarket/refresh
```

Each request must include:

```text
X-Internal-Token: <INTERNAL_API_TOKEN>
```

Recommended first runner:

```text
GitHub Actions scheduled workflows
```

Why:

- no extra fixed cost for normal MVP usage
- secrets stay in GitHub Actions secrets
- logs are visible in the Actions tab
- workflows can be triggered manually with `workflow_dispatch`

Use Render Cron Jobs later only if GitHub Actions schedule delay becomes a match-day problem.

Conservative schedules:

| Source | Before Tournament | Tournament Days |
|---|---:|---:|
| API-Football fixtures | every 12h | every 1-3h |
| Odds | every 6-12h | every 60m |
| Odds near kickoff | off initially | every 15-30m only if quota allows |
| Polymarket | every 2h | every 30-60m |

Do not make high-frequency odds polling the default. The Odds API quota is one of the main cost risks.

## Cost Guardrails

Hosting is not the main cost risk. The largest variable costs are:

1. OpenAI chat usage.
2. The Odds API refresh frequency and market/region selection.
3. Supabase overages if spend cap is off.
4. Frontend function/SSR usage if hosted on a platform with function overages.

Current planning targets:

```text
Minimum platform base:
Render FastAPI Starter + Supabase Pro + GitHub Actions + Cloudflare
~$32-$37/mo before provider and AI usage

Vercel fallback platform base:
Render FastAPI Starter + Supabase Pro + GitHub Actions + Vercel Pro
~$52/mo before provider and AI usage
```

Operational rules:

- Keep Supabase spend cap enabled.
- Keep free chat limits enabled.
- Add premium and global usage caps before broader launch.
- Start odds refreshes conservatively.
- Store compact normalized provider rows rather than large raw payloads forever.

## Security Notes

Immediate production posture:

- `INTERNAL_API_TOKEN` protects internal provider refresh endpoints. Keep it long, random, and server-only.
- Stripe webhook verification is required and should remain enabled.
- `SUPABASE_KEY` is a service role key and must only exist on the backend.
- Public frontend env vars must use Supabase publishable/anon keys only.
- If a secret is pasted into chat, issue trackers, screenshots, or logs, rotate it.

`/docs`, `/redoc`, and `/openapi.json` are useful during setup, but they expose endpoint structure. They do not expose secret values, but they make the API easier to inspect. Disable them before real public launch or gate them behind a production flag.

Known security gap to fix before public sharing:

Some user-facing endpoints still support local-development fallback behavior by accepting a client-supplied `user_id` or using the default dev user when no bearer token is present. That is convenient locally but not appropriate for production. Before broader access, production routes should require Supabase bearer auth and derive the user id from the token.

Affected surfaces include:

- `/chat`
- `/users/me`
- `/bets`
- `/conversations`

Public cache/read endpoints such as fixture, odds, and signal reads can stay public if they expose only non-user-specific data.

## Deployment Flow

With Render auto-deploy enabled:

```text
local code change
-> git commit
-> git push origin main
-> Render builds from apps/api
-> Render restarts the FastAPI service
```

Frequent redeploys do not charge a new monthly service fee. Costs are driven by running services, instance size, bandwidth, and additional paid resources.

Environment variable changes in Render require a restart/redeploy for the app process to pick them up.

With Cloudflare Pages auto-deploy enabled:

```text
local code change
-> git commit
-> git push origin main
-> Cloudflare builds from the repo root
-> Cloudflare publishes apps/web/out
```

Cloudflare static traffic can show many requests immediately after deployment. That is normal because Cloudflare counts every HTML, JS, CSS, font, icon, bot, and validation request. The cost-sensitive signals to watch are Render API logs, OpenAI usage, Supabase usage, and provider API usage.
