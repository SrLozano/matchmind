"use client"

import { Lock, TrendingUp, Clock } from "lucide-react"

const matches = [
  {
    id: 1,
    teamA: { name: "Spain", flag: "🇪🇸" },
    teamB: { name: "Morocco", flag: "🇲🇦" },
    time: "18:00 UTC · Group B",
    divergence: "+14%",
    divergenceLabel: "Polymarket",
    valueSignal: "green" as const,
    valueLabel: "Strong Value",
    bookmakerOdds: "2.10",
    polymarketOdds: "2.45",
    premium: false,
  },
  {
    id: 2,
    teamA: { name: "Brazil", flag: "🇧🇷" },
    teamB: { name: "Argentina", flag: "🇦🇷" },
    time: "21:00 UTC · Group C",
    divergence: "+6%",
    divergenceLabel: "Polymarket",
    valueSignal: "yellow" as const,
    valueLabel: "Neutral",
    bookmakerOdds: "1.95",
    polymarketOdds: "2.07",
    premium: false,
  },
  {
    id: 3,
    teamA: { name: "France", flag: "🇫🇷" },
    teamB: { name: "Germany", flag: "🇩🇪" },
    time: "15:00 UTC · Group D",
    divergence: "-8%",
    divergenceLabel: "Polymarket",
    valueSignal: "red" as const,
    valueLabel: "Avoid",
    bookmakerOdds: "1.75",
    polymarketOdds: "1.61",
    premium: true,
  },
]

const signalConfig = {
  green: {
    dot: "bg-[#00FF87]",
    badge: "bg-[#00FF87]/15 text-[#00FF87] border border-[#00FF87]/30",
    glow: "shadow-[0_0_12px_rgba(0,255,135,0.2)]",
    bar: "bg-[#00FF87]",
  },
  yellow: {
    dot: "bg-[#FFD600]",
    badge: "bg-[#FFD600]/15 text-[#FFD600] border border-[#FFD600]/30",
    glow: "shadow-[0_0_12px_rgba(255,214,0,0.1)]",
    bar: "bg-[#FFD600]",
  },
  red: {
    dot: "bg-[#FF4D4D]",
    badge: "bg-[#FF4D4D]/15 text-[#FF4D4D] border border-[#FF4D4D]/30",
    glow: "shadow-[0_0_12px_rgba(255,77,77,0.1)]",
    bar: "bg-[#FF4D4D]",
  },
}

const today = new Date().toLocaleDateString("en-US", {
  weekday: "long",
  month: "long",
  day: "numeric",
})

export default function DailyFeed() {
  return (
    <div className="flex flex-col h-full overflow-y-auto">
      {/* Header */}
      <div className="px-5 pt-6 pb-4 flex-shrink-0">
        <p className="text-xs font-medium tracking-widest uppercase text-[#6A7A9B] mb-1">
          {today}
        </p>
        <h1 className="text-2xl font-bold text-foreground tracking-tight">
          Today&apos;s Picks
        </h1>
        <div className="flex items-center gap-2 mt-2">
          <div className="w-1.5 h-1.5 rounded-full bg-[#00FF87] animate-pulse" />
          <span className="text-xs text-[#6A7A9B]">Live analysis · Updated 2 min ago</span>
        </div>
      </div>

      {/* Stat bar */}
      <div className="mx-5 mb-5 flex-shrink-0 rounded-xl bg-[#0F1C35] border border-[#1A2845] p-3 flex items-center justify-between">
        <div className="text-center">
          <p className="text-[10px] uppercase tracking-wider text-[#6A7A9B] mb-0.5">Picks Today</p>
          <p className="text-lg font-bold text-foreground">3</p>
        </div>
        <div className="w-px h-8 bg-[#1A2845]" />
        <div className="text-center">
          <p className="text-[10px] uppercase tracking-wider text-[#6A7A9B] mb-0.5">Avg Edge</p>
          <p className="text-lg font-bold text-[#00FF87]">+9.3%</p>
        </div>
        <div className="w-px h-8 bg-[#1A2845]" />
        <div className="text-center">
          <p className="text-[10px] uppercase tracking-wider text-[#6A7A9B] mb-0.5">Win Rate</p>
          <p className="text-lg font-bold text-foreground">67%</p>
        </div>
      </div>

      {/* Match cards */}
      <div className="px-5 flex flex-col gap-4 pb-6">
        {matches.map((match) => {
          const cfg = signalConfig[match.valueSignal]
          return (
            <div
              key={match.id}
              className={`relative rounded-2xl bg-card border border-[#1A2845] overflow-hidden ${cfg.glow}`}
            >
              {/* Left accent bar */}
              <div className={`absolute left-0 top-0 bottom-0 w-1 ${cfg.bar}`} />

              {/* Premium overlay */}
              {match.premium && (
                <div className="absolute inset-0 bg-[#070D1A]/70 backdrop-blur-[2px] z-10 flex flex-col items-center justify-center gap-2 rounded-2xl">
                  <div className="flex items-center gap-2 bg-[#FFD600]/10 border border-[#FFD600]/30 rounded-full px-4 py-2">
                    <Lock className="w-4 h-4 text-[#FFD600]" />
                    <span className="text-xs font-semibold text-[#FFD600] tracking-wider uppercase">Premium Pick</span>
                  </div>
                  <p className="text-xs text-[#6A7A9B]">Upgrade to unlock all picks</p>
                </div>
              )}

              <div className="pl-5 pr-4 pt-4 pb-3">
                {/* Teams row */}
                <div className="flex items-center justify-between mb-3">
                  <div className="flex flex-col gap-2">
                    <div className="flex items-center gap-2.5">
                      <span className="text-xl">{match.teamA.flag}</span>
                      <span className="text-sm font-semibold text-foreground">{match.teamA.name}</span>
                    </div>
                    <div className="flex items-center gap-2.5">
                      <span className="text-xl">{match.teamB.flag}</span>
                      <span className="text-sm font-semibold text-foreground">{match.teamB.name}</span>
                    </div>
                  </div>

                  {/* Divergence badge */}
                  <div className="flex flex-col items-end gap-2">
                    <div className={`flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-bold ${cfg.badge}`}>
                      <TrendingUp className="w-3 h-3" />
                      {match.divergence}
                    </div>
                    <span className="text-[10px] text-[#6A7A9B]">{match.divergenceLabel} edge</span>
                  </div>
                </div>

                {/* Footer row */}
                <div className="flex items-center justify-between pt-2.5 border-t border-[#1A2845]">
                  <div className="flex items-center gap-1.5 text-[#6A7A9B]">
                    <Clock className="w-3 h-3" />
                    <span className="text-xs">{match.time}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-[10px] text-[#6A7A9B]">Book: {match.bookmakerOdds}</span>
                    <span className="text-[10px] text-[#6A7A9B]">·</span>
                    <span className="text-[10px] text-[#6A7A9B]">PM: {match.polymarketOdds}</span>
                    <div className={`flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-semibold ${cfg.badge}`}>
                      <div className={`w-1.5 h-1.5 rounded-full ${cfg.dot}`} />
                      {match.valueLabel}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
