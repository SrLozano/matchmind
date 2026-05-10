# Matchmind Architecture

This document is the lightweight map of how the project is organized. Keep deep provider-specific notes in separate files under `docs/` and keep operational setup in the app READMEs.

## Monorepo Boundaries

- `apps/api` owns server-side logic, secrets, provider integrations, Supabase access, and OpenAI calls.
- `apps/web` owns the browser experience and should only use public environment variables. It is currently a Next.js App Router app with a mobile-first product shell.
- `packages/shared` is reserved for shared contracts once the frontend and backend need them.

## Backend Shape

The API follows a simple pattern:

```text
routers/
-> service functions
-> Supabase or provider APIs
-> compact response/context objects
```

Chat is intentionally a lightweight request path. It stores the user turn, checks the daily limit, reads cached provider context, calls OpenAI, and stores the assistant turn. It should not call slow or fragile provider APIs directly. Provider data is refreshed separately into Supabase, then served to chat through a short in-memory cache.

## Data Flow Pattern

For provider integrations, prefer this shape:

```text
External provider
-> internal refresh/seed endpoint
-> Supabase cache table
-> in-memory TTL cache
-> chat/feed/UI endpoints
```

This keeps chat fast, makes provider failures easier to isolate, and gives us stored raw payloads for debugging.

Current examples:

- API-Football fixtures: `POST /world-cup/refresh` writes `world_cup_matches`.
- Polymarket markets: `POST /polymarket/refresh` writes `polymarket_markets` and `polymarket_market_snapshots`.
- Polymarket bootstrap: `POST /polymarket/seed-from-discovery` writes the same tables from the local exploration JSON when live Polymarket access is blocked.

Planned next provider:

- The Odds API should follow the same cache-first pattern before any bookmaker-vs-crowd divergence appears in chat or the UI.

## Current Product Surfaces

- Chat: `POST /chat`, backed by OpenAI plus cached API-Football and supported long-term Polymarket context.
- Daily Feed: `GET /world-cup/fixtures`, showing cached World Cup fixtures and free/premium insight slots.
- Market Signals: `GET /polymarket/signals`, showing usable tournament-level crowd signals with premium locking.
- Bet Tracker: `POST /bets`, `GET /bets`, `PATCH /bets/{bet_id}`, and `DELETE /bets/{bet_id}`.
- Profile: `GET /users/me`, currently using a dev user ID until real auth is wired.

## Current Gaps

- Auth is not wired in the frontend yet. The web app uses `NEXT_PUBLIC_DEV_USER_ID`.
- Stripe checkout is represented in pricing/profile UI and env placeholders, but no payment endpoints are implemented yet.
- The Odds API is still planned. There is no odds cache table or bookmaker divergence endpoint in the backend yet.
- `packages/shared` is intentionally empty until shared generated clients, schemas, or constants are needed.

## Documentation Map

- [Polymarket Integration](polymarket-integration.md): market scope, cache flow, endpoints, schema meaning, classification, and known caveats.
- [The Odds API Exploration](odds-api-exploration.md): extractable bookmaker odds data, Matchmind use cases, cache schema proposal, and rollout plan.
- [API README](../apps/api/README.md): local setup, endpoint list, environment variables, and SQL schema.
- [Root README](../README.md): repo structure and local development commands.

## Local Ports

- API: `http://localhost:8000`
- Web: `http://localhost:3000` for the current Next.js app.
