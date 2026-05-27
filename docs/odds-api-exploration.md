# The Odds API Exploration

This document records what Matchmind can extract from The Odds API and how that data should be used in the product. It is based on the current v4 documentation and the World Cup-specific docs checked on 2026-05-10.

Sources:

- The Odds API v4 docs: https://the-odds-api.com/liveapi/guides/v4/
- FIFA World Cup odds docs: https://the-odds-api.com/sports/fifa-world-cup-odds.html
- Betting markets list: https://the-odds-api.com/sports-odds-data/betting-markets.html
- Sports list: https://the-odds-api.com/sports-odds-data/sports-apis.html
- Bookmaker regions: https://the-odds-api.com/sports-odds-data/bookmaker-apis.html

## Product Role

The Odds API should be the bookmaker-pricing layer for Matchmind. API-Football explains football context, Polymarket gives crowd probability for long-term tournament markets, and The Odds API tells us where regulated or exchange books are actually pricing the bet.

Best v1 use:

- Compare a user-entered price against live bookmaker consensus.
- Show best available price across selected regions or books.
- Calculate no-vig implied probabilities for match winner, handicap, and totals.
- Detect bookmaker disagreement and simple value flags.
- Power richer Daily Feed match cards with 1X2, handicap, and over/under.
- Add bookmaker-vs-crowd divergence for World Cup winner markets.

Avoid in v1:

- Treating bookmaker consensus as truth.
- Calling The Odds API inside the normal chat request path.
- Over-indexing on player props, cards, and corners before coverage is verified for the World Cup.
- Showing affiliate or betslip links until the legal/product position is explicit.

## Relevant Sports

The important sport keys are:

```text
soccer_fifa_world_cup
soccer_fifa_world_cup_winner
```

`soccer_fifa_world_cup` covers live and upcoming World Cup matches and supports scores/results. `soccer_fifa_world_cup_winner` covers the tournament outright market.

The provider docs also list World Cup qualifiers and many club competitions, but those are out of scope for the 2026 tournament-first version.

## Extractable Data

### Sports Metadata

Endpoint:

```text
GET /v4/sports?apiKey=...
```

Useful fields:

- `key`: provider sport key.
- `group`: sport family, for example `Soccer`.
- `title`: human league or tournament name.
- `description`: provider description.
- `active`: whether the sport is currently available.
- `has_outrights`: whether outright/futures markets exist.

Matchmind use:

- Startup/health validation that World Cup keys are active.
- Admin/debug endpoint showing provider readiness.
- Guardrails so scheduled refreshes fail visibly if a sport key disappears.

This endpoint does not count against quota.

### Events

Endpoint:

```text
GET /v4/sports/{sport}/events?apiKey=...
```

Useful fields:

- `id`: The Odds API event id.
- `sport_key`, `sport_title`.
- `commence_time`.
- `home_team`, `away_team`.

Matchmind use:

- Map provider events to cached `world_cup_matches`.
- Discover upcoming/live event ids without spending odds quota.
- Feed event-specific odds refresh jobs.

The events endpoint does not count against quota.

### Featured Match Odds

Endpoint:

```text
GET /v4/sports/soccer_fifa_world_cup/odds?regions=eu&markets=h2h,spreads,totals&oddsFormat=decimal&apiKey=...
```

Useful top-level fields:

- `id`: event id.
- `sport_key`, `sport_title`.
- `commence_time`.
- `home_team`, `away_team`.
- `bookmakers`.

Useful bookmaker fields:

- `key`: stable bookmaker key, for example `pinnacle`.
- `title`: display name.
- `last_update`: bookmaker-specific freshness.
- `markets`.

Useful market fields:

- `key`: market key.
- `last_update`.
- `outcomes`.

Useful outcome fields:

- `name`: team, `Draw`, `Over`, or `Under`.
- `price`: decimal or American odds depending on request.
- `point`: handicap or total line when applicable.
- optional links/source ids/bet limits if requested.

Core markets:

