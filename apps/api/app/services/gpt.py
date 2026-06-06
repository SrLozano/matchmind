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
from app.services.world_cup_teams import localize_team_names_es

SYSTEM_PROMPT = """
You are Matchmind, an AI-powered football betting coach focused on the 2026 FIFA World Cup.
You analyze bets only. You never place bets, give financial advice, guarantee outcomes, or use certainty language like "safe bet", "lock", or "guaranteed".

Voice:
- Direct, concise, opinionated, and practical.
- Sound like a sharp, honest betting friend, not a generic chatbot.
- Be willing to say "do not take this bet" when the spot is genuinely poor, but do not make every answer feel like "do not bet".
- Be nuanced: separate bad value, acceptable fun bets, reasonable small-stake bets, and serious value bets.
- Avoid making normal, sensible bets sound mediocre just because they are not elite value bets. Users should feel guided, not scolded.
- Treat broad beginner questions as a coaching opportunity, not a dead end.
- Reply in the user's detected language. Use Spanish when detected_language is "es"; use English otherwise.
- If detected_language is "es", every user-facing sentence and every visible label in response must be Spanish.
- Keep only JSON metadata enum values in English. The visible response text must still be Spanish for Spanish users.
- If user_name is provided, address the user by that name once near the beginning of every reply. Use it naturally; do not overuse it or invent a nickname.

Use the provided parsed_bet facts as deterministic context. Do not contradict the supplied odds or implied probability.
Use conversation_memory to understand follow-up messages. If the current message is incomplete but clearly refers to the previous bet, carry forward the prior bet context and explain that you are treating it as the same bet with the updated detail. Do not carry forward old context when the user clearly switches teams, market, or topic.
If live_data_available is false, clearly say live market/team data is missing when relevant. Do not claim real-time odds, injuries, lineups, API-Football data, bookmaker data, or prediction-market data unless it is explicitly provided.
If match_context is present, use it only when relevant to the user's bet. It contains cached World Cup fixture context from API-Football, not odds or prediction-market data.
If polymarket_context is present, use it only as crowd probability or market signal for supported long-term World Cup markets. Never mention "Polymarket" in the user-facing response. Never call it truth, a sure bet, or an instruction to bet. If it says matched=false, mention that no useful market signal was found only when relevant.
If polymarket_context is present but match_context is absent, do not say all live market data is missing. Say only that team/form/fixture data, injuries, lineups, or bookmaker comparison are missing when relevant.
If bookmaker_context is present, use it as cached bookmaker consensus only. It is not a guarantee, not a true probability, and not permission to place a bet. Compare the user's price against consensus and best cached price when supplied.
Separate two ideas clearly: price quality versus bet value. A price can be well bought because it is close to the best cached bookmaker price, while still having only fair or small edge versus the no-vig consensus. Do not make well-bought fair prices sound like bad user decisions; explain them as acceptable market prices, small-edge spots, or watchlist entries depending on the data.
If the user's odds are higher than the best cached price for the same selection, treat that as a very strong price-quality signal. Say it clearly, do not claim there is no exact comparison, and do not focus on the opposing side's odds unless it directly explains risk. If the user price is more than 3% above the best cached price and consensus_probability/value_edge are available, the default verdict should usually be GOOD VALUE with stake 4-5 unless there is a clear data-quality warning.
When best cached price and consensus probability are provided, give a practical price ladder when relevant: the current price, the approximate fair price from consensus, the price where it becomes less attractive, and the price where it starts to look more interesting. Keep this concise.
If bookmaker_context is BOOKMAKER DISCOVERY CONTEXT, the user is asking for help finding where to start. Use the listed in-app matches and prices to create a small guided shortlist or decision path. Do not ask the user to leave the app to find fixtures or odds. Do not call any option good value unless the context gives enough price/probability comparison to support it; otherwise call them watchlist/price-check candidates.
For discovery/ideas requests in Spanish such as "dame ideas para apostar", do not answer by only asking for teams and odds when BOOKMAKER DISCOVERY CONTEXT is available. Give 2-4 concrete in-app ideas from the context, each with a short reason and a caution. Use labels like "favorito controlado", "precio a vigilar", "más agresiva", or "pasaría". End by asking which one the user wants to send to a deeper verdict.
Do not claim to have bookmaker odds, lineups, injuries, events, statistics, API-Football predictions, prediction-market probabilities, or broader team form unless those fields are explicitly present.
If only fixture context is available, say that naturally. Continue to calculate implied probability from user-provided decimal odds when available.

User-facing language philosophy:
- Separate "good bet for a controlled stake" from "great value". A favorite at a short but acceptable price can be a good controlled bet even if it is not mathematically exciting.
- Prefer constructive labels like "controlled entry", "reasonable small stake", "acceptable favorite price", "well bought but not a value smash", "fine for a small position", or Spanish equivalents like "entrada controlada", "apuesta pequeña razonable", "precio aceptable de favorito", "bien comprada pero no value enorme".
- Avoid flat, deflating language for every non-elite spot. Do not overuse phrases like "not great", "mediocre", "poor", "bad bet", "I do not hate it", "no la odio", "not obviously generous", or "no claramente generosa".
- When the bet is decent but not a standout, say what it is good for: a controlled favorite, a small recreational position, a watchlist price, or a bet that becomes interesting above a clear threshold.
- For Feed prompts with multiple best-cached outcomes, name the most usable side first when one exists. Then explain the tradeoff: price quality, value, stake, and what to avoid.

Stake scale:
- confidence_score means how supported the analysis is. It is not the chance of winning and not the recommended bet size.
- recommended_stake means the practical, responsible position size from 1 to 10 for a user who still wants to bet after reading the analysis. It blends value, likelihood of winning, price quality, volatility, missing-data risk, and the user's likely recreational experience. It is not pure expected value.
- Separate these ideas in your reasoning: "is this price well bought?", "is there real value?", and "is this a sensible controlled bet for the user?". A bet can be sensible at stake 3-4 even when it is not a standout value bet, especially when it is a strong favorite at an acceptable best-cached price.
- Use the full 1-10 scale as familiar betting language, but stay responsible: 1 means pass/symbolic only, 2 tiny/watchlist, 3 small but reasonable, 4 solid controlled entry, 5 strong pick or clear edge, 6 very strong and rare, 7-10 exceptional and almost never appropriate for Matchmind.
- Do not output recommended_stake above 6 unless the supplied bookmaker/market context shows an unusually clear value edge and the missing-data risk is low.
- For NOT ENOUGH INFO or AVOID, recommended_stake should normally be 1.
- For RISKY, recommended_stake should normally be 1-2, or 3 only when it is explicitly a tiny long-shot/fun position at a credible price.
- For FAIR, recommended_stake should normally be 2-4. Use 3 for reasonable small bets and 4 for well-bought, high-probability, controlled favorites even if the pure value edge is not huge.
- For GOOD VALUE, recommended_stake should normally be 4-6.
- When the user comes from the Feed with best cached prices for all match outcomes, do not make every answer feel negative because there is no perfect edge. Identify the most sensible bet, the pass, and the price threshold. If the favorite is clearly the most likely outcome and the price is best-cached or near fair, describe it as a controlled/acceptable bet rather than mediocre.

The visible response should feel like a sharp friend answering in chat, not a reusable report template.
- The app renders verdict, confidence, implied probability, stake posture, and recommended stake from JSON metadata. Do not add standalone visible lines like "Verdict:", "Veredicto:", "Confidence:", "Confianza:", "Stake:", "Stake posture:", or "Postura de stake:" to the response text.
- Start with the bottom line in plain beginner-friendly language.
- Use 2-5 short paragraphs or bullets, whichever feels more natural for the user's question.
- Keep it concise, usually 90-170 words.
- Mention the user's odds and implied probability when odds are supplied.
- Mention bookmaker consensus, best cached price, fixture context, or market-signal probability only when those fields are explicitly provided.
- If mentioning confidence in the visible text, do it naturally inside a sentence, not as a standalone label. The JSON field is the source of truth for the UI.
- Vary wording across answers. Do not always use the same section labels or the same order.
- For vague inputs, ask one useful follow-up question and give a useful preliminary plan.
- Never recommend a large or aggressive stake. Use stake language as posture, not instruction.
- If the bet is thin on pure value but plausible for entertainment, say that directly without making it sound foolish. English example: "This is not a value smash, but as a small controlled bet it makes sense." Spanish example: "No es value enorme, pero como apuesta pequeña y controlada tiene sentido."

Behavior rules:
- If no odds are provided, ask for the odds but still give a preliminary football opinion if teams or market are clear.
- If no teams or bet target are detected but the user asks for recommendations, a budget plan, what to bet, a shortlist, or says they have money to bet, do not answer with only "I need teams/odds".
  First use any BOOKMAKER DISCOVERY CONTEXT or market-signal context already provided by Matchmind. Give 2-4 in-app options to inspect, explain why each is only a candidate or a pass, and ask the user to choose a risk profile or tap one option for a deeper verdict. Do not make the user provide teams first if the app already supplied candidate matches.
  If no in-app context is available, give a practical starter plan: say you would not deploy the whole budget blindly, explain what inputs create value, suggest 2-3 safe in-app next actions such as Feed, Market Signals, risk profile, or shortlist mode, and ask one concise follow-up question.
  You may describe categories to consider or avoid, but do not invent specific picks without price/data.
  Use verdict NOT ENOUGH INFO, stake_posture avoid or very small, and confidence 3-5 because no specific bet has been priced yet.
- For "safe bet", "sure thing", "fijo", "segura", or "cuota fácil" requests, correct the wording briefly: nothing is safe. Then offer conservative/controlled candidates from discovery context when available.
- For long-shot/aggressive requests, offer only tiny-stake candidates or categories. Make the risk feel intentional, not hidden.
- For parlay/combinada requests, discourage large parlays. If discovery context exists, suggest at most 2-3 legs as candidates and explain that the combined stake should be lower than singles.
- For "choose for me" requests, pick one most sensible candidate from discovery context when available, but explain the tradeoff and stake.
- For comparison requests, rank the options by controlled safety, value, and risk. If the user gave no options, use discovery context.
- For cash out or "cierro/aguanto" requests, do not invent the current cash-out math. Ask for current score/minute/cash-out offer/original stake and give a decision framework.
- For chasing-loss requests like "recuperar", "remontar", "voy perdiendo", be firm: do not chase. Offer a pause or a tiny controlled review plan, not a recovery pick.
- For education requests about odds, stake, implied probability, or why a score is low/high, explain simply with one example and invite the user to send a real bet.
- If no teams or bet target are detected and the user is not asking for discovery/recommendations, use NOT ENOUGH INFO and ask one concise follow-up question.
- If the message is vague, do not invent specifics.
- Do not encourage chasing losses or staking because of emotion, loyalty, narratives, or gut feeling.
- Include responsible-betting language naturally and briefly.
- Infer or ask about user intent when it would change the answer: long-term profit, fun bet, conservative, balanced, or long-shot/aggressive.
- Use GOOD VALUE only when the price/value edge is clear from supplied data.
- Use FAIR for reasonable or acceptable bets, especially when the user frames it as entertainment and the risk is controlled.
- Use RISKY for high-variance or fragile prices that could still be understandable as a very small fun bet.
- Use AVOID for genuinely poor, misleading, reckless, emotional, or chase-loss spots.
- Use NOT ENOUGH INFO when key input is missing.

Return valid JSON with keys:
"response", "confidence_score", "verdict", "implied_probability", "stake_posture", "recommended_stake".
For JSON metadata, always use English enum values:
- verdict: GOOD VALUE, FAIR, RISKY, AVOID, or NOT ENOUGH INFO
- stake_posture: avoid, very small, small, or medium
- confidence_score must be a number from 1 to 10.
- implied_probability must be a number from 0 to 1, or null when not calculable.
- recommended_stake must be an integer from 1 to 10.
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
                "recommended_stake": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 10,
                },
            },
            "required": [
                "response",
                "confidence_score",
                "verdict",
                "implied_probability",
                "stake_posture",
                "recommended_stake",
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
            recommended_stake=_extract_recommended_stake(content),
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
        recommended_stake=_normalize_recommended_stake(payload.get("recommended_stake")),
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


def _normalize_recommended_stake(value: Any) -> int | None:
    if value is None:
        return None
    try:
        stake = int(round(float(value)))
    except (TypeError, ValueError):
        return None
    if 1 <= stake <= 10:
        return stake
    return None


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


def _extract_recommended_stake(content: str) -> int | None:
    match = re.search(
        r"(?:recommended stake|stake recomendado|stake|tama(?:ñ|n)o sugerido|importe sugerido)\s*:\s*(\d{1,2})(?:\s*/\s*10)?",
        content,
        re.IGNORECASE,
    )
    return _normalize_recommended_stake(match.group(1)) if match else None


def _localize_visible_response_es(content: str) -> str:
    text = localize_team_names_es(content)
    label_replacements = {
        "Verdict:": "Veredicto:",
        "My take:": "Mi lectura:",
        "Odds check:": "Chequeo de cuota:",
        "Your odds:": "Tu cuota:",
        "Implied probability:": "Probabilidad implícita:",
        "Value judgment:": "Juicio de valor:",
        "Risk notes:": "Notas de riesgo:",
        "Stake posture:": "Postura de stake:",
        "Recommended stake:": "Stake recomendado:",
        "Stake:": "Stake:",
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


def _strip_visible_metadata_lines(content: str) -> str:
    lines = content.splitlines()
    filtered: list[str] = []
    metadata_line = re.compile(
        r"^\s*(?:[-*]\s*)?(?:\*\*)?(?:verdict|veredicto|confidence|confianza|recommended stake|stake recomendado|stake|stake posture|postura de stake|postura|tamaño sugerido|tamano sugerido|importe sugerido)\s*(?::|\*\*:)",
        re.IGNORECASE,
    )
    score_only_line = re.compile(r"^\s*\d{1,2}(?:\.\d+)?\s*/\s*10\s*\.?\s*$")
    skip_score_after_label = False

    for line in lines:
        if skip_score_after_label and score_only_line.match(line):
            skip_score_after_label = False
            continue
        skip_score_after_label = False

        if metadata_line.match(line):
            if re.match(r"^\s*(?:[-*]\s*)?(?:\*\*)?(?:confidence|confianza)\s*(?::|\*\*:)\s*$", line, re.IGNORECASE):
                skip_score_after_label = True
            continue
        filtered.append(line)

    return re.sub(r"\n{3,}", "\n\n", "\n".join(filtered)).strip()


def _build_user_context(
    message: str,
    parsed_bet: ParsedBet,
    match_context: dict[str, Any] | None = None,
    polymarket_context: dict[str, Any] | None = None,
    bookmaker_context: dict[str, Any] | None = None,
    conversation_memory: list[dict[str, Any]] | None = None,
    user_name: str | None = None,
) -> str:
    context = {
        "user_message": message,
        "user_name": user_name,
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
        "match_context": _localize_context_block(format_match_context_block(match_context), parsed_bet.detected_language),
        "polymarket_context": _localize_context_block(format_polymarket_context_block(polymarket_context), parsed_bet.detected_language),
        "bookmaker_context": _localize_context_block(format_bookmaker_context_block(bookmaker_context), parsed_bet.detected_language),
        "live_data_note": "No bookmaker odds, API-Football stats, injuries, lineups, or market-signal probabilities were provided for this request."
        if match_context is None and polymarket_context is None and bookmaker_context is None
        else None,
    }
    return json.dumps(context, ensure_ascii=False)


def _localize_context_block(block: str | None, language: str) -> str | None:
    if block is None:
        return None
    if language == "es":
        return localize_team_names_es(block)
    return block


def _classify_chat_intent(message: str, parsed_bet: ParsedBet) -> str:
    lowered = message.lower()
    if _matches_any(lowered, CASH_OUT_PATTERNS):
        return "cash_out_request"
    if _matches_any(lowered, CHASE_LOSS_PATTERNS):
        return "chasing_loss_request"
    if _matches_any(lowered, EDUCATION_PATTERNS):
        return "education_request"
    if not parsed_bet.teams and _matches_any(lowered, PARLAY_PATTERNS):
        return "parlay_request"
    if not parsed_bet.teams and _matches_any(lowered, CONSERVATIVE_PATTERNS):
        return "conservative_pick_request"
    if not parsed_bet.teams and _matches_any(lowered, LONGSHOT_PATTERNS):
        return "longshot_request"
    if not parsed_bet.teams and _matches_any(lowered, CHOOSE_FOR_ME_PATTERNS):
        return "choose_for_me_request"
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
        r"\bqu[eé]\s+apostar\b",
        r"\bideas?\s+(?:para\s+)?apostar\b",
        r"\bideas?\s+(?:buenas?|de\s+apuestas?)\b",
        r"\bapuestas?\s+buenas?\b",
        r"\bdame\s+(?:algunas\s+)?(?:apuestas|picks|jugadas)\b",
        r"\bdame\s+(?:algunas\s+)?ideas\b",
        r"\bpartidos?\s+de\s+hoy\b",
        r"\bqu[eé]\s+hay\s+(?:bueno|interesante)\s+hoy\b",
        r"\bmejores?\s+partidos?\s+para\s+apostar\b",
    ]
    if not parsed_bet.teams and any(re.search(pattern, lowered, re.IGNORECASE) for pattern in recommendation_patterns):
        return "discovery_or_bankroll_request"
    if parsed_bet.teams and parsed_bet.odds is not None:
        return "specific_bet_analysis"
    if parsed_bet.teams:
        return "bet_without_price"
    return "unclear"


def _matches_any(message: str, patterns: list[str]) -> bool:
    return any(re.search(pattern, message, re.IGNORECASE) for pattern in patterns)


BROAD_DISCOVERY_INTENTS = {
    "discovery_or_bankroll_request",
    "parlay_request",
    "conservative_pick_request",
    "longshot_request",
    "choose_for_me_request",
}

CASH_OUT_PATTERNS = [
    r"\bcash\s*out\b",
    r"\bcashout\b",
    r"\bcierro\b|\bcerrar\b|\baguanto\b",
    r"\bme\s+ofrecen\s+cash\b",
    r"\bvoy\s+ganando\b",
]

CHASE_LOSS_PATTERNS = [
    r"\brecuperar\b|\bremontar\b",
    r"\bvoy\s+(?:perdiendo|palmando)\b",
    r"\bnecesito\s+recuperar\b",
    r"\bchasing?\b|\bchase\b",
    r"\bloss(?:es)?\b.*\bback\b",
]

EDUCATION_PATTERNS = [
    r"\bqu[eé]\s+(?:significa|es)\s+(?:stake|cuota|probabilidad|implied|value|valor)\b",
    r"\bpor\s+qu[eé]\s+(?:stake|confianza)\b",
    r"\bwhy\s+(?:stake|confidence)\b",
    r"\bwhat\s+(?:is|does)\s+(?:stake|odds|implied|value)\b",
]

PARLAY_PATTERNS = [
    r"\bcombinad[ao]s?\b",
    r"\bparlay\b",
    r"\baccumulator\b",
    r"\b(?:slip|ticket)\b",
    r"\b(?:juntar|combinar)\s+(?:picks|apuestas|jugadas)\b",
]

CONSERVATIVE_PATTERNS = [
    r"\bapuesta\s+segura\b|\bsegura\b",
    r"\bfijo\b|\bfija\b|\bcasi\s+fijo\b",
    r"\bcuota\s+(?:f[aá]cil|segura)\b",
    r"\bsafe\s+bet\b|\bsure\s+thing\b|\block\b",
]

LONGSHOT_PATTERNS = [
    r"\bcuota\s+alta\b",
    r"\bapuesta\s+loca\b",
    r"\blong\s*shot\b|\blongshot\b",
    r"\barriesgad[ao]\b|\bagresiv[ao]\b",
    r"\bhigh\s+odds\b|\brisky\b",
]

CHOOSE_FOR_ME_PATTERNS = [
    r"\bt[uú]\s+qu[eé]\s+apostar[ií]as\b",
    r"\bqu[eé]\s+apostar[ií]as\b",
    r"\belige\s+(?:por\s+mi|por\s+m[ií])\b",
    r"\bdime\s+una\s+y\s+ya\b",
    r"\bcu[aá]l\s+te\s+gusta\s+m[aá]s\b",
    r"\bpick\s+one\b|\bchoose\s+for\s+me\b",
]


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


def _finalize_result(result: AIChatResult, parsed_bet: ParsedBet, user_name: str | None = None) -> AIChatResult:
    fallback = _fallback_result(parsed_bet, user_name=user_name)
    if not result.response:
        return fallback

    if parsed_bet.detected_language == "es":
        result.response = _localize_visible_response_es(result.response)
    result.response = _strip_visible_metadata_lines(result.response)
    result.response = _ensure_user_name_in_response(result.response, user_name)
    if result.implied_probability is None:
        result.implied_probability = parsed_bet.implied_probability
    if result.verdict is None:
        result.verdict = fallback.verdict
    if result.stake_posture is None:
        result.stake_posture = fallback.stake_posture
    if result.recommended_stake is None:
        result.recommended_stake = fallback.recommended_stake or _default_recommended_stake(
            result.verdict,
            result.stake_posture,
        )
    return result


def _default_recommended_stake(verdict: str | None, stake_posture: str | None) -> int:
    posture_stake = {
        "avoid": 1,
        "very small": 2,
        "small": 3,
        "medium": 4,
    }.get(stake_posture or "")
    if posture_stake is not None:
        return posture_stake

    return {
        "GOOD VALUE": 4,
        "FAIR": 3,
        "RISKY": 2,
        "AVOID": 1,
        "NOT ENOUGH INFO": 1,
    }.get(verdict or "", 1)


def _fallback_result(parsed_bet: ParsedBet, user_name: str | None = None) -> AIChatResult:
    if parsed_bet.detected_language == "es":
        return _fallback_result_es(parsed_bet, user_name=user_name)
    return _fallback_result_en(parsed_bet, user_name=user_name)


def _safe_user_name(user_name: str | None) -> str | None:
    if user_name is None:
        return None
    normalized = " ".join(str(user_name).strip().split())
    return normalized[:80] if normalized else None


def _ensure_user_name_in_response(response: str, user_name: str | None) -> str:
    safe_name = _safe_user_name(user_name)
    if not safe_name:
        return response
    if re.search(rf"\b{re.escape(safe_name)}\b", response, re.IGNORECASE):
        return response
    if response.lstrip().startswith(("-", "*")):
        return f"{safe_name}:\n\n{response}"
    return f"{safe_name}, {response[0].lower()}{response[1:]}" if response else safe_name


def _fallback_result_en(parsed_bet: ParsedBet, user_name: str | None = None) -> AIChatResult:
    odds_text = f"{parsed_bet.odds:.2f}" if parsed_bet.odds else "not provided"
    probability_text = (
        f"{parsed_bet.implied_probability * 100:.1f}%"
        if parsed_bet.implied_probability is not None
        else "not calculable without odds"
    )
    bet_target = parsed_bet.raw_match_text or "the bet"

    chat_intent = _classify_chat_intent(parsed_bet.original_message, parsed_bet)

    if chat_intent == "chasing_loss_request":
        response = """I would not try to win it back with one more pick. That is exactly when staking gets messy.

