"use client"

import { CheckCircle2, XCircle, Clock3, TrendingUp, TrendingDown, Plus } from "lucide-react"
import { useLanguage } from "@/lib/i18n"

const bets = [
  {
    id: 1,
    matchKey: "portugalCzechia" as const,
    flags: ["🇵🇹", "🇨🇿"],
    marketKey: "portugalWin" as const,
    amount: 25,
    odds: 1.65,
    outcome: "win" as const,
    pnl: +16.25,
    dateKey: "jun14" as const,
  },
  {
    id: 2,
    matchKey: "usaMexico" as const,
    flags: ["🇺🇸", "🇲🇽"],
    marketKey: "bothTeamsScore" as const,
    amount: 15,
    odds: 1.90,
    outcome: "win" as const,
    pnl: +13.5,
    dateKey: "jun15" as const,
  },
  {
    id: 3,
    matchKey: "englandSerbia" as const,
    flags: ["🏴󠁧󠁢󠁥󠁮󠁧󠁿", "🇷🇸"],
    marketKey: "englandHandicap" as const,
    amount: 30,
    odds: 2.10,
    outcome: "loss" as const,
    pnl: -30,
    dateKey: "jun16" as const,
  },
  {
    id: 4,
    matchKey: "japanColombia" as const,
    flags: ["🇯🇵", "🇨🇴"],
    marketKey: "underGoals" as const,
    amount: 20,
    odds: 1.75,
    outcome: "pending" as const,
    pnl: 0,
    dateKey: "jun17" as const,
  },
]

const totalBets = bets.length
const wins = bets.filter((b) => b.outcome === "win").length
const settled = bets.filter((b) => b.outcome !== "pending").length
const winRate = settled > 0 ? Math.round((wins / settled) * 100) : 0
const totalPnl = bets.reduce((acc, b) => acc + b.pnl, 0)

const outcomeConfig = {
  win: {
    icon: CheckCircle2,
    color: "text-[#00FF87]",
    bg: "bg-[#00FF87]/10 border border-[#00FF87]/20",
    labelKey: "won" as const,
  },
  loss: {
    icon: XCircle,
    color: "text-[#FF4D4D]",
    bg: "bg-[#FF4D4D]/10 border border-[#FF4D4D]/20",
    labelKey: "lost" as const,
  },
  pending: {
    icon: Clock3,
    color: "text-[#FFD600]",
    bg: "bg-[#FFD600]/10 border border-[#FFD600]/20",
    labelKey: "live" as const,
  },
}

export default function BetTracker() {
  const { t } = useLanguage()

  return (
    <div className="flex flex-col h-full overflow-y-auto">
      {/* Header */}
      <div className="px-5 pt-6 pb-4 flex-shrink-0 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground tracking-tight">{t.tracker.title}</h1>
          <p className="text-xs text-[#6A7A9B] mt-0.5">{t.tracker.subtitle}</p>
        </div>
        <button className="flex items-center gap-1.5 bg-[#00FF87]/10 border border-[#00FF87]/30 text-[#00FF87] text-xs font-semibold rounded-xl px-3 py-2 hover:bg-[#00FF87]/20 active:scale-95 transition-all">
          <Plus className="w-3.5 h-3.5" />
          {t.tracker.logBet}
        </button>
      </div>

      {/* Summary bar */}
      <div className="mx-5 mb-5 flex-shrink-0 rounded-2xl bg-[#0F1C35] border border-[#1A2845] p-4">
        <div className="flex items-center justify-between">
          <div className="text-center flex-1">
            <p className="text-[10px] uppercase tracking-wider text-[#6A7A9B] mb-1">{t.tracker.totalBets}</p>
            <p className="text-xl font-bold text-foreground">{totalBets}</p>
          </div>
          <div className="w-px h-10 bg-[#1A2845]" />
          <div className="text-center flex-1">
            <p className="text-[10px] uppercase tracking-wider text-[#6A7A9B] mb-1">{t.tracker.winRate}</p>
            <p className="text-xl font-bold text-[#00FF87]">{winRate}%</p>
          </div>
          <div className="w-px h-10 bg-[#1A2845]" />
          <div className="text-center flex-1">
            <p className="text-[10px] uppercase tracking-wider text-[#6A7A9B] mb-1">P&amp;L</p>
            <div className="flex items-center justify-center gap-1">
              {totalPnl >= 0 ? (
                <TrendingUp className="w-4 h-4 text-[#00FF87]" />
              ) : (
                <TrendingDown className="w-4 h-4 text-[#FF4D4D]" />
              )}
              <p className={`text-xl font-bold ${totalPnl >= 0 ? "text-[#00FF87]" : "text-[#FF4D4D]"}`}>
                {totalPnl >= 0 ? "+" : ""}€{totalPnl.toFixed(2)}
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Bet list */}
      <div className="px-5 flex flex-col gap-3 pb-6">
        {bets.map((bet) => {
          const cfg = outcomeConfig[bet.outcome]
          const Icon = cfg.icon
          return (
            <div
              key={bet.id}
              className="rounded-2xl bg-card border border-[#1A2845] p-4"
            >
              <div className="flex items-start justify-between gap-3 mb-3">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-1.5 mb-1">
                    <span className="text-base">{bet.flags[0]}</span>
                    <span className="text-xs text-[#6A7A9B]">{t.tracker.vs}</span>
                    <span className="text-base">{bet.flags[1]}</span>
                  </div>
                  <p className="text-xs font-semibold text-foreground truncate">{t.tracker.matches[bet.matchKey]}</p>
                  <p className="text-[11px] text-[#6A7A9B] mt-0.5">{t.tracker.markets[bet.marketKey]}</p>
                </div>
                <div className={`flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-semibold flex-shrink-0 ${cfg.bg} ${cfg.color}`}>
                  <Icon className="w-3.5 h-3.5" />
                  {t.tracker[cfg.labelKey]}
                </div>
              </div>

              <div className="flex items-center justify-between pt-2.5 border-t border-[#1A2845]">
                <div className="flex items-center gap-3">
                  <div>
                    <p className="text-[10px] text-[#6A7A9B] uppercase tracking-wider">{t.tracker.stake}</p>
                    <p className="text-sm font-semibold text-foreground">€{bet.amount}</p>
                  </div>
                  <div className="w-px h-6 bg-[#1A2845]" />
                  <div>
                    <p className="text-[10px] text-[#6A7A9B] uppercase tracking-wider">{t.tracker.odds}</p>
                    <p className="text-sm font-semibold text-foreground">{bet.odds}</p>
                  </div>
                  <div className="w-px h-6 bg-[#1A2845]" />
                  <div>
                    <p className="text-[10px] text-[#6A7A9B] uppercase tracking-wider">{t.tracker.date}</p>
                    <p className="text-sm font-semibold text-foreground">{t.tracker.dates[bet.dateKey]}</p>
                  </div>
                </div>
                <div className="text-right">
                  <p className="text-[10px] text-[#6A7A9B] uppercase tracking-wider">P&amp;L</p>
                  {bet.outcome === "pending" ? (
                    <p className="text-sm font-bold text-[#FFD600]">{t.tracker.pending}</p>
                  ) : (
                    <p className={`text-sm font-bold ${bet.pnl >= 0 ? "text-[#00FF87]" : "text-[#FF4D4D]"}`}>
                      {bet.pnl >= 0 ? "+" : ""}€{bet.pnl.toFixed(2)}
                    </p>
                  )}
                </div>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