- `h2h`: soccer 1X2 match winner, including draw.
- `spreads`: handicap.
- `totals`: over/under goals.
- `outrights`: futures.

Matchmind use:

- Daily Feed: show best 1X2 price and consensus.
- Chat: inject compact bookmaker context only after reading cache.
- Odds Analyzer: compare the user's offered odds against best price and no-vig consensus.
- Divergence: compare bookmaker consensus vs Polymarket for compatible markets.

Quota cost is `number of markets * number of regions`. The World Cup docs show `h2h,spreads,totals` for one region costing 3 credits.

### Event-Specific Additional Markets

Endpoint:

```text
GET /v4/sports/{sport}/events/{eventId}/odds?regions=...&markets=...&oddsFormat=decimal&apiKey=...
```

Additional soccer markets listed by the provider:

- `btts`: both teams to score.
- `draw_no_bet`.
- `h2h_3_way`.
- `double_chance`.
- `alternate_spreads_corners`.
- `alternate_totals_corners`.
- `alternate_spreads_cards`.
- `alternate_totals_cards`.

Soccer player prop markets listed by the provider:

- `player_goal_scorer_anytime`.
- `player_first_goal_scorer`.
- `player_last_goal_scorer`.
- `player_to_receive_card`.
- `player_to_receive_red_card`.
- `player_shots_on_target`.
- `player_shots`.
- `player_assists`.

Important caveat: additional markets are accessed one event at a time and coverage is not guaranteed for every sport/bookmaker. Player prop coverage is documented for major leagues and MLS with US bookmakers, so World Cup availability must be verified during a live discovery pass.

Matchmind use:

- V1.5 or v2 expansion into user-requested bets like "both teams to score" or "Messi anytime scorer".
- `GET /odds/events/{id}/markets` can be used shortly before kickoff to discover which markets actually exist for an event.

### Scores

Endpoint:

```text
GET /v4/sports/{sport}/scores?apiKey=...&daysFrom=3
```

Useful fields:

- Upcoming/live/recently completed games.
- Live and final scores where covered.
- Recently completed games up to 3 days back via `daysFrom`.

Matchmind use:

- Backfill bet tracker settlement hints.
- Cross-check API-Football score freshness.
- Lightweight match result fallback.

This should not replace API-Football for football stats, fixtures, and richer context.

### Historical Odds

Endpoints:

```text
GET /v4/historical/sports/{sport}/odds?...
GET /v4/historical/sports/{sport}/events?...
GET /v4/historical/sports/{sport}/events/{eventId}/odds?...
```

Useful capabilities:

- Historical odds snapshots from June 2020.
- Snapshots every 10 minutes historically, and every 5 minutes from September 2022.
- Historical World Cup 1X2 odds are documented as available from April 2022.

Important caveat: historical odds are paid-plan-only and cost more. The provider documents historical odds cost as `10 * markets * regions`.

Matchmind use:

- Closing line value after the user logs a bet.
- Line movement charts.
- Backtesting simple signal rules.
- "You got a better/worse number than the close" feedback in the bet tracker.

This is not needed for first integration.

## Bookmaker Regions

Regions available in the docs:

```text
us, us2, uk, eu, fr, se, au
```

Recommended Matchmind default:

- Start with `eu` because the project is Spain/Europe-oriented and includes Pinnacle, Betfair Exchange EU, Betsson, Marathonbet, Matchbook, Unibet variants, William Hill, Winamax, and others.
- Consider `uk` as a second region if quota allows, because UK soccer coverage is strong.
- Avoid mixing too many regions in v1. It increases quota cost and can make the user-facing "best price" less relevant.

Bookmaker selection can also be explicit via `bookmakers=...`. Up to 10 bookmakers count like one region. This is useful if we want a curated comparison set such as:

```text
pinnacle,betfair_ex_eu,matchbook,betsson,williamhill,unibet_fr,winamax_fr
```

## Derived Matchmind Signals

These are the signals we should compute ourselves from raw odds.

### Implied Probability

For decimal odds:

```text
raw_implied_probability = 1 / decimal_price
```