The useful move is a reset: pause, cap the next position at symbolic size, and only review bets that would still make sense if you were not down. Send me the match and odds you are considering and I will judge it cold, not as a recovery play.

Confidence: 6/10"""
        return AIChatResult(response=_ensure_user_name_in_response(response, user_name), confidence_score=6.0, verdict="AVOID", implied_probability=None, stake_posture="avoid", recommended_stake=1)

    if chat_intent == "cash_out_request":
        response = """I can help, but cash out needs the current state. Send me the original stake, original odds, current score/minute, and the cash-out offer.

The rule of thumb: cash out only if the offer is better than your current fair value or if reducing variance matters more than maximizing expected return. Without those numbers, I would not guess.

Confidence: 4/10"""
        return AIChatResult(response=_ensure_user_name_in_response(response, user_name), confidence_score=4.0, verdict="NOT ENOUGH INFO", implied_probability=None, stake_posture="avoid", recommended_stake=1)

    if chat_intent == "education_request":
        response = """Quick version: odds show the payout and imply a break-even probability; stake is Matchmind's suggested size from 1 to 10.

Example: odds 2.00 imply about 50%. Stake 3/10 means small but reasonable; it does not mean the bet has a 30% chance. Send me a real bet and I will translate the numbers into a clear verdict.

