# Matchmind Backend

FastAPI backend foundation for Matchmind, an AI-powered betting coach focused on the 2026 FIFA World Cup.

## Project Structure

```text
apps/api/
├── app/
│   ├── main.py
│   ├── config.py
│   ├── routers/
│   │   ├── bets.py
│   │   ├── chat.py
│   │   ├── conversations.py
│   │   ├── odds.py
│   │   ├── polymarket.py
│   │   ├── referrals.py
│   │   ├── users.py
│   │   └── world_cup.py
│   ├── services/
│   │   ├── api_football.py
│   │   ├── bet_parser.py
│   │   ├── bets.py
│   │   ├── gpt.py
│   │   ├── odds_api.py
│   │   ├── polymarket.py
│   │   ├── referrals.py
│   │   ├── supabase.py
│   │   └── world_cup_teams.py
│   └── models/
│       ├── bets.py
│       ├── chat.py
│       ├── conversations.py
│       ├── referrals.py
│       └── users.py
├── tests/
├── .env.example
├── requirements.txt
└── README.md
```

## Setup

1. Create and activate a virtual environment.
2. Install dependencies from the repo root:

```bash
make api-install
```

3. Copy the root `.env.example` to `.env` and fill in your project values. The API also reads `apps/api/.env` if you prefer a service-local file.
4. Run the API locally from the repo root:

```bash
make api-dev
```

Or run it directly from this directory:

```bash
cd apps/api
uvicorn app.main:app --reload
```

5. Run tests from the repo root:

```bash
make api-test
```

## Endpoints

- `GET /health` checks API and Supabase connectivity.
- `GET /users/me` returns the authenticated user's name, plan, and chat usage. Requires a Supabase bearer token unless `ALLOW_DEV_AUTH_FALLBACK=true`.
- `PATCH /users/me` updates the authenticated user's display name and avatar emoji.
- `GET /world-cup/fixtures` returns cached 2026 World Cup fixture context from Supabase/memory.
- `POST /world-cup/refresh` refreshes fixtures from API-Football. This is internal and requires `X-Internal-Token` matching `INTERNAL_API_TOKEN`.
- `GET /polymarket/signals` returns compact active World Cup 2026 prediction-market signals from Supabase/memory.
- `POST /polymarket/seed-from-discovery` seeds Polymarket markets from `POLYMARKET_DISCOVERY_PATH`. This is internal and requires `X-Internal-Token`.
- `POST /polymarket/refresh` refreshes Polymarket markets from Gamma/CLOB APIs. This is internal and requires `X-Internal-Token`.
- `GET /odds/matches` returns compact cached bookmaker consensus for match cards.
- `POST /odds/analyze` compares a user-entered price against cached bookmaker consensus.
- `POST /odds/seed-from-discovery` seeds bookmaker odds from `ODDS_API_DISCOVERY_PATH`. This is internal and requires `X-Internal-Token`.
- `POST /odds/refresh/events` refreshes The Odds API World Cup event ids. This is internal and requires `X-Internal-Token`.
- `POST /odds/refresh` refreshes featured World Cup match and outright bookmaker odds. This is internal and requires `X-Internal-Token`.
- `POST /payments/create-checkout-session` creates a Stripe Checkout Session for the one-time tournament pass. This requires a Supabase bearer token.
- `POST /payments/webhook` receives Stripe webhooks, verifies `Stripe-Signature`, and upgrades users to `plan = 'premium'` on `checkout.session.completed`.
- `POST /referrals/bar-partner` registers the authenticated user as a partner bar and generates a readable unique code.
- `POST /referrals/user-code` creates or returns the authenticated user's personal referral code.
- `GET /referrals/me` returns the authenticated user's partner-bar dashboard, personal referral metrics, plus any code they have applied.
- `GET /referrals/validate/{code}` validates a public referral code and returns only the public partner name and discount.
- `POST /referrals/apply` applies one referral code to the authenticated user.
- `POST /bets` logs a manual bet for the authenticated user.
- `GET /bets` returns the authenticated user's bet history plus tracker summary metrics.
- `PATCH /bets/{bet_id}` updates one of the authenticated user's tracked bets and recalculates P&L.
- `DELETE /bets/{bet_id}` deletes one of the authenticated user's tracked bets.
- `GET /conversations?limit=20` returns the authenticated user's conversation summaries derived from `conversations.messages`.
- `GET /conversations/{conversation_id}` returns one authenticated-user-scoped conversation and its stored messages.
- `POST /chat` accepts:

