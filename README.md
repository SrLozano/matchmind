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
│   └── web/              # Paste or scaffold the frontend here
├── packages/
│   └── shared/           # Future shared schemas, constants, generated clients
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

Install the frontend dependencies from the repo root:

```bash
pnpm install
pnpm web:dev
```

The frontend README has the framework-specific commands: [apps/web/README.md](apps/web/README.md).

## Environment

Keep local secrets in the root `.env`. The API also supports an `apps/api/.env` if you want service-specific env files later.

```bash
cp .env.example .env
```

The API env variables are documented in [apps/api/README.md](apps/api/README.md).

## Documentation

- [Architecture](docs/architecture.md) explains repo boundaries and provider cache flows.
- [Polymarket Integration](docs/polymarket-integration.md) records the current Polymarket data model, endpoints, classification rules, and operational caveats.

## Pasting Your Frontend

Put the frontend project contents directly inside `apps/web`.

Recommended frontend env naming:

```text
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_DEV_USER_ID=a87d09e8-7e10-46b8-9927-c9500c9559cf
```

Keep public browser-safe keys in frontend env files, and keep secret service keys in the backend `.env`.