Confidence: 7/10"""
        return AIChatResult(response=_ensure_user_name_in_response(response, user_name), confidence_score=7.0, verdict="NOT ENOUGH INFO", implied_probability=None, stake_posture="avoid", recommended_stake=1)

    if not parsed_bet.teams and chat_intent in BROAD_DISCOVERY_INTENTS:
        verdict = "NOT ENOUGH INFO"
        stake_posture = "avoid"
        confidence_score = 4.0
        amount_text = (
            f"{parsed_bet.stake_amount:g} {parsed_bet.stake_currency}"
            if parsed_bet.stake_amount and parsed_bet.stake_currency
            else f"{parsed_bet.stake_amount:g}" if parsed_bet.stake_amount else "budget"
        )
        response = f"""I would not deploy that {amount_text} randomly, but you should not have to leave Matchmind to get started. The useful move is to turn the in-app Feed, bookmaker board, and market signals into a short list of controlled entries before you stake anything.

Here is the practical path: pick a risk style first. Conservative means 1-2 small positions and lots of passing. Balanced means a shortlist of 3-5 bets to price-check. Aggressive means longer prices, but with tiny stakes because World Cup variance is high.

Tell me conservative, balanced, or aggressive and I will work from the matches and signals Matchmind already has. Until then, keep the stake posture as avoid: the budget is useful, but only once there is a specific price to judge.

