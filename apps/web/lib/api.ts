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

function getApiUrl() {
  return process.env.NEXT_PUBLIC_API_URL ?? DEFAULT_API_URL
}

export async function sendChatMessage(message: string, preferredLanguage?: "en" | "es"): Promise<ChatResponse> {
  const apiUrl = getApiUrl()
  const userId = process.env.NEXT_PUBLIC_DEV_USER_ID ?? DEFAULT_DEV_USER_ID

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
    let detail = "Unable to reach the Matchmind coach. Try again in a moment."

    try {
      const errorBody = (await response.json()) as { detail?: string }
      detail = errorBody.detail ?? detail
    } catch {
      // Keep the generic fallback when the API returns a non-JSON error.
    }

    throw new Error(detail)
  }

  return response.json()
}

export async function getWorldCupFixtures(): Promise<WorldCupFixturesResponse> {
  const response = await fetch(`${getApiUrl()}/world-cup/fixtures`)

  if (!response.ok) {
    let detail = "Unable to load the World Cup match radar. Try again in a moment."

    try {
      const errorBody = (await response.json()) as { detail?: string }
      detail = errorBody.detail ?? detail
    } catch {
      // Keep the generic fallback when the API returns a non-JSON error.
    }

    throw new Error(detail)
  }

  return response.json()
}
