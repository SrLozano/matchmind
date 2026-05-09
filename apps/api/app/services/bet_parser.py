from __future__ import annotations

import re
from pydantic import BaseModel, Field

from app.services.world_cup_teams import team_aliases_by_canonical


TEAM_ALIASES: dict[str, tuple[str, ...]] = team_aliases_by_canonical()

MARKET_PATTERNS: list[tuple[str, str]] = [
    (r"\b(?:over|más\s+de|mas\s+de)\s+\d+(?:[.,]\d+)?\s+(?:goals?|goles)\b", "Over goals"),
    (r"\b(?:under|menos\s+de)\s+\d+(?:[.,]\d+)?\s+(?:goals?|goles)\b", "Under goals"),
    (r"\b[-+]?\d+(?:[.,]\d+)?\s+h[áa]ndicap\b|\bh[áa]ndicap\b|\bhandicap\b", "Handicap"),
    (
        r"\b(?:to\s+win\s+the\s+world\s+cup|win\s+the\s+world\s+cup|ganar\s+(?:el\s+)?mundial|campe[oó]n[ao]?\s+del\s+mundial|gana\s+(?:el\s+)?mundial|ganar\s+(?:la\s+)?copa|gana\s+(?:la\s+)?copa)\b",
        "Tournament outright",
    ),
    (r"\b(?:to\s+beat|beats?|to\s+win|gana|ganar|vence|vencer|derrota|ganador)\b", "Match winner"),
]

SPANISH_HINTS = {
    "apuesto",
    "apostar",
    "apostaría",
    "apostaria",
    "cuota",
    "cuotas",
    "gana",
    "ganar",
    "vence",
    "hándicap",
    "handicap",
    "más",
    "mas",
    "menos",
    "goles",
    "mundial",
    "campeón",
    "campeon",
    "pienso",
    "meter",
    "poner",
    "valor",
}


class ParsedBet(BaseModel):
    original_message: str
    detected_language: str = "en"
    teams: list[str] = Field(default_factory=list)
    raw_match_text: str | None = None
    market_type: str | None = None
    odds: float | None = None
    implied_probability: float | None = Field(default=None, ge=0, le=1)
    stake_amount: float | None = None
    stake_currency: str | None = None
    needs_clarification: bool = False
    missing_fields: list[str] = Field(default_factory=list)


def parse_bet_message(message: str) -> ParsedBet:
    normalized = " ".join(message.strip().split())
    detected_language = _detect_language(normalized)
    odds = _extract_decimal_odds(normalized)
    team_matches = _extract_team_matches(normalized)
    teams = [team for _, team, _ in team_matches]
    stake_amount, stake_currency = _extract_stake(normalized)
    market_type = _extract_market_type(normalized)
    raw_match_text = _extract_raw_match_text(normalized, team_matches)
    missing_fields = _missing_fields(teams, odds, market_type, normalized)

    return ParsedBet(
        original_message=message,
        detected_language=detected_language,
        teams=teams,
        raw_match_text=raw_match_text,
        market_type=market_type,
        odds=odds,
        implied_probability=round(1 / odds, 4) if odds else None,
        stake_amount=stake_amount,
        stake_currency=stake_currency,
        needs_clarification="teams" in missing_fields,
        missing_fields=missing_fields,
    )


def _extract_decimal_odds(message: str) -> float | None:
    priority_patterns = [
        r"(?:odds|cuotas?|at|@|priced\s+at|price\s+of|a)\s*(\d{1,2}[.,]\d{2})\b",
        r"\b(\d{1,2}[.,]\d{2})\s*(?:odds|price|cuotas?)\b",
    ]
    for pattern in priority_patterns:
        match = re.search(pattern, message, re.IGNORECASE)
        if match:
            return _valid_decimal_odd(match.group(1))

    for match in re.finditer(r"(?<![€$£])(?<!\d)(\d{1,2}[.,]\d{2})(?!\d|%)", message):
        odd = _valid_decimal_odd(match.group(1))
        if odd:
            return odd
    return None


