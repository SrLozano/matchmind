const flagByTeamName: Record<string, string> = {
  Algeria: "🇩🇿",
  Argentina: "🇦🇷",
  Australia: "🇦🇺",
  Austria: "🇦🇹",
  Belgium: "🇧🇪",
  "Bosnia and Herzegovina": "🇧🇦",
  "Bosnia-Herzegovina": "🇧🇦",
  Brazil: "🇧🇷",
  "Cape Verde": "🇨🇻",
  "Cabo Verde": "🇨🇻",
  Canada: "🇨🇦",
  Chile: "🇨🇱",
  Colombia: "🇨🇴",
  "Costa Rica": "🇨🇷",
  "South Korea": "🇰🇷",
  "Korea Republic": "🇰🇷",
  "Republic of Korea": "🇰🇷",
  "Ivory Coast": "🇨🇮",
  "Côte d'Ivoire": "🇨🇮",
  "Cote d'Ivoire": "🇨🇮",
  Croatia: "🇭🇷",
  Curaçao: "🇨🇼",
  Curacao: "🇨🇼",
  Denmark: "🇩🇰",
  Ecuador: "🇪🇨",
  Egypt: "🇪🇬",
  England: "\u{1F3F4}\u{E0067}\u{E0062}\u{E0065}\u{E006E}\u{E0067}\u{E007F}",
  France: "🇫🇷",
  Germany: "🇩🇪",
  Ghana: "🇬🇭",
  Haiti: "🇭🇹",
  Haïti: "🇭🇹",
  Iran: "🇮🇷",
  Iraq: "🇮🇶",
  Italy: "🇮🇹",
  Jamaica: "🇯🇲",
  Japan: "🇯🇵",
  Jordan: "🇯🇴",
  Mexico: "🇲🇽",
  Morocco: "🇲🇦",
  Netherlands: "🇳🇱",
  Holland: "🇳🇱",
  "New Zealand": "🇳🇿",
  Norway: "🇳🇴",
  Panama: "🇵🇦",
  Paraguay: "🇵🇾",
  Peru: "🇵🇪",
  Poland: "🇵🇱",
  Portugal: "🇵🇹",
  Qatar: "🇶🇦",
  Czechia: "🇨🇿",
  "Czech Republic": "🇨🇿",
  "DR Congo": "🇨🇩",
  "Congo DR": "🇨🇩",
  "Democratic Republic of the Congo": "🇨🇩",
  "Saudi Arabia": "🇸🇦",
  Scotland: "\u{1F3F4}\u{E0067}\u{E0062}\u{E0073}\u{E0063}\u{E0074}\u{E007F}",
  Senegal: "🇸🇳",
  Serbia: "🇷🇸",
  "South Africa": "🇿🇦",
  Spain: "🇪🇸",
  Sweden: "🇸🇪",
  Switzerland: "🇨🇭",
  Turkey: "🇹🇷",
  Türkiye: "🇹🇷",
  Turkiye: "🇹🇷",
  Tunisia: "🇹🇳",
  Ukraine: "🇺🇦",
  "United Arab Emirates": "🇦🇪",
  UAE: "🇦🇪",
  "United States": "🇺🇸",
  USA: "🇺🇸",
  "United States of America": "🇺🇸",
  Uruguay: "🇺🇾",
  Uzbekistan: "🇺🇿",
  Wales: "\u{1F3F4}\u{E0067}\u{E0062}\u{E0077}\u{E006C}\u{E0073}\u{E007F}",
}

const normalizedFlagByTeamName = Object.fromEntries(
  Object.entries(flagByTeamName).map(([team, flag]) => [normalizeTeamName(team), flag])
)

export function flagForTeam(teamName: string) {
  return normalizedFlagByTeamName[normalizeTeamName(teamName)] ?? "⚽"
}

function normalizeTeamName(value: string) {
  return value
    .normalize("NFKD")
    .replace(/\p{Diacritic}/gu, "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, " ")
    .trim()
}