```json
{
  "message": "Thinking of betting €20 on Spain to beat Germany at 2.10",
  "preferred_language": "en",
  "conversation_id": null
}
```

Returns:

```json
{
  "conversation_id": "11111111-1111-1111-1111-111111111111",
  "response": "I lean fair at that number, but I would keep it controlled...",
  "confidence_score": 6,
  "verdict": "FAIR",
  "implied_probability": 0.4762,
  "stake_posture": "small",
  "market_signal": null,
  "daily_chats_remaining": 4,
  "chat_count": 1,
  "chat_count_limit": 5,
  "chat_limit_period": "day",
  "chats_remaining": 4
}
```

`POST /chat` requires a Supabase bearer token unless `ALLOW_DEV_AUTH_FALLBACK=true`. The backend derives the user id from the authenticated Supabase user and ignores any deprecated client-supplied `user_id`. `preferred_language` can be `"en"` or `"es"`. If omitted, the backend detects language from the message and asks the coach to answer in that language. `conversation_id` is optional; omit it to start a new conversation, or send a previous ID to append a follow-up and give the coach recent conversation memory.

The OpenAI call uses a strict JSON schema for `response`, `confidence_score`, `verdict`, `implied_probability`, and `stake_posture`. The visible `response` is allowed to be conversational and varied, while these metadata fields stay stable for UI rendering.

Chat provider context is resilient by design. API-Football, Polymarket, and bookmaker context builders are best-effort in the `/chat` route; a provider/cache failure is logged and omitted instead of crashing the chat request.

### Conversations

Conversation history uses the existing `conversations.messages` JSONB field; no additional Supabase columns are required for the current UI.

List summaries:

```bash
curl -H "Authorization: Bearer $SUPABASE_ACCESS_TOKEN" "http://localhost:8000/conversations?limit=20"
```

Fetch one conversation:

```bash
curl -H "Authorization: Bearer $SUPABASE_ACCESS_TOKEN" "http://localhost:8000/conversations/{conversation_id}"
```

Summaries derive `title` from the first user message, `last_message_preview` from the latest valid message, and `updated_at` from the latest message timestamp when available. A future explicit `updated_at` column would make this faster and cleaner, but it is not required for v1.

### Bet Tracker

Create a bet. User ownership comes from the Supabase bearer token:

```json
{
  "match": "Spain vs Germany - Spain win",
  "amount": 20,
  "odds": 2.1,
  "outcome": "pending"
}
```

The API calculates `profit_loss` server-side:

- `pending`: `0`
- `win`: `amount * (odds - 1)`
- `loss`: `-amount`

List response:

```json
{
  "bets": [],
  "summary": {
    "total_bets": 0,
    "pending_bets": 0,
    "wins": 0,
    "losses": 0,
    "win_rate": 0,
    "total_staked": 0,
    "profit_loss": 0,
    "roi": 0
  }
}
```

## Supabase Schema

Run this SQL in the Supabase SQL editor:

```sql
create extension if not exists "pgcrypto";

create table if not exists public.users (
    id uuid primary key default gen_random_uuid(),
    email text unique,
    name text,
    avatar_emoji text not null default '👤',
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

create table if not exists public.polymarket_markets (
    id uuid primary key default gen_random_uuid(),
    polymarket_event_id text,
    polymarket_market_id text not null unique,
    condition_id text,
    market_type text not null,
    matched_team text,
    matched_teams jsonb not null default '[]'::jsonb,
    matched_group text,
    matched_player text,
    question text not null,
    slug text,
    event_title text,
    event_slug text,
    outcomes jsonb not null default '[]'::jsonb,
    outcome_prices jsonb not null default '[]'::jsonb,
    yes_price numeric,
    no_price numeric,
    liquidity numeric,
    volume numeric,
    active boolean not null default false,
    closed boolean not null default false,
    archived boolean not null default false,
    end_date timestamptz,
    clob_token_ids jsonb not null default '[]'::jsonb,
    best_bid numeric,
    best_ask numeric,
    midpoint numeric,
    spread numeric,
    raw_payload jsonb not null default '{}'::jsonb,
    match_confidence numeric not null default 0,
    signal_quality_score integer not null default 0,
    is_usable boolean not null default false,
    last_fetched_at timestamptz not null,
    created_at timestamptz not null default timezone('utc', now()),
    updated_at timestamptz not null default timezone('utc', now())
);

create index if not exists idx_polymarket_markets_type_quality
    on public.polymarket_markets(market_type, is_usable, signal_quality_score desc);

create index if not exists idx_polymarket_markets_matched_team
    on public.polymarket_markets(matched_team);

create table if not exists public.polymarket_market_snapshots (
    id uuid primary key default gen_random_uuid(),
    polymarket_market_id text not null references public.polymarket_markets(polymarket_market_id) on delete cascade,
    yes_price numeric,
    no_price numeric,
    liquidity numeric,
    volume numeric,
    best_bid numeric,
    best_ask numeric,
    midpoint numeric,
    spread numeric,
    signal_quality_score integer not null default 0,
    fetched_at timestamptz not null default timezone('utc', now())
);

create index if not exists idx_polymarket_snapshots_market_time
    on public.polymarket_market_snapshots(polymarket_market_id, fetched_at desc);

create table if not exists public.bookmaker_events (
    id uuid primary key default gen_random_uuid(),
    odds_api_event_id text not null unique,
    api_football_fixture_id bigint,
    sport_key text not null,
    sport_title text,
    home_team text,
    away_team text,
    commence_time timestamptz,
    matchmind_match_key text,
    raw_payload jsonb not null default '{}'::jsonb,
    last_fetched_at timestamptz not null,
    created_at timestamptz not null default timezone('utc', now())
);

create index if not exists idx_bookmaker_events_commence_time
    on public.bookmaker_events(commence_time);

create index if not exists idx_bookmaker_events_match_key
    on public.bookmaker_events(matchmind_match_key);

create table if not exists public.bookmaker_odds (
    id uuid primary key default gen_random_uuid(),
    odds_api_event_id text not null references public.bookmaker_events(odds_api_event_id) on delete cascade,
    bookmaker_key text not null,
    bookmaker_title text,
    market_key text not null,
    line_key text not null,
    outcome_name text not null,
    outcome_team text,
    price numeric(10, 4) not null,
    point numeric(10, 3),
    odds_format text not null default 'decimal',
    bookmaker_last_update timestamptz,
    fetched_at timestamptz not null,
    raw_payload jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default timezone('utc', now()),
    unique (odds_api_event_id, bookmaker_key, market_key, outcome_name, line_key)
);

create index if not exists idx_bookmaker_odds_event_market
    on public.bookmaker_odds(odds_api_event_id, market_key);

create table if not exists public.bookmaker_odds_snapshots (
    id uuid primary key default gen_random_uuid(),
    odds_api_event_id text not null references public.bookmaker_events(odds_api_event_id) on delete cascade,
    bookmaker_key text not null,
    bookmaker_title text,
    market_key text not null,
    line_key text not null,
    outcome_name text not null,
    outcome_team text,
    price numeric(10, 4) not null,
    point numeric(10, 3),
    odds_format text not null default 'decimal',
    bookmaker_last_update timestamptz,
    fetched_at timestamptz not null,
    raw_payload jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default timezone('utc', now())
);

create index if not exists idx_bookmaker_snapshots_event_market_time
    on public.bookmaker_odds_snapshots(odds_api_event_id, market_key, fetched_at desc);

create table if not exists public.bookmaker_market_consensus (
    id uuid primary key default gen_random_uuid(),
    odds_api_event_id text not null references public.bookmaker_events(odds_api_event_id) on delete cascade,
    market_key text not null,
    line_key text not null,
    outcome_name text not null,
    outcome_team text,
    point numeric(10, 3),
    best_price numeric(10, 4),
    best_bookmaker_key text,
    best_bookmaker_title text,
    median_price numeric(10, 4),
    mean_price numeric(10, 4),
    min_price numeric(10, 4),
    max_price numeric(10, 4),
    no_vig_probability numeric(8, 6),
    bookmaker_count integer not null default 0,
    stale_bookmaker_count integer not null default 0,
    fetched_at timestamptz not null,
    created_at timestamptz not null default timezone('utc', now()),
    unique (odds_api_event_id, market_key, outcome_name, line_key)
);

create index if not exists idx_bookmaker_consensus_event_market
    on public.bookmaker_market_consensus(odds_api_event_id, market_key);

create table if not exists public.referral_partners (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references public.users(id) on delete cascade,
    partner_type text not null default 'bar' check (partner_type in ('bar')),
    business_name text not null,
    location text not null,
    responsible_name text not null,
    phone text not null,
    status text not null default 'active' check (status in ('active', 'pending', 'paused')),
    terms_accepted_at timestamptz not null,
    created_at timestamptz not null default timezone('utc', now()),
    updated_at timestamptz not null default timezone('utc', now())
);

create index if not exists idx_referral_partners_user_id
    on public.referral_partners(user_id);

create table if not exists public.referral_codes (
    id uuid primary key default gen_random_uuid(),
    code text unique not null check (code ~ '^[A-Z0-9]+$'),
    owner_type text not null default 'bar_partner' check (owner_type in ('bar_partner', 'user')),
    partner_id uuid references public.referral_partners(id) on delete cascade,
    owner_user_id uuid references public.users(id) on delete cascade,
    discount_type text not null default 'fixed_amount' check (discount_type in ('fixed_amount')),
    discount_amount numeric(10, 2) not null default 1.00 check (discount_amount >= 0),
    commission_amount numeric(10, 2) not null default 2.00 check (commission_amount >= 0),
    active boolean not null default true,
    starts_at timestamptz,
    ends_at timestamptz,
    created_at timestamptz not null default timezone('utc', now()),
    check (
        (owner_type = 'bar_partner' and partner_id is not null and owner_user_id is null)
        or
        (owner_type = 'user' and owner_user_id is not null and partner_id is null)
    )
);

create index if not exists idx_referral_codes_partner_id
    on public.referral_codes(partner_id);

create index if not exists idx_referral_codes_owner_user_id
    on public.referral_codes(owner_user_id);

create table if not exists public.referral_attributions (
    id uuid primary key default gen_random_uuid(),
    referred_user_id uuid not null references public.users(id) on delete cascade,
    referral_code_id uuid not null references public.referral_codes(id) on delete restrict,
    partner_id uuid references public.referral_partners(id) on delete restrict,
    referrer_user_id uuid references public.users(id) on delete restrict,
    applied_at timestamptz not null default timezone('utc', now()),
    converted_at timestamptz,
    gross_amount numeric(10, 2),
    stripe_checkout_session_id text,
    stripe_payment_intent_id text,
    conversion_source text,
    converted_price_type text,
    payout_cancelled_at timestamptz,
    payout_cancellation_reason text,
    stripe_dispute_id text,
    discount_amount numeric(10, 2),
    commission_amount numeric(10, 2),
    payout_status text not null default 'pending' check (payout_status in ('pending', 'approved', 'paid', 'cancelled')),
    created_at timestamptz not null default timezone('utc', now()),
    unique (referred_user_id),
    check (
        (partner_id is not null and referrer_user_id is null)
        or
        (partner_id is null and referrer_user_id is not null)
    )
);

create index if not exists idx_referral_attributions_partner_id
    on public.referral_attributions(partner_id);

create index if not exists idx_referral_attributions_code_id
    on public.referral_attributions(referral_code_id);

create index if not exists idx_referral_attributions_referrer_user_id
    on public.referral_attributions(referrer_user_id);

create unique index if not exists idx_referral_attributions_stripe_checkout_session_id
    on public.referral_attributions(stripe_checkout_session_id)
    where stripe_checkout_session_id is not null;

create index if not exists idx_referral_attributions_conversion_source
    on public.referral_attributions(conversion_source);

create index if not exists idx_referral_attributions_stripe_payment_intent_id
    on public.referral_attributions(stripe_payment_intent_id)
    where stripe_payment_intent_id is not null;

grant usage on schema public to service_role;
grant select, insert, update on public.users to service_role;
grant select, insert, update on public.conversations to service_role;
grant select, insert, update, delete on public.bet_tracker to service_role;
grant select, insert, update on public.world_cup_matches to service_role;
grant select, insert, update on public.polymarket_markets to service_role;
grant select, insert on public.polymarket_market_snapshots to service_role;
grant select, insert, update on public.bookmaker_events to service_role;
grant select, insert, update on public.bookmaker_odds to service_role;
grant select, insert on public.bookmaker_odds_snapshots to service_role;
grant select, insert, update on public.bookmaker_market_consensus to service_role;
grant select, insert, update on public.referral_partners to service_role;
grant select, insert, update on public.referral_codes to service_role;
grant select, insert, update on public.referral_attributions to service_role;
```