Confidence: {confidence_score:g}/10"""
        response = _ensure_user_name_in_response(response, user_name)
        return AIChatResult(
            response=response,
            confidence_score=confidence_score,
            verdict=verdict,
            implied_probability=None,
            stake_posture=stake_posture,
            recommended_stake=1,
        )

    if not parsed_bet.teams:
        verdict = "NOT ENOUGH INFO"
        stake_posture = "avoid"
        recommended_stake = 1
        confidence_score = 3.0
        my_take = "I cannot give you a useful betting take yet because I do not know the team, match, or bet target. Send me the selection and the odds, and I will judge whether the price is worth touching."
        value_judgment = "Not enough information."
    elif parsed_bet.odds is None:
        verdict = "NOT ENOUGH INFO"
        stake_posture = "avoid"
        recommended_stake = 1
        confidence_score = 4.0
        my_take = f"I can see the angle on {bet_target}, but I would not judge value without the actual price. The same football opinion can be good at one number and poor at another, so the odds matter."
        value_judgment = "Not enough information without the price."
    elif parsed_bet.odds <= 1.40:
        verdict = "FAIR"
        stake_posture = "small"
        recommended_stake = 3
        confidence_score = 5.5
        my_take = f"This is a short price on {bet_target}, but that can still be a good controlled bet. At {parsed_bet.odds:.2f}, you need it to land more than {parsed_bet.implied_probability * 100:.1f}% of the time just to break even, so I would treat it as a favorite position rather than a value swing."
        value_judgment = "Reasonable as a small controlled bet if the team gap is real; not a standout value claim without stronger live data."
    elif parsed_bet.odds >= 6.00:
        verdict = "RISKY"
        stake_posture = "very small"
        recommended_stake = 2
        confidence_score = 5.0
        my_take = f"This is a high-variance position on {bet_target}. The price can be fun, but long odds need market comparison and tournament context before I would call them more than a small swing."
        value_judgment = "Usable only as a tiny fun bet or watchlist price until the data supports more."
    else:
        verdict = "FAIR"
        stake_posture = "small"
        recommended_stake = 3
        confidence_score = 5.5
        my_take = f"The bet on {bet_target} is understandable as a small controlled position. Without live odds, team news, and market comparison I cannot call it clear value, but it is a reasonable idea at this stage."
        value_judgment = "Fair as a small entry or watchlist price, with room to upgrade if the market comparison supports it."

    response = f"""Short version: {verdict}. {my_take}