Use this for explaining the user's exact entered odds.

### No-Vig Probability

For each bookmaker and market line:

```text
raw_probabilities = [1 / price for each outcome]
overround = sum(raw_probabilities)
no_vig_probability = raw_probability / overround
```

Use this as a cleaner estimate of what that bookmaker is saying after removing margin.

### Consensus Probability

Recommended v1 method:

- Compute no-vig probability per bookmaker for the same event, market, outcome, and point.
- Use median as the primary consensus.
- Store min, max, mean, and bookmaker count for transparency.
- Prefer median over mean because outlier books and stale lines are common.

### Best Price

For each event/market/outcome:

- Track highest decimal price.
- Track bookmaker key/title.
- Track `last_update`.
- Compare user-entered odds against best price and consensus.

### Bookmaker Disagreement

Signal when:

- Best price is meaningfully above median price.
- No-vig probabilities have wide dispersion.
- Sharp/exchange book differs from soft-book consensus.

This can power "shop around" guidance without telling the user to place a bet.

### Bookmaker vs Polymarket Divergence

Compatible v1 markets:

- World Cup winner from `soccer_fifa_world_cup_winner` vs Polymarket `tournament_outright`.

Possible later markets if both sides have coverage:

- Group winner.
- Reach stage / advance markets.

Avoid comparing Polymarket to match-level h2h unless Polymarket has active fixture-level World Cup markets with enough liquidity. Current project decision says it does not.

## Proposed Data Flow

Implemented data flow keeps the existing provider pattern:

```text
The Odds API
-> internal refresh/discovery endpoint
-> Supabase odds tables
-> in-memory TTL cache
-> /chat, /odds/matches, /odds/analyze, Match Radar
```

Chat should never call The Odds API directly.

## Implemented Tables

### `bookmaker_events`

Current provider mapping for events. This table must include both match events and the separate outright event from `soccer_fifa_world_cup_winner`.

Main fields:

- `id uuid primary key`
- `odds_api_event_id text unique not null`
- `api_football_fixture_id bigint null`
- `sport_key text not null`
- `sport_title text`
- `home_team text`
- `away_team text`
- `commence_time timestamptz`
- `matchmind_match_key text`
- `raw_payload jsonb`
- `last_fetched_at timestamptz`
- `created_at timestamptz default now()`

### `bookmaker_odds`

Latest normalized odds by event/bookmaker/market/outcome/point.

Main fields:

- `id uuid primary key`
- `odds_api_event_id text not null`
- `bookmaker_key text not null`
- `bookmaker_title text not null`
- `market_key text not null`
- `line_key text not null`
- `outcome_name text not null`
- `outcome_team text null`
- `price numeric(10, 4) not null`
- `point numeric(10, 3) null`
- `odds_format text not null default 'decimal'`
- `bookmaker_last_update timestamptz`
- `fetched_at timestamptz not null`
- `raw_payload jsonb`
- unique constraint on `odds_api_event_id, bookmaker_key, market_key, outcome_name, line_key`

`line_key` exists because Postgres unique constraints do not treat `null` values as equal. Without it, `h2h` and `outrights` rows with `point = null` can duplicate across refreshes. For regular no-line markets, `line_key` is the market key, for example `h2h`. For line markets, it includes the signed point, for example `totals:2.5` or `spreads:-1.5`. Spread consensus still uses an unsigned pricing key internally when calculating no-vig probabilities across opposing sides.

### `bookmaker_odds_snapshots`

Historical observations for line movement and closing line value.

Main fields:

- `id uuid primary key`
- same identifying fields as `bookmaker_odds`
- `price numeric(10, 4) not null`
- `point numeric(10, 3) null`
- `bookmaker_last_update timestamptz`
- `fetched_at timestamptz not null`
- `raw_payload jsonb`

### `bookmaker_market_consensus`

Precomputed consensus rows for fast chat/UI reads.

Main fields:

