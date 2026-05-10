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

Chat provider context is best-effort. API-Football, Polymarket, and bookmaker odds failures are logged and omitted independently so the coach can still answer from the user message, parsed odds, and any remaining sources.

Conversations are stored in the existing `conversations.messages` JSONB field. `POST /chat` accepts an optional `conversation_id`; when present, the backend appends the new user turn to that conversation and injects compact recent `conversation_memory` into the model prompt. If the current user message lacks teams but appears to be a follow-up, provider matching can use the previous bet under discussion for context. `GET /conversations` and `GET /conversations/{conversation_id}` power the web history panel.

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
- The Odds API bookmaker odds: `POST /odds/refresh` writes `bookmaker_events`, `bookmaker_odds`, `bookmaker_odds_snapshots`, and `bookmaker_market_consensus`.
- The Odds API bootstrap: `POST /odds/seed-from-discovery` writes the same bookmaker tables from `tmp/odds_api_world_cup_discovery.json`.

## Current Product Surfaces

- Chat: `POST /chat`, backed by OpenAI plus cached API-Football context, supported long-term Polymarket context, cached bookmaker consensus when the user asks about a supported match/tournament market, and recent conversation memory for follow-ups. The web UI shows structured response chips for verdict, confidence, stake posture, and implied probability.
- Conversation History: `GET /conversations` and `GET /conversations/{conversation_id}`, deriving titles, previews, and message lists from `conversations.messages`.
- Match Radar / Daily Feed: `GET /world-cup/fixtures` plus `GET /odds/matches`, showing cached fixtures, 1X2 bookmaker prices, the market favorite, no-vig/fair probability, bookmaker count, freshness, and expandable goals over/under and goal handicap markets.
- Market Signals: `GET /polymarket/signals`, showing usable tournament-level crowd signals with premium locking.
- Bet Tracker: `POST /bets`, `GET /bets`, `PATCH /bets/{bet_id}`, and `DELETE /bets/{bet_id}`.
- Profile: `GET /users/me`, currently using a dev user ID until real auth is wired.

## Bookmaker Odds Layer

The Odds API integration is currently scoped to featured World Cup match markets and tournament outrights:

- `h2h`: match winner / 1X2.
- `spreads`: goal handicap.
- `totals`: goals over/under.
- `outrights`: World Cup winner futures.

The backend stores individual bookmaker prices in `bookmaker_odds`, keeps refresh history in `bookmaker_odds_snapshots`, and precomputes product-facing rows in `bookmaker_market_consensus`. Most product surfaces should read from `bookmaker_market_consensus` because it contains best price, median price, no-vig probability, and bookmaker count.

The frontend currently uses this data in Match Radar. The expandable label is intentionally user-friendly: "More markets" opens sections named "Goals over/under" and "Goal handicap" instead of bookmaker-native terms like "totals" alone.

## Current Gaps

- Auth is not wired in the frontend yet. The web app uses `NEXT_PUBLIC_DEV_USER_ID`.
- Stripe checkout is represented in pricing/profile UI and env placeholders, but no payment endpoints are implemented yet.
- Additional The Odds API event-specific markets such as BTTS, cards, corners, and player props are not wired into product surfaces yet.
- Bookmaker-vs-Polymarket divergence is not implemented yet. The clean first overlap would be bookmaker `outrights` vs Polymarket `tournament_outright`.
- Rich source transparency/freshness chips for exactly which data sources were used in each chat answer are not implemented yet.
- `packages/shared` is intentionally empty until shared generated clients, schemas, or constants are needed.

## Documentation Map

- [Polymarket Integration](polymarket-integration.md): market scope, cache flow, endpoints, schema meaning, classification, and known caveats.
- [The Odds API Exploration](odds-api-exploration.md): extractable bookmaker odds data, Matchmind use cases, cache schema proposal, and rollout plan.
- [API README](../apps/api/README.md): local setup, endpoint list, environment variables, and SQL schema.
- [Root README](../README.md): repo structure and local development commands.

## Local Ports

- API: `http://localhost:8000`
- Web: `http://localhost:3000` for the current Next.js app.
