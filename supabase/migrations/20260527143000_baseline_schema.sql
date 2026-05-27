-- Matchmind baseline schema.
-- This migration is intentionally idempotent so it can be applied to an
-- existing Supabase project without dropping data.

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

alter table public.users
    add column if not exists email text,
    add column if not exists name text,
    add column if not exists avatar_emoji text not null default '👤',
    add column if not exists plan text not null default 'free',
    add column if not exists daily_chat_count integer not null default 0,
    add column if not exists last_reset_date date not null default current_date,
    add column if not exists created_at timestamptz not null default timezone('utc', now());

alter table public.users
    alter column avatar_emoji set default '👤',
    alter column plan set default 'free',
    alter column daily_chat_count set default 0,
    alter column last_reset_date set default current_date,
    alter column created_at set default timezone('utc', now());

alter table public.users drop constraint if exists users_plan_check;
alter table public.users
    add constraint users_plan_check check (plan in ('free', 'premium'));

update public.users
    set email = lower(btrim(email))
    where email is not null and email <> lower(btrim(email));

alter table public.users drop constraint if exists users_email_normalized_check;
alter table public.users
    add constraint users_email_normalized_check check (email is null or email = lower(btrim(email)));

create unique index if not exists idx_users_email_normalized
    on public.users (lower(email))
    where email is not null;

create table if not exists public.conversations (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references public.users(id) on delete cascade,
    messages jsonb not null default '[]'::jsonb,
    created_at timestamptz not null default timezone('utc', now())
);

alter table public.conversations
    add column if not exists user_id uuid references public.users(id) on delete cascade,
    add column if not exists messages jsonb not null default '[]'::jsonb,
    add column if not exists created_at timestamptz not null default timezone('utc', now());

create index if not exists idx_conversations_user_created_at
    on public.conversations(user_id, created_at desc);

create table if not exists public.bet_tracker (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references public.users(id) on delete cascade,
    match text not null,
    pick text not null,
    market_type text not null,
    bookmaker text,
    amount numeric(10, 2) not null,
    odds numeric(10, 2) not null,
    outcome text not null default 'pending' check (outcome in ('win', 'loss', 'pending', 'cashed_out')),
    profit_loss numeric(10, 2) not null default 0,
    created_at timestamptz not null default timezone('utc', now())
);

alter table public.bet_tracker
    add column if not exists user_id uuid references public.users(id) on delete cascade,
    add column if not exists match text,
    add column if not exists pick text,
    add column if not exists market_type text,
    add column if not exists bookmaker text,
    add column if not exists amount numeric(10, 2),
    add column if not exists odds numeric(10, 2),
    add column if not exists outcome text not null default 'pending',
    add column if not exists profit_loss numeric(10, 2) not null default 0,
    add column if not exists created_at timestamptz not null default timezone('utc', now());

alter table public.bet_tracker drop constraint if exists bet_tracker_outcome_check;
alter table public.bet_tracker
    add constraint bet_tracker_outcome_check check (outcome in ('win', 'loss', 'pending', 'cashed_out'));

create index if not exists idx_bet_tracker_user_created_at
    on public.bet_tracker(user_id, created_at desc);

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

alter table public.world_cup_matches
    add column if not exists api_football_fixture_id bigint,
    add column if not exists home_team text,
    add column if not exists away_team text,
    add column if not exists home_team_aliases jsonb not null default '[]'::jsonb,
    add column if not exists away_team_aliases jsonb not null default '[]'::jsonb,
    add column if not exists kickoff_time timestamptz,
    add column if not exists venue text,
    add column if not exists stage text,
    add column if not exists status text,
    add column if not exists home_score integer,
    add column if not exists away_score integer,
    add column if not exists raw_payload jsonb not null default '{}'::jsonb,
    add column if not exists last_fetched_at timestamptz,
    add column if not exists created_at timestamptz not null default timezone('utc', now()),
    add column if not exists updated_at timestamptz not null default timezone('utc', now());

create unique index if not exists idx_world_cup_matches_fixture_id
    on public.world_cup_matches(api_football_fixture_id);

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

