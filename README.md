# Matchmind

Matchmind is an AI-powered betting coach for the 2026 FIFA World Cup. This repo is organized as a small monorepo so the FastAPI backend and your frontend can evolve together without mixing dependencies or build outputs.

## Structure

```text
matchmind/
├── apps/
│   ├── api/              # FastAPI backend
│   │   ├── app/
│   │   ├── tests/
│   │   ├── requirements.txt
│   │   └── README.md
│   └── web/              # Next.js mobile-first frontend
├── packages/
│   └── shared/           # Reserved for future shared contracts
├── docs/                 # Product and architecture notes
├── .env.example          # Root local environment template
├── Makefile              # Common local commands
└── package.json          # Optional Node workspace shell for frontend tooling
```

## Local Development

Install and run the API:

```bash
make api-install
make api-dev
```

Run backend tests:

```bash
make api-test
```

Install and run the frontend dependencies from the repo root:

```bash
pnpm install
pnpm web:dev
```

The frontend README has the framework-specific commands: [apps/web/README.md](apps/web/README.md).

Current local URLs:

```text
API: http://localhost:8000
Web: http://localhost:3000
```

## Environment

Keep local secrets in the root `.env`. The API also supports an `apps/api/.env` if you want service-specific env files later.

```bash
cp .env.example .env
```

The API env variables are documented in [apps/api/README.md](apps/api/README.md).

## Documentation

- [Architecture](docs/architecture.md) explains repo boundaries and provider cache flows.
- [Polymarket Integration](docs/polymarket-integration.md) records the current Polymarket data model, endpoints, classification rules, and operational caveats.
- [The Odds API Exploration](docs/odds-api-exploration.md) records bookmaker coverage, implemented cache tables, endpoints, and product usage.
- [Stripe Payments](docs/stripe-payments.md) documents test-mode checkout, webhook setup, troubleshooting, and the production checklist.
- [Legal and Compliance Pass](docs/legal-compliance.md) records the current analysis-only product posture and launch compliance checklist.
- [Referral Payout Review](docs/referral-payout-review.md) documents the manual pub commission audit and payout SQL checklist.
- [Deployment Runbook](docs/deployment.md) records Render deployment settings, frontend hosting decisions, scheduled refreshes, cost guardrails, and security notes.
- [Backend README](apps/api/README.md) documents endpoints, environment variables, and SQL schema.
- [Web README](apps/web/README.md) documents the Next.js app, public env vars, and frontend commands.

## Frontend Status

`apps/web` now contains the imported v1 Next.js app. It includes the mobile shell, bottom navigation, chat coach with conversation history, structured response chips, Match Radar with cached fixture and bookmaker odds data, Polymarket market signals, bet tracker, profile, language toggle, and API client wiring.

Match Radar reads fixtures from `/world-cup/fixtures` and bookmaker consensus from `/odds/matches`. Each match card shows 1X2 best prices, the bookmaker-consensus favorite, no-vig/fair probability, bookmaker count, freshness, and an expandable "More markets" area for goals over/under and goal handicap.

Recommended frontend env naming:

```text
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_APP_URL=http://localhost:3000
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY=your-supabase-publishable-key
```

Keep public browser-safe keys in frontend env files, and keep secret service keys in the backend `.env`. When Supabase public env vars are set, the web app uses real Supabase email/password sessions and sends the access token to FastAPI. Backend-only local development can opt into the fixed dev user with `ALLOW_DEV_AUTH_FALLBACK=true`; leave it false or unset in deployed environments.

FastAPI docs are disabled by default. Set `API_DOCS_ENABLED=true` only for local/private setup, and keep `APP_ENVIRONMENT=production` plus `API_DOCS_ENABLED=false` in the deployed API.

## Stripe Test-Mode Payments

Matchmind uses Stripe Checkout for the one-time World Cup Tournament Pass: €9.99 normally, a public €6.99 founder price until June 10, 2026 at 23:59 CEST, €8.99 when a referral code or Scout tier is active, €4.99 for Insider, and €2.49 for Captain. Free referral tiers activate the pass without a Stripe payment. Keep all Stripe values in the root/backend `.env` and use test-mode keys only during development:

```text
STRIPE_SECRET_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_TOURNAMENT_PASS_PRICE_ID=price_...
STRIPE_TOURNAMENT_PASS_FOUNDER_PRICE_ID=price_...
STRIPE_TOURNAMENT_PASS_REFERRAL_PRICE_ID=price_...
STRIPE_TOURNAMENT_PASS_INSIDER_PRICE_ID=price_...
STRIPE_TOURNAMENT_PASS_CAPTAIN_PRICE_ID=price_...
FOUNDER_PASS_SALE_ENDS_AT=2026-06-10T21:59:59+00:00
APP_URL=http://localhost:3000
```

For local webhook testing, run the API and then forward Stripe CLI events:

```bash
stripe listen --forward-to localhost:8000/payments/webhook
```

Use Stripe's test card `4242 4242 4242 4242` with any future expiry, CVC, and postal code. The frontend must not contain Stripe secret keys.

The full local setup, troubleshooting notes, and production migration checklist live in [docs/stripe-payments.md](docs/stripe-payments.md).
