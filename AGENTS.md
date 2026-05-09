# Matchmind — Project Brief & Decision Log

## Concept

Matchmind is an AI-powered betting coach web app focused on the 2026 FIFA World Cup (June 11 - July 19, 2026). Users describe bets they are considering and the app gives them a direct, honest analysis combining bookmaker odds, statistical data, and Polymarket prediction market probabilities.

The AI acts as a knowledgeable friend: opinionated, direct, and always gives a confidence score out of 10.

**The app never places bets. It is a pure analysis and coaching tool.**

---

## Core Value Proposition

"Your expert friend who combines stats, bookmaker odds, and prediction market wisdom to tell you the truth before you bet on the World Cup."

### What makes Matchmind different from ChatGPT
- Real-time bookmaker odds integrated
- Polymarket prediction market data integrated
- World Cup 2026 context always present
- Tracks the user's bet history and decision quality
- UX designed specifically for this use case

---

## Target Users
- Casual bettors who only bet on big events like the World Cup
- Regular bettors who already use betting platforms
- People who currently improvise with ChatGPT for betting analysis

---

## The Four Core Features

### 1. Chat with the Coach
Conversational UI where the user describes a bet and the coach gives an honest, data-backed take with a confidence score out of 10.

### 2. Daily Feed / Market Signals
Every morning, a feed of the top matches of the day plus tournament-level market signals. Because Polymarket currently has stronger World Cup 2026 coverage for long-term markets than match-level markets, Polymarket should power a "Market Signals" layer first rather than being forced into every match card.

### 3. Odds Analyzer
The user inputs a specific odds from any bookmaker and the app tells them if it represents good or bad value compared to the estimated real probability.

### 4. Bet Tracker
The user logs their bets manually. The app tracks outcomes, win rate, and P&L over the tournament.

---

## Business Model

### Freemium
- **Free tier:** 5 AI chat messages per day, basic daily feed, limited bet history
- **Premium tier:** Unlimited chats, full divergence alerts, complete history with metrics

### Pricing
- €4.99/month
- €9.99 one-time payment for the full tournament (main conversion hook)

The tournament pass is the key pricing insight: users perceive it as a bounded, one-time purchase rather than an ongoing subscription.

---

## Data Sources

| Source | Purpose |
|---|---|
| API-Football | Team stats, standings, recent form, head-to-head history |
| The Odds API | Real-time bookmaker odds across multiple markets |
| Polymarket | Crowd wisdom implied probabilities from prediction markets |

### Why Polymarket matters
Polymarket prices reflect aggregated probability from people betting real money. Combined with bookmaker odds and stats, divergences between sources reveal actionable insights the coach can explain.

---

## Tech Stack

| Layer | Technology | Notes |
|---|---|---|
| Frontend | Lovable or V0 | Built separately |
| Backend | Python + FastAPI | Async throughout |
| Database + Auth | Supabase | RLS enabled |
| AI Model | OpenAI GPT-5.4 mini | See model decision below |
| Payments | Stripe | Later phase |
| HTTP client | httpx | Async API calls |
| Deployment | Railway or Render | Backend hosting |

---

## Key Decisions Log

### Name: Matchmind
"BetCoach" was the original working name but was discarded because the "Bet" prefix triggers automatic filters on distribution platforms (App Store, Google Play) and advertising networks, and likely has trademark conflicts. Matchmind works in both English and Spanish, has no direct gambling connotation, and conveys the core value of the product.

### AI Model: GPT-5.4 mini
Chosen after a structured evaluation of all available OpenAI models. Selected for the best balance of response quality, cost, and latency for Matchmind's specific use case: short, frequent, conversational messages.

Cost projection for 500 active users (400 free + 100 premium) over the 38-day tournament: approximately $168 total inference cost.

### Database: Supabase
Chosen over Firebase and self-hosted PostgreSQL for speed of setup. Provides database, auth, and REST API in one platform. Configured with:
- Data API: enabled
- Automatically expose new tables: disabled (manual control for security)
- Automatic RLS: enabled (critical — ensures users can only access their own data)

### Supabase API Keys Usage
- **Publishable key:** frontend (Lovable/V0)
- **Secret key:** backend FastAPI (.env)

### AI Provider: OpenAI (not Anthropic Claude)
Initial plan included Claude API. Switched to OpenAI GPT during early backend setup.

### Data Caching
Provider data should not be fetched directly in the normal chat request path. The preferred pattern is:

```text
external provider
-> internal refresh/seed endpoint
-> Supabase cache table
-> short in-memory TTL cache
-> chat/feed/UI endpoint
```

API-Football fixtures use this pattern through `world_cup_matches`. Polymarket uses `polymarket_markets` and `polymarket_market_snapshots`.

### Fallback Strategy for Live Data
If team names are not detected in a user message, or if any external API call fails, the chat endpoint falls back gracefully and the coach continues without live data. The chat never crashes due to a data source failure.

### Polymarket Scope
Polymarket should be used in v1 for:

- World Cup winner markets
- Group winner markets
- Team advancement/progression markets
- Tournament-level market signals
- Chat context for supported long-term bets

