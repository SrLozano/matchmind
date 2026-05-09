"use client"

import { createContext, useContext, useEffect, useMemo, useState } from "react"
import type { ReactNode } from "react"

export type Language = "en" | "es"

const LANGUAGE_STORAGE_KEY = "matchmind-language"

export const translations = {
  en: {
    nav: {
      aria: "Main navigation",
      picks: "Picks",
      coach: "Coach",
      tracker: "Tracker",
      profile: "Profile",
    },
    feed: {
      title: "Match Radar",
      upcoming: "Upcoming",
      free: "Free",
      pro: "Pro",
      datePending: "Date pending",
      tbd: "TBD",
      freeInsight: "Free match insight",
      coachAvailable: "Coach analysis is available for this match.",
      unlockedFixture: "Fixture unlocked. Confidence and edge will appear here when market data is attached.",
      confidence: "Confidence",
      open: "Open",
      edge: "edge",
      proInsight: "Pro insight available",
      lockedCopy: "Unlock the pick, confidence score, market edge, and coach take.",
      locked: "Locked",
      unavailable: "Match radar is unavailable",
      retry: "Retry",
      emptyTitle: "No matches loaded yet",
      emptyCopy: "The radar will fill in as soon as World Cup fixtures are available.",
      liveFixtureList: "Live fixture list",
      updated: "Updated",
      loadError: "Unable to load matches.",
    },
    chat: {
      title: "BetCoach AI",
      status: "Online · World Cup 2026 expert",
      dailyLimit: "5 chats/day",
      left: "left",
      initialCoach: "Hey! Tell me about the bet you're thinking of placing. I'll give you my honest take.",
      initialUser: "I'm thinking of betting €20 on Spain to win Group A at 1.8 odds",
      initialAnalysis:
        "Good question. Let me break this down for you:\n\n**Bookmaker odds:** 1.80 (implied prob: 55.6%)\n**Crowd probability:** ~64% (fair odds: ~1.56)\n\nThe book is offering you worse value than the broader market signal suggests, meaning the crowd thinks Spain is more likely to win than the bookmaker's price implies. That's a divergence working in your favour.\n\nHowever, Spain face Morocco and Japan in Group A. Morocco are dangerous at home-continent odds and Japan are historically solid. The 1.80 price is stingy for what's a real risk group.\n\n**My recommendation: Pass or reduce stake.** If you must play, €10 max at these odds. Wait for post-matchday 1 odds which may open up.\n\n**Confidence score: 6/10**",
      pending: "Checking the bet and building a straight answer...",
      requestFailed: "I couldn't complete that request.",
      reachError: "Unable to reach the Matchmind coach.",
      placeholder: "Ask about any World Cup bet...",
      send: "Send message",
      disclaimer: "For entertainment purposes only. Always bet responsibly.",
      marketSignal: "Market signal",
      noMarketSignal: "No useful market signal was found for this bet.",
      crowdProbability: "Crowd prob.",
      liquidity: "Liquidity",
      market: "Market",
      quality: "Quality",
    },
    tracker: {
      title: "Bet Tracker",
      subtitle: "World Cup 2026 · All bets",
      logBet: "Log Bet",
      totalBets: "Total Bets",
      winRate: "Win Rate",
      stake: "Stake",
      odds: "Odds",
      date: "Date",
      won: "Won",
      lost: "Lost",
      live: "Live",
      pending: "Pending",
      loading: "Loading bets...",
      unavailable: "Tracker unavailable",
      emptyTitle: "No bets logged yet",
      emptyCopy: "Your World Cup betting record will appear here as soon as you add the first one.",
      betDescription: "Bet description",
      betPlaceholder: "Spain vs Germany - Spain win",
      saveBet: "Save bet",
      cancel: "Cancel",
      settle: "Settle",
      delete: "Delete",
      markWin: "Win",
      markLoss: "Loss",
      saving: "Saving...",
      vs: "vs",
      matches: {
        portugalCzechia: "Portugal vs. Czech Republic",
        usaMexico: "USA vs. Mexico",
        englandSerbia: "England vs. Serbia",
        japanColombia: "Japan vs. Colombia",
      },
      markets: {
        portugalWin: "Portugal Win",
        bothTeamsScore: "Both Teams Score",
        englandHandicap: "England -1 AH",
        underGoals: "Under 2.5 Goals",
      },
      dates: {
        jun14: "Jun 14",
        jun15: "Jun 15",
        jun16: "Jun 16",
        jun17: "Jun 17",
      },
    },
    profile: {
      title: "Profile",
      freePlan: "Free Plan",
      editProfile: "Edit profile",
      dailyChats: "Daily AI Chats",
      resets: "Resets midnight UTC",
      remaining: "2 chats remaining today",
      pass: "World Cup Pass",
      oneTime: "one time",
      unlock: "Unlock Every Pick for the Full Tournament",
      upgrade: "Upgrade Now · €9.99",
      stripe: "Powered by Stripe · Secure checkout · No subscription",
      notificationSettings: "Notification Settings",
      notificationCopy: "Choose how Matchmind talks to you.",
      language: "Language",
      english: "English",
      spanish: "Español",
      responsibleGambling: "Responsible Gambling",
      help: "Help & Support",
      privacy: "Privacy Policy",
      features: [
        "Unlimited AI Coach chats",
        "Full market divergence feed",
        "All 48 group stage match picks",
        "Knockout bracket predictions",
        "Live odds movement alerts",
      ],
    },
  },
  es: {
    nav: {
      aria: "Navegación principal",
      picks: "Pronósticos",
      coach: "Coach",
      tracker: "Registro",
      profile: "Perfil",
    },
    feed: {
      title: "Radar de Partidos",
      upcoming: "Próximos",
      free: "Gratis",
      pro: "Pro",
      datePending: "Fecha pendiente",
      tbd: "Pend.",
      freeInsight: "Análisis gratuito",
      coachAvailable: "El análisis del coach está disponible para este partido.",
      unlockedFixture: "Partido desbloqueado. La confianza y el edge aparecerán cuando haya datos de mercado.",
      confidence: "Confianza",
      open: "Abierto",
      edge: "ventaja",
      proInsight: "Análisis Pro disponible",
      lockedCopy: "Desbloquea el pick, la confianza, el edge de mercado y la lectura del coach.",
      locked: "Bloqueado",
      unavailable: "El radar no está disponible",
      retry: "Reintentar",
      emptyTitle: "Aún no hay partidos cargados",
      emptyCopy: "El radar se llenará en cuanto estén disponibles los partidos del Mundial.",
      liveFixtureList: "Lista de partidos en vivo",
      updated: "Actualizado",
      loadError: "No se pudieron cargar los partidos.",
    },
    chat: {
      title: "BetCoach AI",
      status: "En línea · Experto Mundial 2026",
      dailyLimit: "5 chats/día",
      left: "restantes",
      initialCoach: "¡Ey! Cuéntame qué apuesta estás pensando hacer y te doy mi opinión honesta.",
      initialUser: "Estoy pensando en apostar 20€ a que España gana el Grupo A a cuota 1.8",
      initialAnalysis:
        "Buena pregunta. Te lo desgloso:\n\n**Cuota de la casa:** 1.80 (prob. implícita: 55.6%)\n**Probabilidad de mercado:** ~64% (cuota justa: ~1.56)\n\nLa casa te ofrece peor valor de lo que sugiere la señal agregada de mercado, es decir, la gente cree que España tiene más opciones de ganar de lo que implica esa cuota. Esa divergencia juega a tu favor.\n\nAun así, España se enfrenta a Marruecos y Japón en el Grupo A. Marruecos es peligroso y Japón suele competir muy bien. La cuota 1.80 es algo corta para un grupo con riesgo real.\n\n**Mi recomendación: pasar o bajar stake.** Si entras, máximo 10€ a estas cuotas. Esperaría a después de la primera jornada por si se abre el precio.\n\n**Confianza: 6/10**",
      pending: "Revisando la apuesta y preparando una respuesta directa...",
      requestFailed: "No pude completar esa petición.",
      reachError: "No se pudo contactar con el coach de Matchmind.",
      placeholder: "Pregunta por cualquier apuesta del Mundial...",
      send: "Enviar mensaje",
      disclaimer: "Solo con fines de entretenimiento. Apuesta siempre con responsabilidad.",
      marketSignal: "Señal de mercado",
      noMarketSignal: "No se encontró una señal útil de mercado para esta apuesta.",
      crowdProbability: "Prob. mercado",
      liquidity: "Liquidez",
      market: "Mercado",
      quality: "Calidad",
    },
    tracker: {
      title: "Registro de Apuestas",
      subtitle: "Mundial 2026 · Todas las apuestas",
      logBet: "Añadir",
      totalBets: "Apuestas",
      winRate: "Acierto",
      stake: "Importe",
      odds: "Cuota",
      date: "Fecha",
      won: "Ganada",
      lost: "Perdida",
      live: "En vivo",
      pending: "Pendiente",
      loading: "Cargando apuestas...",
      unavailable: "Registro no disponible",
      emptyTitle: "Aún no hay apuestas",
      emptyCopy: "Tu registro del Mundial aparecerá aquí cuando añadas la primera apuesta.",
      betDescription: "Descripción de la apuesta",
      betPlaceholder: "España vs Alemania - gana España",
      saveBet: "Guardar apuesta",
      cancel: "Cancelar",
      settle: "Resolver",
      delete: "Borrar",
      markWin: "Ganada",
      markLoss: "Perdida",
      saving: "Guardando...",
      vs: "vs",
      matches: {
        portugalCzechia: "Portugal vs. Chequia",
        usaMexico: "EE. UU. vs. México",
        englandSerbia: "Inglaterra vs. Serbia",
        japanColombia: "Japón vs. Colombia",
      },
      markets: {
        portugalWin: "Gana Portugal",
        bothTeamsScore: "Ambos marcan",
        englandHandicap: "Inglaterra -1 HA",
        underGoals: "Menos de 2.5 goles",
      },
      dates: {
        jun14: "14 jun",
        jun15: "15 jun",
        jun16: "16 jun",
        jun17: "17 jun",
      },
    },
    profile: {
      title: "Perfil",
      freePlan: "Plan Gratis",
      editProfile: "Editar perfil",
      dailyChats: "Chats IA diarios",
      resets: "Reinicia a medianoche UTC",
      remaining: "2 chats restantes hoy",
      pass: "Pase Mundial",
      oneTime: "pago único",
      unlock: "Desbloquea todos los picks del torneo",
      upgrade: "Mejorar ahora · €9.99",
      stripe: "Con Stripe · Pago seguro · Sin suscripción",
      notificationSettings: "Ajustes de notificaciones",
      notificationCopy: "Elige cómo quieres que Matchmind te hable.",
      language: "Idioma",
      english: "English",
      spanish: "Español",
      responsibleGambling: "Juego responsable",
      help: "Ayuda y soporte",
      privacy: "Política de privacidad",
      features: [
        "Chats ilimitados con el coach IA",
        "Feed completo de divergencias de mercado",
        "Picks de los 48 partidos de fase de grupos",
        "Predicciones del cuadro eliminatorio",
        "Alertas de movimiento de cuotas en vivo",
      ],
    },
  },
} as const

type Translation = (typeof translations)[Language]

type LanguageContextValue = {
  language: Language
  setLanguage: (language: Language) => void
  t: Translation
}

const LanguageContext = createContext<LanguageContextValue | null>(null)

function isLanguage(value: string | null): value is Language {
  return value === "en" || value === "es"
}

export function LanguageProvider({ children }: { children: ReactNode }) {
  const [language, setLanguageState] = useState<Language>("en")

  useEffect(() => {
    const storedLanguage = window.localStorage.getItem(LANGUAGE_STORAGE_KEY)
    if (isLanguage(storedLanguage)) {
      setLanguageState(storedLanguage)
    }
  }, [])

  const setLanguage = (nextLanguage: Language) => {
    setLanguageState(nextLanguage)
    window.localStorage.setItem(LANGUAGE_STORAGE_KEY, nextLanguage)
  }

  const value = useMemo(
    () => ({
      language,
      setLanguage,
      t: translations[language],
    }),
    [language]
  )

  return <LanguageContext.Provider value={value}>{children}</LanguageContext.Provider>
}

export function useLanguage() {
  const context = useContext(LanguageContext)
  if (!context) {
    throw new Error("useLanguage must be used within LanguageProvider")
  }
  return context
}
