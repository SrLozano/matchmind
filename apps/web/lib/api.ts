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

export async function sendChatMessage(message: string): Promise<ChatResponse> {
  const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? DEFAULT_API_URL
  const userId = process.env.NEXT_PUBLIC_DEV_USER_ID ?? DEFAULT_DEV_USER_ID

  const response = await fetch(`${apiUrl}/chat`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      user_id: userId,
      message,
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