- `id uuid primary key`
- `odds_api_event_id text not null`
- `market_key text not null`
- `line_key text not null`
- `outcome_name text not null`
- `point numeric(10, 3) null`
- `best_price numeric(10, 4)`
- `best_bookmaker_key text`
- `best_bookmaker_title text`
- `median_price numeric(10, 4)`
- `mean_price numeric(10, 4)`
- `min_price numeric(10, 4)`
- `max_price numeric(10, 4)`
- `no_vig_probability numeric(8, 6)`
- `bookmaker_count integer`
- `stale_bookmaker_count integer`
- `fetched_at timestamptz not null`

## Implemented Backend Endpoints

Internal:

- `POST /odds/refresh/events`: refresh World Cup event ids and map them to fixtures.
- `POST /odds/refresh`: refresh featured markets for configured regions/books.
- `POST /odds/seed-from-discovery`: seed match and outright bookmaker data from `ODDS_API_DISCOVERY_PATH`.

Planned later:

- `POST /odds/refresh-event/{event_id}`: refresh additional markets for one event near kickoff.

Public/product:

- `GET /odds/matches`: compact odds context for feed cards.
- `POST /odds/analyze`: compare user odds against cache and return value summary.

Planned later:

- `GET /odds/matches/{event_id}`: full current odds by market/bookmaker.

Chat integration:

- `build_bookmaker_context_for_chat(message, parsed_bet, match_context)` reads cached bookmaker consensus.
- Chat injects only compact fields into GPT context: event, market, user odds, implied probability, consensus probability, best price, best bookmaker title, freshness, and caveats.
- In `/chat`, bookmaker context is best-effort. If the cache read fails or no relevant event/market can be matched, the coach still answers from parsed bet facts and any other available context.

## V1 Rollout

1. Add configuration:

```text
ODDS_API_KEY=
ODDS_API_BASE_URL=https://api.the-odds-api.com
ODDS_API_REGIONS=eu
ODDS_API_BOOKMAKERS=
ODDS_API_MARKETS=h2h,spreads,totals
ODDS_API_OUTRIGHT_MARKETS=outrights
ODDS_API_ODDS_FORMAT=decimal
ODDS_API_CACHE_TTL_SECONDS=600
ODDS_API_DISCOVERY_PATH=tmp/odds_api_world_cup_discovery.json
ODDS_SNAPSHOT_RETENTION_DAYS=30
```

2. Build a one-off explorer script:

```text
scripts/explore_odds_api_world_cup.py
```

The script should call sports, events, featured odds, and event markets for a small sample. It should write `tmp/odds_api_world_cup_discovery.json`, including provider usage headers.

3. Implement cache tables and refresh endpoint for featured markets only. Done.

4. Compute consensus rows during refresh. Done.

5. Wire Match Radar / Daily Feed to show 1X2 consensus and best prices. Done.

6. Wire chat to use cached odds for match-specific bets. Done.

7. Add Odds Analyzer using cached consensus. Backend endpoint exists through `POST /odds/analyze`; dedicated frontend flow is not built yet.

8. Add tournament outright comparison with Polymarket once `soccer_fifa_world_cup_winner` is verified live. Not implemented yet.

## Open Questions

- Which plan will Matchmind use during beta? This determines whether historical odds and high-frequency refreshes are viable.
- Which regions/books match the target user geography best? Defaulting to `eu` is sensible, but Spain-specific legal UX may affect which bookmaker names we display.
- Does World Cup 2026 have reliable coverage for additional markets such as BTTS, cards, corners, and player props? This needs live discovery closer to kickoff.
- Do we want to display bookmaker names only, or deep links too? Deep links are technically available, but product/legal review should come first.
- How often should refresh run during matchdays? A practical start is every 30 minutes pre-match, every 5 minutes in the final hour before kickoff, and no live in-play betting surface in v1.

## Product Takeaway

The Odds API should become Matchmind's primary source of bookmaker reality. The first valuable version is not exotic props; it is reliable 1X2, handicap, totals, best-price, and no-vig consensus for every World Cup match. That unlocks honest coaching language:

