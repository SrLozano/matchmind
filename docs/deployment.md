# Deployment Runbook

Last updated: 2026-05-23

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

As of 2026-05-23:

```text
Backend: Render Web Service
Frontend: Cloudflare Pages
Frontend URL: https://matchmind-web.pages.dev
Custom domain: https://trymatchmind.com
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
ALLOW_DEV_AUTH_FALLBACK=false
```

Stripe variables:

```text
STRIPE_SECRET_KEY
STRIPE_WEBHOOK_SECRET
STRIPE_TOURNAMENT_PASS_PRICE_ID
STRIPE_TOURNAMENT_PASS_REFERRAL_PRICE_ID
STRIPE_TOURNAMENT_PASS_INSIDER_PRICE_ID
STRIPE_TOURNAMENT_PASS_CAPTAIN_PRICE_ID
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
NEXT_PUBLIC_APP_URL=https://trymatchmind.com
NEXT_PUBLIC_SUPABASE_URL
NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY
NODE_VERSION=22
```

Because this is a static export, `NEXT_PUBLIC_*` values are build-time values. If `NEXT_PUBLIC_API_URL` is wrong or missing during the Cloudflare build, the deployed app can fall back to `http://localhost:8000` and all service calls will fail from the deployed site. If `NEXT_PUBLIC_APP_URL` is wrong, Google OAuth can return to the wrong origin. Fix the variables in Cloudflare and redeploy.

The web build validates these variables before `next build`. If any are missing or still set to placeholder values, the Cloudflare deployment should fail instead of publishing a broken login experience.

This project uses `wrangler.toml`, so Cloudflare treats that file as the source of truth for Pages configuration. Public frontend build variables are also defined in `[vars]` there so the static build receives them reliably. If these values change, update `wrangler.toml`, commit, and redeploy.

Supabase Auth URL settings:

```text
Site URL: https://trymatchmind.com
Redirect URLs:
https://trymatchmind.com/auth/callback
https://matchmind-web.pages.dev/auth/callback
http://localhost:3000/auth/callback
```

Add the equivalent `/auth/callback` URL for any custom domain or Cloudflare preview domain you actively use.

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

Current production custom domain:

```text
https://trymatchmind.com
```

Cloudflare DNS records:

```text
trymatchmind.com      CNAME   matchmind-web.pages.dev   Proxied
www                   CNAME   matchmind-web.pages.dev   Proxied
```

Cloudflare redirect rule:

```text
Rule name: Redirect www to root
Match type: Wildcard pattern
Request URL: https://www.trymatchmind.com/*
Target URL: https://trymatchmind.com/${1}
Status code: 301 - Permanent Redirect
Preserve query string: enabled
```

After any frontend domain change, update Render `APP_URL`, Render `CORS_ALLOWED_ORIGINS`, Supabase redirect URLs, Stripe settings, and `NEXT_PUBLIC_APP_URL`, then redeploy the static frontend so the compiled bundle uses the new origin.

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
| Odds | every 12h | every 60m |
| Odds near kickoff | off initially | every 15-30m only if quota allows |
| Polymarket | every 2h | every 30-60m |

Do not make high-frequency odds polling the default. The Odds API quota is one of the main cost risks.

### GitHub Actions Setup

The repo includes three scheduled workflows under `.github/workflows/`:

```text
refresh-world-cup-fixtures.yml -> POST /world-cup/refresh every 12 hours
refresh-odds.yml -> POST /odds/refresh twice daily
refresh-polymarket.yml -> POST /polymarket/refresh every 2 hours
```

Configure these repository secrets in GitHub before enabling production refreshes:

```text
MATCHMIND_API_URL=https://your-render-api-url
MATCHMIND_INTERNAL_API_TOKEN=<same value as Render INTERNAL_API_TOKEN>
```

Only the Matchmind backend URL and internal refresh token belong in GitHub Actions. Provider API keys stay in the Render backend environment, and the scheduled workflows must not call API-Football, The Odds API, or Polymarket directly.

To run a refresh manually, open GitHub Actions, choose the relevant refresh workflow, select **Run workflow**, and run it from the production branch. The workflow logs show the endpoint path, HTTP status, and a short response body preview. Any non-2xx response fails the job.

### Provider Quota Notes

API-Football currently has a 7,500-request/day paid allowance, but pre-tournament fixture/stat context does not need aggressive polling. Keep the default fixture refresh at every 12 hours for now. During the tournament, API-Football can support a future live updates layer for active matches, but do not add that until the product UI needs it.

The Odds API is the tight quota. With the current settings, `POST /odds/refresh` makes:

```text
GET /v4/sports/soccer_fifa_world_cup/events
GET /v4/sports/soccer_fifa_world_cup/odds?markets=h2h,spreads,totals&regions=eu
GET /v4/sports/soccer_fifa_world_cup_winner/odds?markets=outrights&regions=eu
```

That is roughly 4-5 credits per full refresh depending on provider accounting. At 500 credits/month, two daily pre-tournament refreshes should use roughly 240-300 credits/month, leaving room for manual checks and testing. The current GitHub Actions schedule runs at 07:23 and 19:23 UTC, which lands around Spain morning and evening. Do not schedule `POST /odds/refresh/events` separately unless the app needs to update event ids without refreshing prices; `POST /odds/refresh` already refreshes event metadata as part of the full odds refresh.

Polymarket is free for our current public market-data use, but it still has rate limits. The documented public limits are high enough for a 2-hour refresh cadence; avoid per-user Polymarket polling from frontend or chat requests.

Keep `POLYMARKET_REFRESH_CLOB_TOKEN_LIMIT=0` in production unless we explicitly need CLOB order-book enrichment. The Gamma market payload usually provides enough prices for v1 Market Signals, while CLOB enrichment can add three extra requests per token (`/midpoint`, `/spread`, and `/book`) and may push a Render refresh request past the practical timeout.

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

User-specific routes must require Supabase bearer auth in production. Keep `ALLOW_DEV_AUTH_FALLBACK` false or unset in deployed environments; it exists only to let local backend development use the fixed dev user when explicitly enabled.

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