User referral perks are computed from `referral_attributions`, so no extra rewards table is required for v1:

| Requirement | User perk |
|---|---|
| 1 friend registers with the code | €8.99 World Cup Pass price |
| 2 friends purchase | 50% discount, €4.99 |
| 5 friends purchase | 75% discount, €2.49 |
| 7 friends purchase | Free World Cup Pass |
| 10 friends purchase | Founder Circle / priority beta access for future League and Champions versions |

If a user has already purchased, the API still returns the same perk state so the frontend can present it as future Matchmind credit instead of asking for a refund or extra claim step.

Paid referral counts and bar commissions require Stripe proof on the attribution row. `converted_at` alone is not treated as real-money evidence; the API only counts a paid referral when the row also has `conversion_source = 'stripe_checkout_completed'`, a non-empty `stripe_checkout_session_id` written from a verified Stripe webhook, and `payout_status != 'cancelled'`.

If Stripe later sends `charge.dispute.created` or `payment_intent.canceled`, the API marks the matching attribution `payout_status = 'cancelled'` unless the commission has already been paid.

Seed a local dev user if you are using the default frontend env:

```sql
insert into public.users (id, email, plan)
values ('a87d09e8-7e10-46b8-9927-c9500c9559cf', 'dev@matchmind.local', 'free')
on conflict (id) do nothing;
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
POLYMARKET_DISCOVERY_PATH=tmp/polymarket_world_cup_discovery.json
POLYMARKET_GAMMA_BASE_URL=https://gamma-api.polymarket.com
POLYMARKET_CLOB_BASE_URL=https://clob.polymarket.com
POLYMARKET_CACHE_TTL_SECONDS=600
POLYMARKET_REFRESH_CLOB_TOKEN_LIMIT=0
POLYMARKET_MIN_MATCH_CONFIDENCE=0.7
POLYMARKET_MIN_SIGNAL_QUALITY=40
ODDS_API_KEY=
ODDS_API_BASE_URL=https://api.the-odds-api.com
ODDS_API_REGIONS=eu
ODDS_API_BOOKMAKERS=
ODDS_API_MARKETS=h2h,spreads,totals
ODDS_API_OUTRIGHT_MARKETS=outrights
ODDS_API_ODDS_FORMAT=decimal
ODDS_API_CACHE_TTL_SECONDS=600
ODDS_API_DISCOVERY_PATH=tmp/odds_api_world_cup_discovery.json
INTERNAL_API_TOKEN=
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
```

