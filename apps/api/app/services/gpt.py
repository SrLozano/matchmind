import json
import re
from typing import Any

from openai import AsyncOpenAI

from app.config import get_settings
from app.models.chat import AIChatResult
from app.services.bet_parser import ParsedBet, parse_bet_message
from app.services.api_football import format_match_context_block
from app.services.odds_api import format_bookmaker_context_block
from app.services.polymarket import format_polymarket_context_block

SYSTEM_PROMPT = """
You are Matchmind, an AI-powered football betting coach focused on the 2026 FIFA World Cup.
You analyze bets only. You never place bets, give financial advice, guarantee outcomes, or use certainty language like "safe bet", "lock", or "guaranteed".

Voice:
- Direct, concise, opinionated, and practical.
- Sound like a sharp, honest betting friend, not a generic chatbot.
- Be willing to say "do not take this bet" when the edge is weak.
- Treat broad beginner questions as a coaching opportunity, not a dead end.
- Reply in the user's detected language. Use Spanish when detected_language is "es"; use English otherwise.
- If detected_language is "es", every user-facing sentence and every visible label in response must be Spanish.
- Keep only JSON metadata enum values in English. The visible response text must still be Spanish for Spanish users.

Use the provided parsed_bet facts as deterministic context. Do not contradict the supplied odds or implied probability.
Use conversation_memory to understand follow-up messages. If the current message is incomplete but clearly refers to the previous bet, carry forward the prior bet context and explain that you are treating it as the same bet with the updated detail. Do not carry forward old context when the user clearly switches teams, market, or topic.
If live_data_available is false, clearly say live market/team data is missing when relevant. Do not claim real-time odds, injuries, lineups, API-Football data, bookmaker data, or prediction-market data unless it is explicitly provided.
If match_context is present, use it only when relevant to the user's bet. It contains cached World Cup fixture context from API-Football, not odds or prediction-market data.
If polymarket_context is present, use it only as crowd probability or market signal for supported long-term World Cup markets. Never mention "Polymarket" in the user-facing response. Never call it truth, a sure bet, or an instruction to bet. If it says matched=false, mention that no useful market signal was found only when relevant.
If polymarket_context is present but match_context is absent, do not say all live market data is missing. Say only that team/form/fixture data, injuries, lineups, or bookmaker comparison are missing when relevant.
If bookmaker_context is present, use it as cached bookmaker consensus only. It is not a guarantee, not a true probability, and not permission to place a bet. Compare the user's price against consensus and best cached price when supplied.
Separate two ideas clearly: price quality versus bet value. A price can be well bought because it is close to the best cached bookmaker price, while still having only fair or small edge versus the no-vig consensus. Do not make well-bought fair prices sound like bad user decisions; explain them as acceptable market prices, small-edge spots, or watchlist entries depending on the data.
When best cached price and consensus probability are provided, give a practical price ladder when relevant: the current price, the approximate fair price from consensus, the price where it becomes less attractive, and the price where it starts to look more interesting. Keep this concise.
If bookmaker_context is BOOKMAKER DISCOVERY CONTEXT, the user is asking for help finding where to start. Use the listed in-app matches and prices to create a small guided shortlist or decision path. Do not ask the user to leave the app to find fixtures or odds. Do not call any option good value unless the context gives enough price/probability comparison to support it; otherwise call them watchlist/price-check candidates.
Do not claim to have bookmaker odds, lineups, injuries, events, statistics, API-Football predictions, prediction-market probabilities, or broader team form unless those fields are explicitly present.
If only fixture context is available, say that naturally. Continue to calculate implied probability from user-provided decimal odds when available.

The visible response should feel like a sharp friend answering in chat, not a reusable report template.
- Start with the bottom line in plain language.
- Use 2-5 short paragraphs or bullets, whichever feels more natural for the user's question.
- Keep it concise, usually 90-170 words.
- Mention the user's odds and implied probability when odds are supplied.
- Mention bookmaker consensus, best cached price, fixture context, or market-signal probability only when those fields are explicitly provided.
- Include the confidence score naturally at the end, but avoid making every answer look identical.
- Vary wording across answers. Do not always use the same section labels or the same order.
- For vague inputs, ask one useful follow-up question and give a useful preliminary plan.
- Never recommend a large or aggressive stake. Use stake language as posture, not instruction.

Behavior rules:
- If no odds are provided, ask for the odds but still give a preliminary football opinion if teams or market are clear.
- If no teams or bet target are detected but the user asks for recommendations, a budget plan, what to bet, a shortlist, or says they have money to bet, do not answer with only "I need teams/odds".
  First use any BOOKMAKER DISCOVERY CONTEXT or market-signal context already provided by Matchmind. Give 2-4 in-app options to inspect, explain why each is only a candidate or a pass, and ask the user to choose a risk profile or tap one option for a deeper verdict.
  If no in-app context is available, give a practical starter plan: say you would not deploy the whole budget blindly, explain what inputs create value, suggest 2-3 safe in-app next actions such as Feed, Market Signals, risk profile, or shortlist mode, and ask one concise follow-up question.
  You may describe categories to consider or avoid, but do not invent specific picks without price/data.
  Use verdict NOT ENOUGH INFO, stake_posture avoid or very small, and confidence 3-5 because no specific bet has been priced yet.
- If no teams or bet target are detected and the user is not asking for discovery/recommendations, use NOT ENOUGH INFO and ask one concise follow-up question.
- If the message is vague, do not invent specifics.
- Do not encourage chasing losses or staking because of emotion, loyalty, narratives, or gut feeling.
- Include responsible-betting language naturally and briefly.

Return valid JSON with keys:
"response", "confidence_score", "verdict", "implied_probability", "stake_posture".
For JSON metadata, always use English enum values:
- verdict: GOOD VALUE, FAIR, RISKY, AVOID, or NOT ENOUGH INFO
- stake_posture: avoid, very small, small, or medium
- confidence_score must be a number from 1 to 10.
- implied_probability must be a number from 0 to 1, or null when not calculable.
""".strip()