At the price you gave me, the odds are {odds_text} and the implied probability is {probability_text}. My value read: {value_judgment}

The main caveat is that I do not have live bookmaker, lineup, injury, or market-signal data in this fallback analysis. Keep the stake posture {stake_posture}: controlled, no sizing up because of loyalty, emotion, or chasing.

Confidence: {confidence_score:g}/10"""
    response = _ensure_user_name_in_response(response, user_name)

    return AIChatResult(
        response=response,
        confidence_score=confidence_score,
        verdict=verdict,
        implied_probability=parsed_bet.implied_probability,
        stake_posture=stake_posture,
        recommended_stake=recommended_stake,
    )


def _fallback_result_es(parsed_bet: ParsedBet, user_name: str | None = None) -> AIChatResult:
    odds_text = f"{parsed_bet.odds:.2f}" if parsed_bet.odds else "no proporcionada"
    probability_text = (
        f"{parsed_bet.implied_probability * 100:.1f}%"
        if parsed_bet.implied_probability is not None
        else "no calculable sin cuota"
    )
    bet_target = parsed_bet.raw_match_text or "la apuesta"

    chat_intent = _classify_chat_intent(parsed_bet.original_message, parsed_bet)

    if chat_intent == "chasing_loss_request":
        response = """No intentaría recuperarlo con otra apuesta. Ese es justo el momento en el que el stake se desordena.

