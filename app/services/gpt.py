import json
import re

from openai import AsyncOpenAI

from app.config import get_settings
from app.models.chat import AIChatResult

SYSTEM_PROMPT = """
You are Matchmind, an AI-powered football betting coach focused on the 2026 FIFA World Cup.
Your tone is direct, sharp, and grounded, like a knowledgeable friend who gives honest betting takes.
You never place bets or pretend to guarantee outcomes.
When answering:
- Explain the football betting angle clearly.
- Reference odds, implied probability, and risk when useful.
- Be honest when the edge is weak or unclear.
- End every answer with a confidence score out of 10.
- Return valid JSON with keys "response" and "confidence_score".
""".strip()


def _extract_json(content: str) -> AIChatResult:
    try:
        payload = json.loads(content)
    except json.JSONDecodeError:
        score_match = re.search(r"confidence\s*score\s*[:\-]?\s*(\d{1,2})", content, re.IGNORECASE)
        score = int(score_match.group(1)) if score_match else 5
        return AIChatResult(
            response=content.strip(),
            confidence_score=max(1, min(score, 10)),
        )

    return AIChatResult(
        response=str(payload.get("response", "")).strip(),
        confidence_score=max(1, min(int(payload.get("confidence_score", 5)), 10)),
    )


async def generate_chat_reply(message: str) -> AIChatResult:
    settings = get_settings()
    client = AsyncOpenAI(api_key=settings.openai_api_key)
    completion = await client.chat.completions.create(
        model=settings.openai_model,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": message},
        ],
        temperature=0.7,
    )
    content = completion.choices[0].message.content or "{}"
    return _extract_json(content)
