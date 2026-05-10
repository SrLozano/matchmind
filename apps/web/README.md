# Matchmind Web

Next.js frontend for Matchmind. This app was imported from the v1 frontend and lives inside the monorepo at `apps/web`.

## Stack

- Next.js App Router
- React
- TypeScript
- Tailwind CSS
- shadcn/Radix UI components
- pnpm

## Current Screens

- Chat coach: sends `POST /chat` and shows verdict metadata, confidence, and market signal context when available.
- Match Radar / daily feed: reads `GET /world-cup/fixtures` and `GET /odds/matches`, then shows cached World Cup fixtures plus bookmaker 1X2 prices, market favorite, no-vig/fair probability, bookmaker count, freshness, and expandable "More markets" rows for goals over/under and goal handicap.
- Market signals: reads `GET /polymarket/signals` and shows usable long-term crowd probability signals with premium locking.
- Bet tracker: uses `POST /bets`, `GET /bets`, `PATCH /bets/{bet_id}`, and `DELETE /bets/{bet_id}`.
- Profile: reads `GET /users/me`, shows plan/chat usage, language toggle, and the tournament pass CTA.

## Setup

From the repo root:

```bash
pnpm install
```

## Run Locally

Start the frontend dev server:

```bash
pnpm --filter @matchmind/web dev
```

Or use the root script:

```bash
pnpm web:dev
```

By default, Next.js runs at:

```text
http://localhost:3000
```

If port `3000` is busy, Next.js will offer another port.

## Run With The API

In one terminal, start the backend from the repo root:

```bash
make api-dev
```

In another terminal, start the frontend:

```bash
pnpm web:dev
```

Local URLs:

```text
API: http://localhost:8000
Web: http://localhost:3000
```

## Environment Variables

Create `apps/web/.env.local` when you need to override the local defaults:

```text
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_DEV_USER_ID=a87d09e8-7e10-46b8-9927-c9500c9559cf
```

The frontend calls the FastAPI backend on `NEXT_PUBLIC_API_URL`. `NEXT_PUBLIC_DEV_USER_ID` should match a user that exists in Supabase while auth is still being wired.

Do not put private backend secrets in the frontend. Keep `OPENAI_API_KEY`, Supabase service-role keys, Stripe secrets, and provider API keys in the root/backend `.env`.

## Useful Commands

From the repo root:

```bash
pnpm web:dev
pnpm web:build
pnpm web:start
pnpm web:lint
```

From `apps/web`:

```bash
pnpm dev
pnpm build
pnpm start
pnpm lint
```

## Notes

- The app name is `@matchmind/web` so pnpm can target it from the monorepo root.
- Shared frontend/backend contracts can go in `packages/shared` later.
- Static assets belong in `apps/web/public`.
- Payments are not wired yet. The profile upgrade button is a UI placeholder until Stripe checkout exists.
- Real auth is not wired yet. The app uses the dev user ID for all user-specific calls.
- The green highlight in Match Radar bookmaker odds marks the bookmaker-consensus favorite by highest no-vig probability. It does not mean Matchmind recommends that bet.