VERDICTS = {"GOOD VALUE", "FAIR", "RISKY", "AVOID", "NOT ENOUGH INFO"}
STAKE_POSTURES = {"avoid", "very small", "small", "medium"}
CHAT_RESPONSE_JSON_SCHEMA = {
    "type": "json_schema",
    "json_schema": {
        "name": "matchmind_chat_reply",
        "strict": True,
        "schema": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "response": {
                    "type": "string",
                    "description": "User-facing chat answer in the requested language.",
                },
                "confidence_score": {
                    "type": "number",
                    "minimum": 1,
                    "maximum": 10,
                },
                "verdict": {
                    "type": "string",
                    "enum": ["GOOD VALUE", "FAIR", "RISKY", "AVOID", "NOT ENOUGH INFO"],
                },
                "implied_probability": {
                    "anyOf": [
                        {"type": "number", "minimum": 0, "maximum": 1},
                        {"type": "null"},
                    ],
                },
                "stake_posture": {
                    "type": "string",
                    "enum": ["avoid", "very small", "small", "medium"],
                },
            },
            "required": [
                "response",
                "confidence_score",
                "verdict",
                "implied_probability",
                "stake_posture",
            ],
        },
    },
}
SPANISH_VERDICT_MAP = {
    "BUEN VALOR": "GOOD VALUE",
    "VALOR": "GOOD VALUE",
    "JUSTA": "FAIR",
    "JUSTO": "FAIR",
    "NEUTRAL": "FAIR",
    "JUSTA / NEUTRAL": "FAIR",
    "ARRIESGADA": "RISKY",
    "ARRIESGADO": "RISKY",
    "EVITAR": "AVOID",
    "NO HAY INFO SUFICIENTE": "NOT ENOUGH INFO",
    "INFORMACION INSUFICIENTE": "NOT ENOUGH INFO",
    "INFORMACIÓN INSUFICIENTE": "NOT ENOUGH INFO",
}
SPANISH_STAKE_POSTURE_MAP = {
    "evitar": "avoid",
    "muy pequeño": "very small",
    "muy pequena": "very small",
    "muy pequeña": "very small",
    "pequeño": "small",
    "pequeno": "small",
    "pequena": "small",
    "pequeña": "small",
    "medio": "medium",
    "media": "medium",
}
SPANISH_VISIBLE_VERDICT_MAP = {
    "GOOD VALUE": "BUEN VALOR",
    "FAIR": "JUSTA / NEUTRAL",
    "RISKY": "ARRIESGADA",
    "AVOID": "EVITAR",
    "NOT ENOUGH INFO": "NO HAY INFO SUFICIENTE",
}
SPANISH_VISIBLE_STAKE_POSTURE_MAP = {
    "avoid": "evitar",
    "very small": "muy pequeño",
    "small": "pequeño",
    "medium": "medio",
}


