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
```

## Notes

- Free users are limited to `5` chat requests per day by default.
- Premium users bypass the daily message limit.
- Matchmind never places bets; it only provides analysis and coaching.
- The coach parses decimal odds, stake, teams, and obvious markets before calling the AI model so implied probability is stable even when live data is unavailable.
- English and Spanish are supported in the coach flow. Parser output is canonicalized to English for API consistency, while the coach replies in the detected user language.