```text
Your odds imply 41.7%. The bookmaker consensus is closer to 36%.
The best available market price is 2.55, so 2.40 is not attractive.
I like the football angle, but the number is thin.
```

That is the missing layer between "football opinion" and "is this bet actually value?"

## Live Discovery Run - 2026-05-10

Local explorer:

```text
scripts/explore_odds_api_world_cup.py
```

Report:

```text
tmp/odds_api_world_cup_discovery.json
```

Run configuration:

- Base URL: `https://api.the-odds-api.com`
- Sports: `soccer_fifa_world_cup`, `soccer_fifa_world_cup_winner`
- Region: `eu`
- Featured markets: `h2h,spreads,totals`
- Event-specific sample markets: `btts,draw_no_bet,double_chance,h2h_3_way,alternate_totals_corners,alternate_totals_cards`
- Sample size: 3 event market checks, 2 event odds checks

Observed coverage:

- API reachability: 9 successful requests, 0 failed.
- Quota after run: 474 remaining, 26 used, last request cost 3.
- World Cup match sport active: yes.
- World Cup winner sport active: yes.
- Match events found: 49.
- Featured odds events found: 49.
- Featured normalized odds rows: 3,366.
- Tournament outright rows: 139.

Featured market rows:

```text
h2h: 2058
spreads: 328
totals: 860
h2h_lay: 120
```

Outright rows:

```text
outrights: 102
outrights_lay: 37
```

Additional sampled markets seen:

```text
h2h
h2h_3_way
alternate_spreads
alternate_totals
spreads
totals
h2h_3_way_lay
h2h_lay
btts
double_chance
h2h_h1
spreads_h1
totals_h1
```

Bookmakers seen in the EU run:

```text
marathonbet, pinnacle, betfair_ex_eu, everygame, unibet_fr,
coolbet, sport888, williamhill, unibet_nl, leovegas_se,
unibet_se, betonlineag, pmu_fr, mybookieag, winamax_fr,
betclic_fr, betsson, gtbets, nordicbet, onexbet, codere_it,
tipico_de, winamax_de
```

Example event:

```text
Mexico vs South Africa
commence_time: 2026-06-11T19:00:00Z
odds_api_event_id: 80d82d1113934bfbea4ce8daf37a2433
```

Example derived consensus fields now generated:

```text
event_id
market_key
outcome_name
point
bookmaker_count
best_price
best_bookmaker_key
best_bookmaker_title
median_price
min_price
max_price
median_raw_implied_probability
median_no_vig_probability
```

Discovery verdict:

```text
integrate featured match odds
```

## Implementation Update - 2026-05-10

The first Matchmind integration is now implemented:

- Service: `apps/api/app/services/odds_api.py`
- Router: `apps/api/app/routers/odds.py`
- Chat wiring: `apps/api/app/routers/chat.py` and `apps/api/app/services/gpt.py`
- Tests: `apps/api/tests/test_odds_api.py`
- Frontend API client: `apps/web/lib/api.ts`
- Frontend surface: `apps/web/components/betcoach/DailyFeed.tsx`

Implemented surfaces:

- `GET /odds/matches` powers Match Radar bookmaker panels.
- `POST /odds/analyze` returns deterministic comparison of user-entered odds against cached consensus.
- `POST /odds/seed-from-discovery` seeds Supabase from the local discovery JSON.
- `POST /odds/refresh/events` refreshes World Cup event ids.
- `POST /odds/refresh` refreshes featured match odds and tournament outrights.

Match Radar now shows:

- 1X2 best prices for home, draw, and away.
- The bookmaker-consensus favorite, highlighted visually. This highlight means "most likely by no-vig consensus," not "recommended bet."
- Best price, no-vig/fair probability, bookmaker count, and odds freshness.
- Expandable "More markets" section with "Goals over/under" and "Goal handicap."

Known caveats:

- Additional event-specific markets such as BTTS, cards, corners, and player props are not yet wired into the product.
- The dedicated Odds Analyzer UI is not built yet; only the backend endpoint exists.
- Bookmaker-vs-Polymarket divergence is not implemented yet.
