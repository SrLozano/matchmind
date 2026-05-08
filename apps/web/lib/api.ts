const DEFAULT_API_URL = "http://localhost:8000"
const DEFAULT_DEV_USER_ID = "a87d09e8-7e10-46b8-9927-c9500c9559cf"

export type ChatResponse = {
  response: string
  confidence_score: number
  verdict: string | null
  implied_probability: number | null
  stake_posture: string | null
  daily_chats_remaining: number | null
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

function getApiUrl() {
  return process.env.NEXT_PUBLIC_API_URL ?? DEFAULT_API_URL
}

function getDevUserId() {
  return process.env.NEXT_PUBLIC_DEV_USER_ID ?? DEFAULT_DEV_USER_ID
}

async function readApiError(response: Response, fallback: string) {
  try {
    const errorBody = (await response.json()) as { detail?: string }
    return errorBody.detail ?? fallback
  } catch {
    return fallback
  }
}

export async function sendChatMessage(message: string, preferredLanguage?: "en" | "es"): Promise<ChatResponse> {
  const apiUrl = getApiUrl()
  const userId = getDevUserId()

  const response = await fetch(`${apiUrl}/chat`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      user_id: userId,
      message,
      preferred_language: preferredLanguage,
    }),
  })

  if (!response.ok) {
    throw new Error(await readApiError(response, "Unable to reach the Matchmind coach. Try again in a moment."))
  }

  return response.json()
}

export async function getWorldCupFixtures(): Promise<WorldCupFixturesResponse> {
  const response = await fetch(`${getApiUrl()}/world-cup/fixtures`)

  if (!response.ok) {
    throw new Error(await readApiError(response, "Unable to load the World Cup match radar. Try again in a moment."))
  }

  return response.json()
}

export async function getTrackedBets(): Promise<BetListResponse> {
  const response = await fetch(`${getApiUrl()}/bets?user_id=${getDevUserId()}`)

  if (!response.ok) {
    throw new Error(await readApiError(response, "Unable to load your bet tracker. Try again in a moment."))
  }

  return response.json()
}

export async function createTrackedBet(payload: CreateBetPayload): Promise<TrackedBet> {
  const response = await fetch(`${getApiUrl()}/bets`, {
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
  const response = await fetch(`${getApiUrl()}/bets/${betId}`, {
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
  const response = await fetch(`${getApiUrl()}/bets/${betId}?user_id=${getDevUserId()}`, {
    method: "DELETE",
  })

  if (!response.ok) {
    throw new Error(await readApiError(response, "Unable to delete this bet. Try again in a moment."))
  }
}