Match detection uses a local tournament team alias registry first. If no confident cached fixture is found and the message looks match-specific, Matchmind can call `MATCH_DETECTION_MODEL` as a fallback extractor, then validates the proposed teams against Supabase fixtures before using any match context.

Polymarket context reads from Supabase first, then falls back to the normalized exploration output at `POLYMARKET_DISCOVERY_PATH` if the table is empty or unavailable. Chat only injects it for supported long-term markets such as World Cup winner, group winner, and team advancement. Match-level bets, totals, cards, corners, and handicaps intentionally do not receive a Polymarket context block until active fixture-level World Cup markets exist.

## The Odds API Cache Flow

Chat requests do not call The Odds API. Bookmaker data is refreshed manually or by a scheduled job, persisted in `bookmaker_events`, `bookmaker_odds`, `bookmaker_odds_snapshots`, and `bookmaker_market_consensus`, then served through memory cache:

```text
The Odds API
-> scheduled or manual refresh
-> Supabase bookmaker odds tables
-> in-memory TTL cache
-> /chat, /odds/matches, /odds/analyze
```

On a machine where live odds refresh is not desired, seed the first cache from the exploration JSON:

```bash
curl -X POST http://localhost:8000/odds/seed-from-discovery \
  -H "X-Internal-Token: $INTERNAL_API_TOKEN"
```

