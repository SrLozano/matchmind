# Matchmind Backend

FastAPI backend foundation for Matchmind, an AI-powered betting coach focused on the 2026 FIFA World Cup.

## Project Structure

```text
matchmind/
├── app/
│   ├── main.py
│   ├── config.py
│   ├── routers/
│   │   └── chat.py
│   ├── services/
│   │   ├── api_football.py
│   │   ├── gpt.py
│   │   └── supabase.py
│   └── models/
│       └── chat.py
├── .env.example
├── requirements.txt
└── README.md
```

## Setup

1. Create and activate a virtual environment.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Copy `.env.example` to `.env` and fill in your project values.
4. Run the API locally:

```bash
uvicorn app.main:app --reload
```

## Endpoints

- `GET /health` checks API and Supabase connectivity.
- `GET /world-cup/fixtures` returns cached 2026 World Cup fixture context from Supabase/memory.
- `POST /world-cup/refresh` refreshes fixtures from API-Football. This is internal and requires `X-Internal-Token` matching `INTERNAL_API_TOKEN`.
- `POST /chat` accepts:

```json
{
  "user_id": "00000000-0000-0000-0000-000000000000",
  "message": "Thinking of betting €20 on Spain to beat Germany at 2.10"
}
```

Returns:

```json
{
  "response": "Verdict: FAIR\n\nMy take:\n...",
  "confidence_score": 6,
  "verdict": "FAIR",
  "implied_probability": 0.4762,
  "stake_posture": "small",
  "daily_chats_remaining": 4
}
```

## Supabase Schema

Run this SQL in the Supabase SQL editor:

```sql
create extension if not exists "pgcrypto";

create table if not exists public.users (
    id uuid primary key default gen_random_uuid(),
    email text not null unique,
    plan text not null default 'free' check (plan in ('free', 'premium')),
    daily_chat_count integer not null default 0,
    last_reset_date date not null default current_date,
    created_at timestamptz not null default timezone('utc', now())
);

create table if not exists public.conversations (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references public.users(id) on delete cascade,
    messages jsonb not null default '[]'::jsonb,
    created_at timestamptz not null default timezone('utc', now())
);

create table if not exists public.bet_tracker (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references public.users(id) on delete cascade,
    match text not null,
    amount numeric(10, 2) not null,
    odds numeric(10, 2) not null,
    outcome text not null default 'pending' check (outcome in ('win', 'loss', 'pending')),
    profit_loss numeric(10, 2) not null default 0,
    created_at timestamptz not null default timezone('utc', now())
);

create table if not exists public.world_cup_matches (
    id uuid primary key default gen_random_uuid(),
    api_football_fixture_id bigint not null unique,
    home_team text not null,
    away_team text not null,
    home_team_aliases jsonb not null default '[]'::jsonb,
    away_team_aliases jsonb not null default '[]'::jsonb,
    kickoff_time timestamptz,
    venue text,
    stage text,
    status text,
    home_score integer,
    away_score integer,
    raw_payload jsonb not null default '{}'::jsonb,
    last_fetched_at timestamptz not null,
    created_at timestamptz not null default timezone('utc', now()),
    updated_at timestamptz not null default timezone('utc', now())
);

create index if not exists idx_world_cup_matches_kickoff_time
    on public.world_cup_matches(kickoff_time);

grant usage on schema public to service_role;
grant select, insert, update on public.world_cup_matches to service_role;
```

## API-Football Cache Flow

Chat requests do not call API-Football. World Cup fixtures are refreshed manually or by a scheduled job through `POST /world-cup/refresh`, persisted in `world_cup_matches`, then served through a short in-memory TTL cache. This keeps the normal chat path cheap:

```text
API-Football / API-SPORTS
-> scheduled or manual refresh
-> Supabase world_cup_matches
-> in-memory TTL cache
-> /chat
```

Relevant environment variables:

```text
API_FOOTBALL_KEY=
API_FOOTBALL_BASE_URL=https://v3.football.api-sports.io
WORLD_CUP_LEAGUE_ID=1
WORLD_CUP_SEASON=2026
WORLD_CUP_CACHE_TTL_SECONDS=600
WORLD_CUP_FIXTURE_REFRESH_HOURS=12
MATCH_DETECTION_FALLBACK_ENABLED=true
MATCH_DETECTION_MODEL=
INTERNAL_API_TOKEN=
```

Match detection uses a local tournament team alias registry first. If no confident cached fixture is found and the message looks match-specific, Matchmind can call `MATCH_DETECTION_MODEL` as a fallback extractor, then validates the proposed teams against Supabase fixtures before using any match context.

Manual refresh example:

```bash
curl -X POST http://localhost:8000/world-cup/refresh \
  -H "X-Internal-Token: $INTERNAL_API_TOKEN"
```

Manual verification checklist:

1. Refresh fixtures once with a valid `API_FOOTBALL_KEY`.
2. Call `GET /world-cup/fixtures` and confirm `count`, fixture freshness, and `api_football_usage.fixture_requests`.
3. Send `Estoy pensando en meter 20€ a España contra Alemania a cuota 2.10`.
4. Send `Thinking of putting €20 on Spain to beat Germany at 2.10`.
5. Send `Spain vs Alemania at 2.10, cómo lo ves?`.
6. Send `Argentina campeona del mundial a cuota 6.50` and confirm no forced match fixture context.
7. Send `¿Qué apuesta ves buena hoy?` and confirm normal clarification behavior.
8. Remove or break `API_FOOTBALL_KEY`; chat should still work from cached Supabase data or without match context.
9. Repeat chat calls and confirm `api_football_usage.fixture_requests` does not increase.
10. Wait for `WORLD_CUP_CACHE_TTL_SECONDS`, then confirm chat can reload fixtures from Supabase without calling API-Football.

## Notes

- Free users are limited to `5` chat requests per day by default.
- Premium users bypass the daily message limit.
- Matchmind never places bets; it only provides analysis and coaching.
- The coach parses decimal odds, stake, teams, and obvious markets before calling the AI model so implied probability is stable even when live data is unavailable.
- English and Spanish are supported in the coach flow. Parser output is canonicalized to English for API consistency, while the coach replies in the detected user language.
- API-Football fixture context is cached persistently in Supabase and only refreshed outside the normal per-message chat path.
