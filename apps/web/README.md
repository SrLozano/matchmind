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

- Chat coach: sends `POST /chat`, keeps the active `conversation_id`, can start a fresh chat, reopens previous conversations through `GET /conversations`, and shows structured chips for verdict, confidence, stake posture, and implied probability when available.
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
NEXT_PUBLIC_APP_URL=http://localhost:3000
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY=your-supabase-publishable-key
NEXT_PUBLIC_DEV_USER_ID=a87d09e8-7e10-46b8-9927-c9500c9559cf
```

The frontend calls the FastAPI backend on `NEXT_PUBLIC_API_URL`. `NEXT_PUBLIC_APP_URL` is the public web origin used for OAuth redirects; set it to the deployed Cloudflare Pages/custom-domain URL in production. When `NEXT_PUBLIC_SUPABASE_URL` and `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY` are present, the app shows a Supabase auth gate with email/password and Google OAuth, then sends the access token to the API. If those values are absent, local development falls back to `NEXT_PUBLIC_DEV_USER_ID`.

Do not put private backend secrets in the frontend. Keep `OPENAI_API_KEY`, Supabase service-role keys, Stripe secrets, and provider API keys in the root/backend `.env`.

## Tournament Pass Checkout

The Profile upgrade button calls the FastAPI endpoint `/payments/create-checkout-session` with the current Supabase bearer token, then redirects the browser to Stripe Checkout. After a successful or cancelled payment, Stripe redirects back to `APP_URL` from the backend `.env`; when the tab regains focus, the app reloads `/users/me` and shows the premium plan once the webhook has updated Supabase.

Stripe keys and price IDs belong in the backend `.env`, not in `apps/web/.env.local`. For local end-to-end testing, run:

```bash
stripe listen --forward-to localhost:8000/payments/webhook
```

Use the Stripe test card `4242 4242 4242 4242`.

See [Stripe Payments](../../docs/stripe-payments.md) for the complete local setup, troubleshooting guide, and production checklist.

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
- Payments use Stripe Checkout through the backend. The frontend must never expose Stripe secret keys.
- Real auth is wired for email/password and Google OAuth sessions when Supabase public env vars are present. Dev-user fallback remains available for local development.
- Local beta auth decision: keep Supabase email confirmation off for now. Before larger public launch, configure custom SMTP, then reconsider enabling email confirmation. The UI already handles confirmation-required signups if this is turned back on.
- The green highlight in Match Radar bookmaker odds marks the bookmaker-consensus favorite by highest no-vig probability. It does not mean Matchmind recommends that bet.
- The chat starter state is intentionally not a fake analyzed conversation. It shows one coach welcome plus example prompt chips that fill the input without auto-sending.