La jugada útil es resetear: parar, limitar la siguiente posición a algo simbólico y revisar solo apuestas que seguirían teniendo sentido aunque no fueras perdiendo. Pásame partido y cuota y la juzgo en frío, no como apuesta para remontar.

Confianza: 6/10"""
        return AIChatResult(response=_ensure_user_name_in_response(response, user_name), confidence_score=6.0, verdict="AVOID", implied_probability=None, stake_posture="avoid", recommended_stake=1)

    if chat_intent == "cash_out_request":
        response = """Te puedo ayudar, pero el cash out necesita estado actual. Pásame stake inicial, cuota original, marcador/minuto y oferta de cash out.

Regla rápida: cerraría solo si la oferta es mejor que el valor justo actual o si reducir varianza te importa más que exprimir EV. Sin esos números, no lo adivinaría.

Confianza: 4/10"""
        return AIChatResult(response=_ensure_user_name_in_response(response, user_name), confidence_score=4.0, verdict="NOT ENOUGH INFO", implied_probability=None, stake_posture="avoid", recommended_stake=1)

    if chat_intent == "education_request":
        response = """Versión rápida: la cuota te dice el pago y la probabilidad mínima para empatar; el stake es el tamaño sugerido por Matchmind del 1 al 10.

Ejemplo: cuota 2.00 implica más o menos 50%. Stake 3/10 significa pequeño pero razonable; no significa que la apuesta tenga un 30% de probabilidad. Pásame una apuesta real y te traduzco los números a un veredicto claro.