Avoid using Polymarket in v1 for:

- Daily match winner predictions
- Over/under goals
- Handicaps
- Cards/corners
- Any market requiring active fixture-level Polymarket coverage

Polymarket market type classification is deterministic rule-based text matching, not LLM classification. Detailed decisions live in `docs/polymarket-integration.md`.

---

## Database Schema

### users
| Field | Type |
|---|---|
| id | uuid |
| email | text |
| plan | text (free/premium) |
| daily_chat_count | integer |
| last_reset_date | date |
| created_at | timestamp |

### conversations
| Field | Type |
|---|---|
| id | uuid |
| user_id | uuid |
| messages | jsonb |
| created_at | timestamp |

### bet_tracker
| Field | Type |
|---|---|
| id | uuid |
| user_id | uuid |
| match | text |
| amount | numeric |
| odds | numeric |
| outcome | text (win/loss/pending) |
| profit_loss | numeric |
| created_at | timestamp |

### world_cup_matches
Caches API-Football World Cup fixture context for chat and UI reads.

### polymarket_markets
Stores the latest normalized state of each usable or discovered Polymarket World Cup market.

### polymarket_market_snapshots
Stores historical Polymarket price/liquidity observations for movement and rising-signal features.

---

## Backend Project Structure

```text
matchmind/
├── apps/
│   ├── api/
│   │   ├── app/
│   │   │   ├── main.py
│   │   │   ├── config.py
│   │   │   ├── routers/
│   │   │   ├── services/
│   │   │   └── models/
│   │   ├── tests/
│   │   ├── requirements.txt
│   │   └── README.md
│   └── web/
├── docs/
├── packages/
├── scripts/
├── tmp/
├── .env.example
├── Makefile
└── README.md
```

## Environment Variables

```
SUPABASE_URL=
SUPABASE_KEY=
OPENAI_API_KEY=
API_FOOTBALL_KEY=
ODDS_API_KEY=
STRIPE_SECRET_KEY=
POLYMARKET_DISCOVERY_PATH=
POLYMARKET_GAMMA_BASE_URL=
POLYMARKET_CLOB_BASE_URL=
POLYMARKET_CACHE_TTL_SECONDS=
POLYMARKET_REFRESH_CLOB_TOKEN_LIMIT=
POLYMARKET_MIN_MATCH_CONFIDENCE=
POLYMARKET_MIN_SIGNAL_QUALITY=
```

---

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | /health | Health check, confirms DB connection |
| POST | /chat | Main coach chat endpoint |
| GET | /world-cup/fixtures | Cached World Cup fixture context |
| POST | /world-cup/refresh | Internal API-Football fixture refresh |
| GET | /polymarket/signals | Cached Polymarket market signals |
| POST | /polymarket/seed-from-discovery | Internal Polymarket seed from local exploration JSON |
| POST | /polymarket/refresh | Internal Polymarket live refresh |
| POST / GET / PATCH / DELETE | /bets | Bet tracker operations |

### POST /chat
- **Input:** `{ user_id, message }`
- **Logic:** checks daily limit for free users, extracts bet facts, reads cached API-Football/Polymarket context when relevant, injects compact context into the prompt, calls OpenAI
- **Output:** `{ response, confidence_score, daily_chats_remaining }`

### GET /polymarket/signals
- Returns active usable World Cup 2026 market signals from Supabase/memory.
- Powers Market Signals and future divergence surfaces.

### POST /polymarket/seed-from-discovery
- Seeds Supabase from `tmp/polymarket_world_cup_discovery.json`.
- Useful when local Polymarket API access is blocked.

### POST /polymarket/refresh
- Refreshes Polymarket data from Gamma/CLOB APIs.
- Intended for scheduled jobs in an environment that can reach Polymarket.

---

## Execution Plan

### Phase 1 - Foundation (done)
- FastAPI project structure initialized
- Supabase connected and schema created
- /health endpoint working
- /chat endpoint working with fake user

### Phase 2 - Live Data (current)
- API-Football fixture cache integrated
- Polymarket cache, seed, refresh, signals, and chat context integrated
- Next: The Odds API cache and bookmaker-vs-crowd divergence
- Next: Feed/Pronósticos UI surfaces on top of cached data

### Phase 3 - UX and Polish (~May 31)
- Final frontend build in Lovable/V0
- Mobile-first design
- 30-second onboarding flow
- Loading states, errors, empty states
- End-to-end payment flow testing

### Phase 4 - Launch (~June 7)
- Production deployment
- Closed beta with 10-20 real users
- Final adjustments based on feedback
- Landing page live with tournament pass pricing hook

---

## Risks

**Polymarket API:** No official public API documentation. Needs to be validated in Phase 2. Fallback option: Betfair Exchange, which serves a similar prediction market role.

**Regulation:** Matchmind does not execute bets or handle betting funds — it only charges for an analysis service. Worth a quick legal review for Spain and other target markets.

**Post-tournament retention:** The tournament pass model resolves short-term monetization. Long-term product strategy (other tournaments, other sports) is out of scope for v1 but worth keeping in mind during architecture decisions.