def _extract_json(content: str) -> AIChatResult:
    try:
        payload = json.loads(content)
    except json.JSONDecodeError:
        score_match = re.search(
            r"(?:confidence(?:\s+score)?|confianza)\s*[:\-]?\s*(\d{1,2}(?:\.\d+)?)",
            content,
            re.IGNORECASE,
        )
        score = float(score_match.group(1)) if score_match else 5
        return AIChatResult(
            response=content.strip(),
            confidence_score=_clamp_score(score),
            verdict=_extract_verdict(content),
            stake_posture=_extract_stake_posture(content),
        )

    if not isinstance(payload, dict):
        return AIChatResult(
            response=str(payload or "").strip(),
            confidence_score=5.0,
        )

    response = _normalize_response_text(payload.get("response", ""))
    return AIChatResult(
        response=response,
        confidence_score=_clamp_score(payload.get("confidence_score", 5)),
        verdict=_normalize_verdict(payload.get("verdict")),
        implied_probability=_normalize_probability(payload.get("implied_probability")),
        stake_posture=_normalize_stake_posture(payload.get("stake_posture")),
    )


def _normalize_response_text(value: Any) -> str:
    if isinstance(value, dict):
        nested_response = value.get("response")
        if nested_response is not None:
            return _normalize_response_text(nested_response)
        return json.dumps(value, ensure_ascii=False)

    text = str(value or "").strip()
    if not text:
        return ""

    try:
        nested = json.loads(text)
    except json.JSONDecodeError:
        return text

    if isinstance(nested, dict) and "response" in nested:
        return _normalize_response_text(nested.get("response"))
    return text


def _clamp_score(value: Any) -> float:
    try:
        score = float(value)
    except (TypeError, ValueError):
        score = 5.0
    return max(1.0, min(score, 10.0))


def _normalize_probability(value: Any) -> float | None:
    if value is None:
        return None
    try:
        probability = float(value)
    except (TypeError, ValueError):
        return None
    if probability > 1:
        probability = probability / 100
    if 0 <= probability <= 1:
        return round(probability, 4)
    return None


def _normalize_verdict(value: Any) -> str | None:
    if value is None:
        return None
    verdict = str(value).strip().upper()
    verdict = SPANISH_VERDICT_MAP.get(verdict, verdict)
    return verdict if verdict in VERDICTS else None


def _normalize_stake_posture(value: Any) -> str | None:
    if value is None:
        return None
    posture = str(value).strip().lower()
    posture = SPANISH_STAKE_POSTURE_MAP.get(posture, posture)
    return posture if posture in STAKE_POSTURES else None


def _extract_verdict(content: str) -> str | None:
    match = re.search(r"(?:verdict|veredicto)\s*:\s*([A-ZÁÉÍÓÚÜÑ /]+)", content, re.IGNORECASE)
    return _normalize_verdict(match.group(1)) if match else None


def _extract_stake_posture(content: str) -> str | None:
    match = re.search(
        r"(?:stake posture|postura de stake|postura)\s*:\s*(avoid|very small|small|medium|evitar|muy pequeño|muy pequena|pequeño|pequena|medio)",
        content,
        re.IGNORECASE,
    )
    return _normalize_stake_posture(match.group(1)) if match else None