In an environment that can reach The Odds API, refresh live featured markets:

```bash
curl -X POST http://localhost:8000/odds/refresh \
  -H "X-Internal-Token: $INTERNAL_API_TOKEN"
```

The current product-facing market keys are:

- `h2h`: match winner / 1X2.
- `spreads`: goal handicap.
- `totals`: goals over/under.
- `outrights`: World Cup winner futures.

Match Radar reads `GET /odds/matches`. It shows 1X2 best prices by default and exposes `totals` and `spreads` inside the expandable "More markets" area, labelled for users as "Goals over/under" and "Goal handicap."

## Stripe Test-Mode Checkout

Payments are test-mode only for local development. Create one-time Stripe Prices for €9.99, €8.99, €4.99, and €2.49 under the World Cup Tournament Pass product, then set the backend `.env` values:

```text
STRIPE_SECRET_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_TOURNAMENT_PASS_PRICE_ID=price_...
STRIPE_TOURNAMENT_PASS_REFERRAL_PRICE_ID=price_...
STRIPE_TOURNAMENT_PASS_INSIDER_PRICE_ID=price_...
STRIPE_TOURNAMENT_PASS_CAPTAIN_PRICE_ID=price_...
APP_URL=http://localhost:3000
```

The API uses the best eligible price for the authenticated user: applied referral code, personal referral tier, or the normal €9.99 price. Free personal referral tiers activate the pass directly without starting Stripe Checkout.

Start the API, then forward webhooks with the Stripe CLI:

```bash
stripe listen --forward-to localhost:8000/payments/webhook
```

Copy the `whsec_...` value printed by the CLI into `STRIPE_WEBHOOK_SECRET`. In the web app, sign in with Supabase Auth, open Profile, and use the upgrade button. Stripe's standard test card is `4242 4242 4242 4242` with any future expiry, CVC, and postal code.

Do not put Stripe secret keys in `apps/web/.env.local`. The frontend only calls `/payments/create-checkout-session` with the user's Supabase bearer token and redirects to the returned Checkout URL.

See [Stripe Payments](../../docs/stripe-payments.md) for the complete local setup, troubleshooting guide, and production checklist.

## Current Not-Yet-Wired Areas

- The Odds API is integrated as a cache-first bookmaker layer for featured match odds and tournament outrights. Additional event-specific markets such as BTTS, cards, corners, and player props are still not wired into product surfaces.
- Stripe supports the one-time test-mode tournament pass only. Subscriptions, billing portal, refunds, invoices, coupons, and tax logic are intentionally not implemented yet.
- Frontend auth is integrated for Supabase email/password sessions when the web app has public Supabase env vars. Local development can still use the dev user ID documented above.