alter table public.polymarket_markets
    add column if not exists polymarket_event_id text,
    add column if not exists polymarket_market_id text,
    add column if not exists condition_id text,
    add column if not exists market_type text,
    add column if not exists matched_team text,
    add column if not exists matched_teams jsonb not null default '[]'::jsonb,
    add column if not exists matched_group text,
    add column if not exists matched_player text,
    add column if not exists question text,
    add column if not exists slug text,
    add column if not exists event_title text,
    add column if not exists event_slug text,
    add column if not exists outcomes jsonb not null default '[]'::jsonb,
    add column if not exists outcome_prices jsonb not null default '[]'::jsonb,
    add column if not exists yes_price numeric,
    add column if not exists no_price numeric,
    add column if not exists liquidity numeric,
    add column if not exists volume numeric,
    add column if not exists active boolean not null default false,
    add column if not exists closed boolean not null default false,
    add column if not exists archived boolean not null default false,
    add column if not exists end_date timestamptz,
    add column if not exists clob_token_ids jsonb not null default '[]'::jsonb,
    add column if not exists best_bid numeric,
    add column if not exists best_ask numeric,
    add column if not exists midpoint numeric,
    add column if not exists spread numeric,
    add column if not exists raw_payload jsonb not null default '{}'::jsonb,
    add column if not exists match_confidence numeric not null default 0,
    add column if not exists signal_quality_score integer not null default 0,
    add column if not exists is_usable boolean not null default false,
    add column if not exists last_fetched_at timestamptz,
    add column if not exists created_at timestamptz not null default timezone('utc', now()),
    add column if not exists updated_at timestamptz not null default timezone('utc', now());

create unique index if not exists idx_polymarket_markets_market_id
    on public.polymarket_markets(polymarket_market_id);

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

alter table public.users enable row level security;
alter table public.conversations enable row level security;
alter table public.bet_tracker enable row level security;
alter table public.referral_partners enable row level security;
alter table public.referral_codes enable row level security;
alter table public.referral_attributions enable row level security;
alter table public.world_cup_matches enable row level security;
alter table public.polymarket_markets enable row level security;
alter table public.polymarket_market_snapshots enable row level security;
alter table public.bookmaker_events enable row level security;
alter table public.bookmaker_odds enable row level security;
alter table public.bookmaker_odds_snapshots enable row level security;
alter table public.bookmaker_market_consensus enable row level security;

revoke all on public.users from anon, authenticated;
revoke all on public.conversations from anon, authenticated;
revoke all on public.bet_tracker from anon, authenticated;
revoke all on public.referral_partners from anon, authenticated;
revoke all on public.referral_codes from anon, authenticated;
revoke all on public.referral_attributions from anon, authenticated;
revoke all on public.world_cup_matches from anon, authenticated;
revoke all on public.polymarket_markets from anon, authenticated;
revoke all on public.polymarket_market_snapshots from anon, authenticated;
revoke all on public.bookmaker_events from anon, authenticated;
revoke all on public.bookmaker_odds from anon, authenticated;
revoke all on public.bookmaker_odds_snapshots from anon, authenticated;
revoke all on public.bookmaker_market_consensus from anon, authenticated;

-- Browser clients use FastAPI instead of direct Supabase table access. Keep
-- service_role as the only role with table privileges unless backend-only
-- product rules are moved into database policies or functions.
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

drop policy if exists "Users can read own profile" on public.users;
create policy "Users can read own profile"
    on public.users for select
    to authenticated
    using (id = auth.uid());

drop policy if exists "Users can update own profile" on public.users;
drop policy if exists "Users can read own conversations" on public.conversations;
create policy "Users can read own conversations"
    on public.conversations for select
    to authenticated
    using (user_id = auth.uid());

drop policy if exists "Users can manage own bets" on public.bet_tracker;
drop policy if exists "Users can read own referral partners" on public.referral_partners;
create policy "Users can read own referral partners"
    on public.referral_partners for select
    to authenticated
    using (user_id = auth.uid());

drop policy if exists "Users can read own referral codes" on public.referral_codes;
create policy "Users can read own referral codes"
    on public.referral_codes for select
    to authenticated
    using (owner_user_id = auth.uid() or partner_id in (
        select id from public.referral_partners where user_id = auth.uid()
    ));

drop policy if exists "Users can read own referral attributions" on public.referral_attributions;
create policy "Users can read own referral attributions"
    on public.referral_attributions for select
    to authenticated
    using (
        referred_user_id = auth.uid()
        or referrer_user_id = auth.uid()
        or partner_id in (
            select id from public.referral_partners where user_id = auth.uid()
        )
    );