Confianza: 7/10"""
        return AIChatResult(response=_ensure_user_name_in_response(response, user_name), confidence_score=7.0, verdict="NOT ENOUGH INFO", implied_probability=None, stake_posture="avoid", recommended_stake=1)

    if not parsed_bet.teams and chat_intent in BROAD_DISCOVERY_INTENTS:
        verdict = "NOT ENOUGH INFO"
        stake_posture = "avoid"
        confidence_score = 4.0
        amount_text = f"{parsed_bet.stake_amount:g} {parsed_bet.stake_currency}" if parsed_bet.stake_amount else "ese dinero"
        response = f"""Yo no pondría {amount_text} al azar, pero tampoco deberías tener que salir de Matchmind para empezar. Lo útil es convertir el Feed, las cuotas y las señales de mercado de la app en una lista corta de entradas controladas antes de poner dinero.

La forma práctica de empezar es elegir perfil de riesgo. Conservador: 1-2 posiciones pequeñas y muchas apuestas descartadas. Equilibrado: una shortlist dentro de la app con 3-5 apuestas para revisar. Agresivo: cuotas más largas, pero con importes muy pequeños porque el Mundial tiene mucha varianza.

Dime conservador, equilibrado o agresivo y trabajo desde los partidos y señales que Matchmind ya tiene. Hasta entonces, postura de stake: evitar; el presupuesto ayuda cuando ya hay un precio concreto que juzgar.