def _localize_visible_response_es(content: str) -> str:
    text = content
    label_replacements = {
        "Verdict:": "Veredicto:",
        "My take:": "Mi lectura:",
        "Odds check:": "Chequeo de cuota:",
        "Your odds:": "Tu cuota:",
        "Implied probability:": "Probabilidad implícita:",
        "Value judgment:": "Juicio de valor:",
        "Risk notes:": "Notas de riesgo:",
        "Stake posture:": "Postura de stake:",
        "Confidence:": "Confianza:",
    }
    for english, spanish in label_replacements.items():
        text = re.sub(rf"(?im)^({re.escape(english)})", spanish, text)
        text = re.sub(rf"(?im)^(-\s*)({re.escape(english)})", rf"\1{spanish}", text)

    for english, spanish in SPANISH_VISIBLE_VERDICT_MAP.items():
        text = re.sub(rf"(?im)^(Veredicto:\s*){re.escape(english)}\b", rf"\1{spanish}", text)

    for english, spanish in SPANISH_VISIBLE_STAKE_POSTURE_MAP.items():
        text = re.sub(
            rf"(?im)^(Postura de stake:\s*\n?){re.escape(english)}\b",
            rf"\1{spanish}",
            text,
        )

    cleanup_replacements = {
        "crowd probability": "probabilidad de mercado",
        "crowd signal": "señal de mercado",
        "mercado de crowd": "señal de mercado",
        "market signal": "señal de mercado",
    }
    for english, spanish in cleanup_replacements.items():
        text = re.sub(re.escape(english), spanish, text, flags=re.IGNORECASE)

    text = re.sub(r"\bel señal de mercado\b", "la señal de mercado", text, flags=re.IGNORECASE)
    text = re.sub(r"\bel probabilidad de mercado\b", "la probabilidad de mercado", text, flags=re.IGNORECASE)

    return text


def _build_user_context(
    message: str,
    parsed_bet: ParsedBet,
    match_context: dict[str, Any] | None = None,
    polymarket_context: dict[str, Any] | None = None,
    bookmaker_context: dict[str, Any] | None = None,
    conversation_memory: list[dict[str, Any]] | None = None,
) -> str:
    context = {
        "user_message": message,
        "parsed_bet": parsed_bet.model_dump(),
        "chat_intent": _classify_chat_intent(message, parsed_bet),
        "conversation_memory": _compact_conversation_memory(conversation_memory),
        "response_language": parsed_bet.detected_language,
        "language_instruction": (
            "Write all user-facing response text and section labels in Spanish. "
            "Only JSON metadata enum values may remain in English."
            if parsed_bet.detected_language == "es"
            else "Write all user-facing response text and section labels in English."
        ),
        "live_data_available": match_context is not None or polymarket_context is not None or bookmaker_context is not None,
        "match_context": format_match_context_block(match_context),
        "polymarket_context": format_polymarket_context_block(polymarket_context),
        "bookmaker_context": format_bookmaker_context_block(bookmaker_context),
        "live_data_note": "No bookmaker odds, API-Football stats, injuries, lineups, or market-signal probabilities were provided for this request."
        if match_context is None and polymarket_context is None and bookmaker_context is None
        else None,
    }
    return json.dumps(context, ensure_ascii=False)


def _classify_chat_intent(message: str, parsed_bet: ParsedBet) -> str:
    lowered = message.lower()
    recommendation_patterns = [
        r"\brecommend(?:ation|ations)?\b",
        r"\bsuggest(?:ion|ions)?\b",
        r"\bwhat\s+should\s+i\s+bet\b",
        r"\bwhere\s+should\s+i\s+put\b",
        r"\bgive\s+me\s+(?:some\s+)?(?:bets?|picks?|plays?)\b",
        r"\bshortlist\b",
        r"\bbuild\s+me\s+(?:a\s+)?(?:slip|ticket|shortlist)\b",
        r"\bi\s+have\s+(?:€|\$|£)?\s*\d+",
        r"\btengo\s+(?:€|\$|£)?\s*\d+",
        r"\brecomienda\b|\brecomendaciones\b",
        r"\bsugerencias\b|\bsugi[eé]reme\b",
        r"\bqu[eé]\s+apuesto\b",
        r"\bdame\s+(?:algunas\s+)?(?:apuestas|picks|jugadas)\b",
    ]
    if not parsed_bet.teams and any(re.search(pattern, lowered, re.IGNORECASE) for pattern in recommendation_patterns):
        return "discovery_or_bankroll_request"
    if parsed_bet.teams and parsed_bet.odds is not None:
        return "specific_bet_analysis"
    if parsed_bet.teams:
        return "bet_without_price"
    return "unclear"


