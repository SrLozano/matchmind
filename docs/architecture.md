# Matchmind Architecture

This document is the lightweight map of how the project is organized. Keep deep provider-specific notes in separate files under `docs/` and keep operational setup in the app READMEs.

## Monorepo Boundaries

- `apps/api` owns server-side logic, secrets, provider integrations, Supabase access, and OpenAI calls.
- `apps/web` owns the browser experience and should only use public environment variables.
- `packages/shared` is reserved for shared contracts once the frontend and backend need them.

## Backend Shape

The API follows a simple pattern:

```text
routers/
-> service functions
-> Supabase or provider APIs
-> compact response/context objects
```

Chat is intentionally a read path. It should not call slow or fragile provider APIs directly. Provider data is refreshed separately into Supabase, then served to chat through a short in-memory cache.

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

## Documentation Map

- [Polymarket Integration](polymarket-integration.md): market scope, cache flow, endpoints, schema meaning, classification, and known caveats.
- [API README](../apps/api/README.md): local setup, endpoint list, environment variables, and SQL schema.
- [Root README](../README.md): repo structure and local development commands.

## Local Ports

- API: `http://localhost:8000`
- Web: framework default, commonly `http://localhost:5173` for Vite or `http://localhost:3000` for Next.js.
