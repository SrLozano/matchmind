const DEFAULT_API_URL = "http://localhost:8000"
const DEFAULT_DEV_USER_ID = "a87d09e8-7e10-46b8-9927-c9500c9559cf"

let authTokenProvider: (() => Promise<string | null>) | null = null

export function setAuthTokenProvider(provider: (() => Promise<string | null>) | null) {
  authTokenProvider = provider
}

export type ChatResponse = {
  conversation_id: string | null
  response: string
  confidence_score: number
  verdict: string | null
  implied_probability: number | null
  stake_posture: string | null
  market_signal: ChatMarketSignal | null
  daily_chats_remaining: number | null
}

export type ChatMarketSignal = {
  matched: boolean
  market_type: string | null
  team: string | null
  teams: string[]
  group: string | null
  question: string | null
  implied_probability: number | null
  liquidity: number | null
  liquidity_label: string | null
  volume: number | null
  spread: number | null
  signal_quality_score: number | null
  match_confidence: number | null
  last_fetched_at: string | null
  note: string | null
}

export type ConversationMessage = {
  role: "user" | "assistant"
  content: string
  confidence_score: number | null
  created_at: string | null
}

export type ConversationSummary = {
  id: string
  user_id: string
  title: string
  last_message_preview: string | null
  message_count: number
  created_at: string | null
  updated_at: string | null
}

export type ConversationListResponse = {
  conversations: ConversationSummary[]
  count: number
}

export type ConversationDetailResponse = ConversationSummary & {
  messages: ConversationMessage[]
}

export type MarketSignal = {
  matched: boolean
  market_type: string | null
  team: string | null
  teams: string[]
  group: string | null
  question: string | null
  slug: string | null
  yes_price: number | null
  implied_probability: number | null
  liquidity: number | null
  volume: number | null
  best_bid: number | null
  best_ask: number | null
  midpoint: number | null
  spread: number | null
  match_confidence: number | null
  signal_quality_score: number | null
  liquidity_label: string | null
  active: boolean | null
  closed: boolean | null
  end_date: string | null
  last_fetched_at: string | null
}

export type MarketSignalsResponse = {
  signals: MarketSignal[]
  count: number
}

export type UserPlan = "free" | "premium"

export type CurrentUser = {
  id: string
  email: string | null
  plan: UserPlan
  daily_chat_count: number
  daily_chat_count_limit: number
  daily_chats_remaining: number | null
  last_reset_date: string | null
  created_at: string | null
}

export type WorldCupFixture = {
  id: number | string | null
  home_team: string | null
  away_team: string | null
  match: string
  kickoff_time: string | null
  stage: string | null
  status: string | null
  score: string | null
  venue: string | null
  last_fetched_at: string | null
  freshness_minutes: number | null
  access?: "free" | "locked"
  teaser?: string | null
  pick?: string | null
  confidence_score?: number | null
  edge?: number | null
  coach_summary?: string | null
}

export type WorldCupFixturesResponse = {
  matches: WorldCupFixture[]
  count: number
  api_football_usage?: {
    fixture_requests: number
    last_request_at: string | null
    last_error: string | null
  }
}

export type OddsConsensusRow = {
  market_key: string | null
  outcome_name: string | null
  point: number | null
  best_price: number | null
  best_bookmaker_title: string | null
  median_price: number | null
  no_vig_probability: number | null
  bookmaker_count: number
}

export type OddsMatch = {
  odds_api_event_id: string
  sport_key: string | null
  home_team: string | null
  away_team: string | null
  match: string
  commence_time: string | null
  last_fetched_at: string | null
  h2h: OddsConsensusRow[]
  featured_markets: {
    spreads?: OddsConsensusRow[]
    totals?: OddsConsensusRow[]
  }
}

export type OddsMatchesResponse = {
  matches: OddsMatch[]
  count: number
}

export type BetOutcome = "win" | "loss" | "pending"

export type TrackedBet = {
  id: string
  user_id: string
  match: string
  amount: number
  odds: number
  outcome: BetOutcome
  profit_loss: number
  created_at: string
}

export type BetSummary = {
  total_bets: number
  pending_bets: number
  wins: number
  losses: number
  win_rate: number
  total_staked: number
  profit_loss: number
  roi: number
}

export type BetListResponse = {
  bets: TrackedBet[]
  summary: BetSummary
}

export type CreateBetPayload = {
  match: string
  amount: number
  odds: number
  outcome?: BetOutcome
}

export type CheckoutSessionResponse = {
  url: string
}

function getApiUrl() {
  return process.env.NEXT_PUBLIC_API_URL || DEFAULT_API_URL
}

function getDevUserId() {
  return process.env.NEXT_PUBLIC_DEV_USER_ID || DEFAULT_DEV_USER_ID
}

async function readApiError(response: Response, fallback: string) {
  try {
    const errorBody = (await response.json()) as { detail?: string }
    return errorBody.detail ?? fallback
  } catch {
    return fallback
  }
}

async function authHeaders(extra?: HeadersInit): Promise<HeadersInit> {
  const token = authTokenProvider ? await authTokenProvider() : null
  return {
    ...(extra ?? {}),
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  }
}

async function apiFetch(input: string, init: RequestInit = {}) {
  return fetch(input, {
    ...init,
    headers: await authHeaders(init.headers),
  })
}