def _compact_conversation_memory(messages: list[dict[str, Any]] | None, max_turns: int = 8) -> list[dict[str, str]]:
    if not messages:
        return []

    compact_messages: list[dict[str, str]] = []
    for message in messages[-max_turns:]:
        role = str(message.get("role") or "").strip().lower()
        if role not in {"user", "assistant"}:
            continue
        content = str(message.get("content") or "").strip()
        if not content:
            continue
        compact_messages.append(
            {
                "role": role,
                "content": content[:1200],
            }
        )
    return compact_messages


def _chat_response_format() -> dict[str, Any]:
    return CHAT_RESPONSE_JSON_SCHEMA


def _finalize_result(result: AIChatResult, parsed_bet: ParsedBet) -> AIChatResult:
    fallback = _fallback_result(parsed_bet)
    if not result.response:
        return fallback

    if parsed_bet.detected_language == "es":
        result.response = _localize_visible_response_es(result.response)
    if result.implied_probability is None:
        result.implied_probability = parsed_bet.implied_probability
    if result.verdict is None:
        result.verdict = fallback.verdict
    if result.stake_posture is None:
        result.stake_posture = fallback.stake_posture
    return result


def _fallback_result(parsed_bet: ParsedBet) -> AIChatResult:
    if parsed_bet.detected_language == "es":
        return _fallback_result_es(parsed_bet)
    return _fallback_result_en(parsed_bet)


def _fallback_result_en(parsed_bet: ParsedBet) -> AIChatResult:
    odds_text = f"{parsed_bet.odds:.2f}" if parsed_bet.odds else "not provided"
    probability_text = (
        f"{parsed_bet.implied_probability * 100:.1f}%"
        if parsed_bet.implied_probability is not None
        else "not calculable without odds"
    )
    bet_target = parsed_bet.raw_match_text or "the bet"

    if not parsed_bet.teams and _classify_chat_intent(parsed_bet.original_message, parsed_bet) == "discovery_or_bankroll_request":
        verdict = "NOT ENOUGH INFO"
        stake_posture = "avoid"
        confidence_score = 4.0
        amount_text = (
            f"{parsed_bet.stake_amount:g} {parsed_bet.stake_currency}"
            if parsed_bet.stake_amount and parsed_bet.stake_currency
            else f"{parsed_bet.stake_amount:g}" if parsed_bet.stake_amount else "budget"
        )
        response = f"""I would not spend that {amount_text} blindly, but you should not have to leave Matchmind to get started. The value is not in random team names; it is in using the in-app Feed, bookmaker board, and market signals to narrow the board before you stake anything.

Here is the useful path: pick a risk style first. Conservative means 1-2 small positions and lots of passing. Balanced means a short in-app shortlist of 3-5 bets to price-check. Aggressive means long shots, but only tiny stakes because World Cup variance is brutal.

Tell me conservative, balanced, or aggressive and I will work from the matches and signals Matchmind already has. Until then, keep the stake posture as avoid: do not bet just because the money is available.

Confidence: {confidence_score:g}/10"""
        return AIChatResult(
            response=response,
            confidence_score=confidence_score,
            verdict=verdict,
            implied_probability=None,
            stake_posture=stake_posture,
        )

    if not parsed_bet.teams:
        verdict = "NOT ENOUGH INFO"
        stake_posture = "avoid"
        confidence_score = 3.0
        my_take = "I cannot give you a useful betting take yet because I do not know the team, match, or bet target. Send me the selection and the odds, and I will judge whether the price is worth touching."
        value_judgment = "Not enough information."
    elif parsed_bet.odds is None:
        verdict = "NOT ENOUGH INFO"
        stake_posture = "avoid"
        confidence_score = 4.0
        my_take = f"I can see the angle on {bet_target}, but I would not judge value without the actual price. The same football opinion can be good at one number and poor at another, so the odds matter."
        value_judgment = "Not enough information without the price."
    elif parsed_bet.odds <= 1.40:
        verdict = "RISKY"
        stake_posture = "very small"
        confidence_score = 5.5
        my_take = f"This looks short on {bet_target}. At {parsed_bet.odds:.2f}, you need it to land more than {parsed_bet.implied_probability * 100:.1f}% of the time just to break even, which leaves very little room for World Cup chaos."
        value_judgment = "Likely poor unless live data strongly supports it."
    elif parsed_bet.odds >= 6.00:
        verdict = "RISKY"
        stake_posture = "very small"
        confidence_score = 5.0
        my_take = f"This is a high-variance position on {bet_target}. The price is interesting, but long odds need market comparison and tournament context before I would call them value."
        value_judgment = "Interesting number, but not automatically value."
    else:
        verdict = "FAIR"
        stake_posture = "small"
        confidence_score = 5.5
        my_take = f"I do not hate the bet on {bet_target}, but I would not call it clear value without live odds, team news, and market comparison. Treat it as a controlled opinion, not a spot to force."
        value_judgment = "Potentially fair, but not obviously generous."

    response = f"""Short version: {verdict}. {my_take}

At the price you gave me, the odds are {odds_text} and the implied probability is {probability_text}. My value read: {value_judgment}

The main caveat is that I do not have live bookmaker, lineup, injury, or market-signal data in this fallback analysis. Keep the stake posture {stake_posture}; do not size up because of loyalty, emotion, or chasing.

Confidence: {confidence_score:g}/10"""

    return AIChatResult(
        response=response,
        confidence_score=confidence_score,
        verdict=verdict,
        implied_probability=parsed_bet.implied_probability,
        stake_posture=stake_posture,
    )


