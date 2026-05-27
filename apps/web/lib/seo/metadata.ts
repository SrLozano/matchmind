import type { MetadataRoute } from "next"

const fallbackBaseUrl = "https://trymatchmind.com"

export const siteUrl = normalizeSiteUrl(process.env.NEXT_PUBLIC_APP_URL)

export const siteConfig = {
  name: "Matchmind",
  shortName: "Matchmind",
  url: siteUrl,
  locale: "en_US",
  alternateLocale: "es_ES",
  title: "Matchmind - AI World Cup 2026 Betting Coach",
  description:
    "Ask an AI betting coach before you bet on the 2026 FIFA World Cup. Matchmind combines bookmaker odds, match context, market signals, and your bet history.",
  spanishDescription:
    "Pregunta a un coach IA antes de apostar en el Mundial 2026. Matchmind combina cuotas, contexto de partidos, señales de mercado y tu historial.",
  keywords: [
    "Matchmind",
    "World Cup 2026",
    "FIFA World Cup betting analysis",
    "AI betting coach",
    "football odds analyzer",
    "prediction market signals",
    "Polymarket World Cup",
    "bet tracker",
  ],
  creator: "Matchmind",
  themeColor: "#00FF87",
  backgroundColor: "#070D1A",
  ogImage: "/og-image.png",
  ogImageAlt: "Matchmind AI betting coach preview for the 2026 FIFA World Cup",
  twitterImage: "/twitter-image.png",
}

export const publicRoutes: MetadataRoute.Sitemap = [
  {
    url: siteConfig.url,
    lastModified: new Date("2026-05-23"),
    changeFrequency: "daily",
    priority: 1,
  },
  {
    url: absoluteUrl("/legal/terms"),
    lastModified: new Date("2026-05-27"),
    changeFrequency: "monthly",
    priority: 0.4,
  },
  {
    url: absoluteUrl("/legal/privacy"),
    lastModified: new Date("2026-05-27"),
    changeFrequency: "monthly",
    priority: 0.4,
  },
  {
    url: absoluteUrl("/legal/responsible-use"),
    lastModified: new Date("2026-05-27"),
    changeFrequency: "monthly",
    priority: 0.4,
  },
  {
    url: absoluteUrl("/es/legal/terms"),
    lastModified: new Date("2026-05-27"),
    changeFrequency: "monthly",
    priority: 0.4,
  },
  {
    url: absoluteUrl("/es/legal/privacy"),
    lastModified: new Date("2026-05-27"),
    changeFrequency: "monthly",
    priority: 0.4,
  },
  {
    url: absoluteUrl("/es/legal/responsible-use"),
    lastModified: new Date("2026-05-27"),
    changeFrequency: "monthly",
    priority: 0.4,
  },
]

export function absoluteUrl(path = "/") {
  return new URL(path, siteConfig.url).toString()
}

export function normalizeSiteUrl(value?: string) {
  if (!value?.trim()) return fallbackBaseUrl

  try {
    const url = new URL(value)
    return url.origin
  } catch {
    return fallbackBaseUrl
  }
}