export async function sendChatMessage(
  message: string,
  preferredLanguage?: "en" | "es",
  conversationId?: string | null
): Promise<ChatResponse> {
  const apiUrl = getApiUrl()
  const userId = getDevUserId()

  const response = await apiFetch(`${apiUrl}/chat`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      user_id: userId,
      message,
      preferred_language: preferredLanguage,
      conversation_id: conversationId,
    }),
  })

  if (!response.ok) {
    throw new Error(await readApiError(response, "Unable to reach the Matchmind coach. Try again in a moment."))
  }

  return normalizeChatResponse((await response.json()) as ChatResponse)
}

function normalizeChatResponse(payload: ChatResponse): ChatResponse {
  return {
    ...payload,
    response: unwrapNestedResponse(payload.response),
  }
}

export async function getConversations(limit = 20): Promise<ConversationListResponse> {
  const apiUrl = getApiUrl()
  const userId = getDevUserId()
  const response = await apiFetch(`${apiUrl}/conversations?user_id=${userId}&limit=${limit}`)

  if (!response.ok) {
    throw new Error(await readApiError(response, "Unable to load conversation history."))
  }

  return (await response.json()) as ConversationListResponse
}

export async function getConversation(conversationId: string): Promise<ConversationDetailResponse> {
  const apiUrl = getApiUrl()
  const userId = getDevUserId()
  const response = await apiFetch(`${apiUrl}/conversations/${conversationId}?user_id=${userId}`)

  if (!response.ok) {
    throw new Error(await readApiError(response, "Unable to load this conversation."))
  }

  return normalizeConversationDetail((await response.json()) as ConversationDetailResponse)
}

function normalizeConversationDetail(payload: ConversationDetailResponse): ConversationDetailResponse {
  return {
    ...payload,
    messages: payload.messages.map((message) => ({
      ...message,
      content: unwrapNestedResponse(message.content),
    })),
  }
}

function unwrapNestedResponse(value: string): string {
  const text = value.trim()
  if (!text.startsWith("{")) return value

  try {
    const parsed = JSON.parse(text) as { response?: unknown }
    if (typeof parsed.response === "string") {
      return unwrapNestedResponse(parsed.response)
    }
  } catch {
    return value
  }

  return value
}

export async function getWorldCupFixtures(): Promise<WorldCupFixturesResponse> {
  const response = await fetch(`${getApiUrl()}/world-cup/fixtures`)

  if (!response.ok) {
    throw new Error(await readApiError(response, "Unable to load the World Cup match radar. Try again in a moment."))
  }

  return response.json()
}

export async function getOddsMatches({ limit = 50 }: { limit?: number } = {}): Promise<OddsMatchesResponse> {
  const params = new URLSearchParams({ limit: limit.toString() })
  const response = await fetch(`${getApiUrl()}/odds/matches?${params.toString()}`)

  if (!response.ok) {
    throw new Error(await readApiError(response, "Unable to load bookmaker odds. Try again in a moment."))
  }

  return response.json()
}

export async function getMarketSignals({ limit = 16 }: { limit?: number } = {}): Promise<MarketSignalsResponse> {
  const params = new URLSearchParams({ limit: limit.toString() })
  const response = await fetch(`${getApiUrl()}/polymarket/signals?${params.toString()}`)

  if (!response.ok) {
    throw new Error(await readApiError(response, "Unable to load market signals. Try again in a moment."))
  }

  return response.json()
}

export async function getCurrentUser(): Promise<CurrentUser> {
  const response = await apiFetch(`${getApiUrl()}/users/me?user_id=${getDevUserId()}`)

  if (!response.ok) {
    throw new Error(await readApiError(response, "Unable to load your profile. Try again in a moment."))
  }

  return response.json()
}

export async function getTrackedBets(): Promise<BetListResponse> {
  const response = await apiFetch(`${getApiUrl()}/bets?user_id=${getDevUserId()}`)

  if (!response.ok) {
    throw new Error(await readApiError(response, "Unable to load your bet tracker. Try again in a moment."))
  }

  return response.json()
}

export async function createTrackedBet(payload: CreateBetPayload): Promise<TrackedBet> {
  const response = await apiFetch(`${getApiUrl()}/bets`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      user_id: getDevUserId(),
      ...payload,
    }),
  })

  if (!response.ok) {
    throw new Error(await readApiError(response, "Unable to log this bet. Try again in a moment."))
  }

  return response.json()
}

export async function updateTrackedBetOutcome(betId: string, outcome: BetOutcome): Promise<TrackedBet> {
  const response = await apiFetch(`${getApiUrl()}/bets/${betId}`, {
    method: "PATCH",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      user_id: getDevUserId(),
      outcome,
    }),
  })

  if (!response.ok) {
    throw new Error(await readApiError(response, "Unable to update this bet. Try again in a moment."))
  }

  return response.json()
}

export async function deleteTrackedBet(betId: string): Promise<void> {
  const response = await apiFetch(`${getApiUrl()}/bets/${betId}?user_id=${getDevUserId()}`, {
    method: "DELETE",
  })

  if (!response.ok) {
    throw new Error(await readApiError(response, "Unable to delete this bet. Try again in a moment."))
  }
}

export async function createTournamentPassCheckoutSession(): Promise<CheckoutSessionResponse> {
  const response = await apiFetch(`${getApiUrl()}/payments/create-checkout-session`, {
    method: "POST",
  })

  if (!response.ok) {
    throw new Error(await readApiError(response, "Unable to start checkout. Try again in a moment."))
  }

  return response.json()
}