def _fallback_result_es(parsed_bet: ParsedBet) -> AIChatResult:
    odds_text = f"{parsed_bet.odds:.2f}" if parsed_bet.odds else "no proporcionada"
    probability_text = (
        f"{parsed_bet.implied_probability * 100:.1f}%"
        if parsed_bet.implied_probability is not None
        else "no calculable sin cuota"
    )
    bet_target = parsed_bet.raw_match_text or "la apuesta"

    if not parsed_bet.teams and _classify_chat_intent(parsed_bet.original_message, parsed_bet) == "discovery_or_bankroll_request":
        verdict = "NOT ENOUGH INFO"
        stake_posture = "avoid"
        confidence_score = 4.0
        amount_text = f"{parsed_bet.stake_amount:g} {parsed_bet.stake_currency}" if parsed_bet.stake_amount else "ese dinero"
        response = f"""Yo no metería {amount_text} a ciegas, pero tampoco deberías tener que salir de Matchmind para empezar. El valor no está en soltar nombres al azar; está en usar el Feed, las cuotas y las señales de mercado de la app para reducir opciones antes de poner dinero.

La forma útil de empezar es elegir perfil de riesgo. Conservador: 1-2 posiciones pequeñas y muchas apuestas descartadas. Equilibrado: una shortlist dentro de la app con 3-5 apuestas para revisar. Agresivo: cuotas largas, pero con importes muy pequeños porque el Mundial tiene mucha varianza.

Dime conservador, equilibrado o agresivo y trabajo desde los partidos y señales que Matchmind ya tiene. Hasta entonces, postura de stake: evitar; no apuestes solo porque tienes presupuesto.

Confianza: {confidence_score:g}/10"""
        return AIChatResult(
            response=response,
            confidence_score=confidence_score,
            verdict=verdict,
            implied_probability=None,
            stake_posture=stake_posture,
        )

    if not parsed_bet.teams:
        verdict = "NOT ENOUGH INFO"
        visible_verdict = "NO HAY INFO SUFICIENTE"
        stake_posture = "avoid"
        visible_posture = "evitar"
        confidence_score = 3.0
        my_take = "No puedo darte una lectura útil todavía porque no sé el equipo, partido o mercado exacto. Pásame la selección y la cuota, y te digo si el precio merece la pena."
        value_judgment = "No hay información suficiente."
    elif parsed_bet.odds is None:
        verdict = "NOT ENOUGH INFO"
        visible_verdict = "NO HAY INFO SUFICIENTE"
        stake_posture = "avoid"
        visible_posture = "evitar"
        confidence_score = 4.0
        my_take = f"Veo la idea sobre {bet_target}, pero no juzgaría valor sin la cuota. La misma opinión futbolística puede ser buena a un precio y mala a otro."
        value_judgment = "No hay información suficiente sin la cuota."
    elif parsed_bet.odds <= 1.40:
        verdict = "RISKY"
        visible_verdict = "ARRIESGADA"
        stake_posture = "very small"
        visible_posture = "muy pequeño"
        confidence_score = 5.5
        my_take = f"Esta cuota se ve corta para {bet_target}. A {parsed_bet.odds:.2f}, necesitas que salga más del {parsed_bet.implied_probability * 100:.1f}% de las veces solo para empatar, y en un Mundial hay poco margen para sustos."
        value_judgment = "Probablemente pobre salvo que los datos en vivo la apoyen mucho."
    elif parsed_bet.odds >= 6.00:
        verdict = "RISKY"
        visible_verdict = "ARRIESGADA"
        stake_posture = "very small"
        visible_posture = "muy pequeño"
        confidence_score = 5.0
        my_take = f"Esto es una posición de mucha varianza sobre {bet_target}. La cuota es interesante, pero necesito comparación de mercado y contexto del torneo antes de llamarla valor."
        value_judgment = "Número interesante, pero no es valor automáticamente."
    else:
        verdict = "FAIR"
        visible_verdict = "JUSTA / NEUTRAL"
        stake_posture = "small"
        visible_posture = "pequeño"
        confidence_score = 5.5
        my_take = f"No odio la apuesta sobre {bet_target}, pero no la llamaría valor claro sin cuotas en vivo, noticias del equipo y comparación de mercado. Trátala como una opinión controlada, no como algo que haya que forzar."
        value_judgment = "Potencialmente justa, pero no claramente generosa."

    response = f"""Resumen rápido: {visible_verdict}. {my_take}

Con la cuota que me das, el precio es {odds_text} y la probabilidad implícita es {probability_text}. Mi lectura de valor: {value_judgment}

La gran cautela es que no tengo datos en vivo de casas de apuestas, alineaciones, lesiones ni señales de mercado en este análisis de respaldo. Postura de stake: {visible_posture}; no subas el importe por lealtad, emoción o por intentar recuperar.

Confianza: {confidence_score:g}/10"""

    return AIChatResult(
        response=response,
        confidence_score=confidence_score,
        verdict=verdict,
        implied_probability=parsed_bet.implied_probability,
        stake_posture=stake_posture,
    )


async def generate_chat_reply(
    message: str,
    match_context: dict[str, Any] | None = None,
    polymarket_context: dict[str, Any] | None = None,
    bookmaker_context: dict[str, Any] | None = None,
    preferred_language: str | None = None,
    conversation_memory: list[dict[str, Any]] | None = None,
) -> AIChatResult:
    parsed_bet = parse_bet_message(message)
    if preferred_language in {"en", "es"}:
        parsed_bet = parsed_bet.model_copy(update={"detected_language": preferred_language})
    settings = get_settings()
    client = AsyncOpenAI(api_key=settings.openai_api_key)
    completion = await client.chat.completions.create(
        model=settings.openai_model,
        response_format=_chat_response_format(),
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": _build_user_context(
                    message,
                    parsed_bet,
                    match_context,
                    polymarket_context,
                    bookmaker_context,
                    conversation_memory,
                ),
            },
        ],
        temperature=0.4,
    )
    content = completion.choices[0].message.content or "{}"
    result = _extract_json(content)
    return _finalize_result(result, parsed_bet)
