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
- [Backend README](apps/api/README.md) documents endpoints, environment variables, and SQL schema.
- [Web README](apps/web/README.md) documents the Next.js app, public env vars, and frontend commands.

## Frontend Status

`apps/web` now contains the imported v1 Next.js app. It includes the mobile shell, bottom navigation, chat coach with conversation history, structured response chips, Match Radar with cached fixture and bookmaker odds data, Polymarket market signals, bet tracker, profile, language toggle, and API client wiring.

Match Radar reads fixtures from `/world-cup/fixtures` and bookmaker consensus from `/odds/matches`. Each match card shows 1X2 best prices, the bookmaker-consensus favorite, no-vig/fair probability, bookmaker count, freshness, and an expandable "More markets" area for goals over/under and goal handicap.

Recommended frontend env naming:

```text
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY=your-supabase-publishable-key
NEXT_PUBLIC_DEV_USER_ID=a87d09e8-7e10-46b8-9927-c9500c9559cf
```

Keep public browser-safe keys in frontend env files, and keep secret service keys in the backend `.env`. When Supabase public env vars are set, the web app uses real Supabase email/password sessions and sends the access token to FastAPI. Without them, it keeps the documented dev-user fallback.