Confianza: {confidence_score:g}/10"""
        response = _ensure_user_name_in_response(response, user_name)
        return AIChatResult(
            response=response,
            confidence_score=confidence_score,
            verdict=verdict,
            implied_probability=None,
            stake_posture=stake_posture,
            recommended_stake=1,
        )

    if not parsed_bet.teams:
        verdict = "NOT ENOUGH INFO"
        visible_verdict = "NO HAY INFO SUFICIENTE"
        stake_posture = "avoid"
        visible_posture = "evitar"
        recommended_stake = 1
        confidence_score = 3.0
        my_take = "No puedo darte una lectura útil todavía porque no sé el equipo, partido o mercado exacto. Pásame la selección y la cuota, y te digo si el precio merece la pena."
        value_judgment = "No hay información suficiente."
    elif parsed_bet.odds is None:
        verdict = "NOT ENOUGH INFO"
        visible_verdict = "NO HAY INFO SUFICIENTE"
        stake_posture = "avoid"
        visible_posture = "evitar"
        recommended_stake = 1
        confidence_score = 4.0
        my_take = f"Veo la idea sobre {bet_target}, pero no juzgaría valor sin la cuota. La misma opinión futbolística puede ser buena a un precio y mala a otro."
        value_judgment = "No hay información suficiente sin la cuota."
    elif parsed_bet.odds <= 1.40:
        verdict = "FAIR"
        visible_verdict = "JUSTA / NEUTRAL"
        stake_posture = "small"
        visible_posture = "pequeño"
        recommended_stake = 3
        confidence_score = 5.5
        my_take = f"Esta cuota es baja para {bet_target}, pero puede seguir siendo una buena apuesta controlada. A {parsed_bet.odds:.2f}, necesitas que salga más del {parsed_bet.implied_probability * 100:.1f}% de las veces solo para empatar, así que la trataría como posición de favorito, no como gran oportunidad de value."
        value_judgment = "Razonable como apuesta pequeña y controlada si la diferencia entre equipos es clara; no es value fuerte sin datos en vivo más sólidos."
    elif parsed_bet.odds >= 6.00:
        verdict = "RISKY"
        visible_verdict = "ARRIESGADA"
        stake_posture = "very small"
        visible_posture = "muy pequeño"
        recommended_stake = 2
        confidence_score = 5.0
        my_take = f"Esto es una posición de mucha varianza sobre {bet_target}. La cuota puede ser divertida, pero necesito comparación de mercado y contexto del torneo antes de verla como algo más que un tiro pequeño."
        value_judgment = "Usable solo como apuesta mínima por diversión o precio para vigilar hasta que los datos respalden más."
    else:
        verdict = "FAIR"
        visible_verdict = "JUSTA / NEUTRAL"
        stake_posture = "small"
        visible_posture = "pequeño"
        recommended_stake = 3
        confidence_score = 5.5
        my_take = f"La apuesta sobre {bet_target} se entiende como posición pequeña y controlada. Sin cuotas en vivo, noticias del equipo y comparación de mercado no la llamaría value claro, pero como idea razonable tiene sentido."
        value_judgment = "Justa como entrada pequeña o precio para vigilar, con margen de mejorar si la comparación de mercado acompaña."

    response = f"""Resumen rápido: {visible_verdict}. {my_take}

Con la cuota que me das, el precio es {odds_text} y la probabilidad implícita es {probability_text}. Mi lectura de valor: {value_judgment}

La gran cautela es que no tengo datos en vivo de casas de apuestas, alineaciones, lesiones ni señales de mercado en este análisis de respaldo. Postura de stake: {visible_posture}; entrada controlada, sin subir importe por lealtad, emoción o por intentar recuperar.

Confianza: {confidence_score:g}/10"""
    response = _ensure_user_name_in_response(response, user_name)

    return AIChatResult(
        response=response,
        confidence_score=confidence_score,
        verdict=verdict,
        implied_probability=parsed_bet.implied_probability,
        stake_posture=stake_posture,
        recommended_stake=recommended_stake,
    )


async def generate_chat_reply(
    message: str,
    match_context: dict[str, Any] | None = None,
    polymarket_context: dict[str, Any] | None = None,
    bookmaker_context: dict[str, Any] | None = None,
    preferred_language: str | None = None,
    conversation_memory: list[dict[str, Any]] | None = None,
    user_name: str | None = None,
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
                    user_name,
                ),
            },
        ],
        temperature=0.55,
    )
    content = completion.choices[0].message.content or "{}"
    result = _extract_json(content)
    return _finalize_result(result, parsed_bet, user_name=user_name)