def _valid_decimal_odd(value: str) -> float | None:
    odd = float(value.replace(",", "."))
    if 1.01 <= odd <= 50:
        return odd
    return None


def _extract_stake(message: str) -> tuple[float | None, str | None]:
    patterns = [
        r"(?P<currency>€|\$|£)\s*(?P<amount>\d+(?:[.,]\d{1,2})?)",
        r"(?P<amount>\d+(?:[.,]\d{1,2})?)\s*(?P<currency>€|\$|£|eur|euro|euros|usd|dollars?|gbp|pounds?)(?!\w)",
        r"\b(?:stake|bet|putting|put|apuesto|apostar|meter|meto|poner|pongo)\s+(?P<amount>\d+(?:[.,]\d{1,2})?)\b",
    ]
    for pattern in patterns:
        match = re.search(pattern, message, re.IGNORECASE)
        if match:
            currency = match.groupdict().get("currency")
            amount = float(match.group("amount").replace(",", "."))
            return amount, _normalize_currency(currency)
    return None, None


def _normalize_currency(currency: str | None) -> str | None:
    if not currency:
        return None
    value = currency.lower()
    if value in {"€", "eur", "euro", "euros"}:
        return "EUR"
    if value in {"$", "usd", "dollar", "dollars"}:
        return "USD"
    if value in {"£", "gbp", "pound", "pounds"}:
        return "GBP"
    return currency


def _extract_teams(message: str) -> list[str]:
    return [team for _, team, _ in _extract_team_matches(message)]


def _extract_team_matches(message: str) -> list[tuple[int, str, str]]:
    found: list[tuple[int, str, str]] = []
    for canonical_team, aliases in TEAM_ALIASES.items():
        team_matches = [
            (match.start(), canonical_team, match.group(0))
            for alias in aliases
            if (match := re.search(rf"(?<!\w){re.escape(alias)}(?!\w)", message, re.IGNORECASE))
        ]
        if team_matches:
            found.append(min(team_matches))
    return sorted(found)


def _extract_market_type(message: str) -> str | None:
    for pattern, market_type in MARKET_PATTERNS:
        if re.search(pattern, message, re.IGNORECASE):
            return market_type
    return None


def _extract_raw_match_text(message: str, team_matches: list[tuple[int, str, str]]) -> str | None:
    if len(team_matches) >= 2:
        return f"{team_matches[0][2]} vs {team_matches[1][2]}"
    if len(team_matches) == 1:
        return team_matches[0][2]
    versus = re.search(
        r"\b([A-Za-zÁÉÍÓÚÜÑáéíóúüñ ]{2,30})\s+(?:vs|v|versus|against|contra)\s+([A-Za-zÁÉÍÓÚÜÑáéíóúüñ ]{2,30}?)(?=\s+(?:at|odds|cuotas?|@|a)\b|[?,.]|$)",
        message,
        re.IGNORECASE,
    )
    if versus:
        return f"{versus.group(1).strip()} vs {versus.group(2).strip()}"
    return None


def _missing_fields(teams: list[str], odds: float | None, market_type: str | None, message: str) -> list[str]:
    missing: list[str] = []
    if not teams:
        missing.append("teams")
    if odds is None:
        missing.append("odds")
    if market_type is None and not re.search(r"\b\d{1,2}[.,]\d{2}\b", message):
        missing.append("market_type")
    return missing


def _detect_language(message: str) -> str:
    lowered = message.lower()
    if any(char in lowered for char in "áéíóúüñ¿¡"):
        return "es"
    tokens = set(re.findall(r"\b[\wáéíóúüñ]+\b", lowered, re.IGNORECASE))
    if tokens & SPANISH_HINTS:
        return "es"
    for aliases in TEAM_ALIASES.values():
        if any(alias.lower() in lowered for alias in aliases if alias != aliases[0]):
            return "es"
    return "en"