## Polymarket Cache Flow

Chat requests do not call Polymarket. Market data is refreshed manually or by a scheduled job, persisted in `polymarket_markets`, then served through memory cache:

```text
Polymarket Gamma/CLOB APIs
-> scheduled or manual refresh
-> Supabase polymarket_markets + polymarket_market_snapshots
-> in-memory TTL cache
-> /chat and /polymarket/signals
```

On a machine where Polymarket is blocked, seed the first cache from the exploration JSON:

```bash
curl -X POST http://localhost:8000/polymarket/seed-from-discovery \
  -H "X-Internal-Token: $INTERNAL_API_TOKEN"
```

In an environment that can reach Polymarket, refresh live data:

```bash
curl -X POST http://localhost:8000/polymarket/refresh \
  -H "X-Internal-Token: $INTERNAL_API_TOKEN"
```

Manual refresh example:

```bash
curl -X POST http://localhost:8000/world-cup/refresh \
  -H "X-Internal-Token: $INTERNAL_API_TOKEN"
```

Manual verification checklist:

1. Refresh fixtures once with a valid `API_FOOTBALL_KEY`.
2. Call `GET /world-cup/fixtures` and confirm `count`, fixture freshness, and `api_football_usage.fixture_requests`.
3. Seed or refresh bookmaker odds with `POST /odds/seed-from-discovery` or `POST /odds/refresh`.
4. Call `GET /odds/matches` and confirm match cards have `h2h` rows plus `featured_markets.totals` and/or `featured_markets.spreads` when covered.
5. Open Match Radar in the web app and confirm bookmaker odds appear under each covered fixture.
6. Expand "More markets" and confirm "Goals over/under" and "Goal handicap" rows appear with best price, fair probability, and bookmaker count.
7. Send `Estoy pensando en meter 20€ a España contra Alemania a cuota 2.10`.
8. Send `Thinking of putting €20 on Spain to beat Germany at 2.10`.
9. Send `Spain vs Alemania at 2.10, cómo lo ves?`.
10. Send `Argentina campeona del mundial a cuota 6.50` and confirm no forced match fixture context.
11. Send `¿Qué apuesta ves buena hoy?` and confirm normal clarification behavior.
12. Send a follow-up such as `what if I can get 2.30 instead?` with the returned `conversation_id` and confirm the coach treats it as the same bet with the updated price.
13. Call `GET /conversations` and confirm the chat appears in history.
14. Call `GET /conversations/{conversation_id}` and confirm stored user/assistant messages are returned.
15. Remove or break `API_FOOTBALL_KEY`; chat should still work from cached Supabase data or without match context.
16. Repeat chat calls and confirm `api_football_usage.fixture_requests` does not increase.
17. Wait for `WORLD_CUP_CACHE_TTL_SECONDS`, then confirm chat can reload fixtures from Supabase without calling API-Football.

## Notes

- Free users are limited to `5` chat requests per day by default.
- Premium users have a configurable fair-use limit of `200` chat requests per week by default.
- Matchmind never places bets; it only provides analysis and coaching.
- The coach parses decimal odds, stake, teams, and obvious markets before calling the AI model so implied probability is stable even when live data is unavailable.
- English and Spanish are supported in the coach flow. Parser output is canonicalized to English for API consistency, while the coach replies in the detected user language.
- Chat returns stable structured metadata for UI chips: `verdict`, `confidence_score`, `stake_posture`, and `implied_probability`.
- Conversations preserve follow-up memory through `conversation_id` and compact recent `conversation_memory` in the prompt.
- API-Football fixture context is cached persistently in Supabase and only refreshed outside the normal per-message chat path.
- The Odds API bookmaker context is cached persistently in Supabase and only refreshed or seeded outside the normal per-message chat path.
