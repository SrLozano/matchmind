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

### 2. Daily Feed
Every morning, a feed of the top matches of the day showing the divergence between bookmaker odds and Polymarket probabilities. Color coded: green = good value, yellow = neutral, red = avoid.

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
API responses from the three data sources are cached in memory for 10 minutes to avoid hitting free tier rate limits.

### Fallback Strategy for Live Data
If team names are not detected in a user message, or if any external API call fails, the chat endpoint falls back gracefully and the coach continues without live data. The chat never crashes due to a data source failure.

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

---

## Backend Project Structure

```
matchmind/
├── app/
│   ├── main.py
│   ├── config.py
│   ├── routers/
│   │   └── chat.py
│   ├── services/
│   │   ├── openai.py
│   │   ├── supabase.py
│   │   ├── api_football.py
│   │   ├── odds.py
│   │   └── polymarket.py
│   └── models/
│       └── chat.py
├── .env.example
├── requirements.txt
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
```

---

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | /health | Health check, confirms DB connection |
| POST | /chat | Main coach chat endpoint |
| GET | /feed | Daily feed with top matches and divergence scores |

### POST /chat
- **Input:** `{ user_id, message }`
- **Logic:** checks daily limit for free users, extracts team names, fetches live data in parallel, injects context into system prompt, calls OpenAI
- **Output:** `{ response, confidence_score, daily_chats_remaining }`

### GET /feed
- Returns top 3 matches of the day with bookmaker odds, Polymarket probabilities, and divergence score
- Powers the home screen of the frontend

---

## Execution Plan

### Phase 1 - Foundation (done)
- FastAPI project structure initialized
- Supabase connected and schema created
- /health endpoint working
- /chat endpoint working with fake user

### Phase 2 - Live Data (current)
- Integrate API-Football, The Odds API, Polymarket
- Inject live data context into chat system prompt
- Build /feed endpoint with divergence scores
- In-memory caching for API responses

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
