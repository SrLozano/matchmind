"use client"

import { CheckCircle2, XCircle, Clock3, TrendingUp, TrendingDown, Plus } from "lucide-react"

const bets = [
  {
    id: 1,
    match: "Portugal vs. Czech Republic",
    flags: ["🇵🇹", "🇨🇿"],
    market: "Portugal Win",
    amount: 25,
    odds: 1.65,
    outcome: "win" as const,
    pnl: +16.25,
    date: "Jun 14",
  },
  {
    id: 2,
    match: "USA vs. Mexico",
    flags: ["🇺🇸", "🇲🇽"],
    market: "Both Teams Score",
    amount: 15,
    odds: 1.90,
    outcome: "win" as const,
    pnl: +13.5,
    date: "Jun 15",
  },
  {
    id: 3,
    match: "England vs. Serbia",
    flags: ["🏴󠁧󠁢󠁥󠁮󠁧󠁿", "🇷🇸"],
    market: "England -1 AH",
    amount: 30,
    odds: 2.10,
    outcome: "loss" as const,
    pnl: -30,
    date: "Jun 16",
  },
  {
    id: 4,
    match: "Japan vs. Colombia",
    flags: ["🇯🇵", "🇨🇴"],
    market: "Under 2.5 Goals",
    amount: 20,
    odds: 1.75,
    outcome: "pending" as const,
    pnl: 0,
    date: "Jun 17",
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
    label: "Won",
  },
  loss: {
    icon: XCircle,
    color: "text-[#FF4D4D]",
    bg: "bg-[#FF4D4D]/10 border border-[#FF4D4D]/20",
    label: "Lost",
  },
  pending: {
    icon: Clock3,
    color: "text-[#FFD600]",
    bg: "bg-[#FFD600]/10 border border-[#FFD600]/20",
    label: "Live",
  },
}

export default function BetTracker() {
  return (
    <div className="flex flex-col h-full overflow-y-auto">
      {/* Header */}
      <div className="px-5 pt-6 pb-4 flex-shrink-0 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground tracking-tight">Bet Tracker</h1>
          <p className="text-xs text-[#6A7A9B] mt-0.5">World Cup 2026 · All bets</p>
        </div>
        <button className="flex items-center gap-1.5 bg-[#00FF87]/10 border border-[#00FF87]/30 text-[#00FF87] text-xs font-semibold rounded-xl px-3 py-2 hover:bg-[#00FF87]/20 active:scale-95 transition-all">
          <Plus className="w-3.5 h-3.5" />
          Log Bet
        </button>
      </div>

      {/* Summary bar */}
      <div className="mx-5 mb-5 flex-shrink-0 rounded-2xl bg-[#0F1C35] border border-[#1A2845] p-4">
        <div className="flex items-center justify-between">
          <div className="text-center flex-1">
            <p className="text-[10px] uppercase tracking-wider text-[#6A7A9B] mb-1">Total Bets</p>
            <p className="text-xl font-bold text-foreground">{totalBets}</p>
          </div>
          <div className="w-px h-10 bg-[#1A2845]" />
          <div className="text-center flex-1">
            <p className="text-[10px] uppercase tracking-wider text-[#6A7A9B] mb-1">Win Rate</p>
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
                    <span className="text-xs text-[#6A7A9B]">vs</span>
                    <span className="text-base">{bet.flags[1]}</span>
                  </div>
                  <p className="text-xs font-semibold text-foreground truncate">{bet.match}</p>
                  <p className="text-[11px] text-[#6A7A9B] mt-0.5">{bet.market}</p>
                </div>
                <div className={`flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-semibold flex-shrink-0 ${cfg.bg} ${cfg.color}`}>
                  <Icon className="w-3.5 h-3.5" />
                  {cfg.label}
                </div>
              </div>

              <div className="flex items-center justify-between pt-2.5 border-t border-[#1A2845]">
                <div className="flex items-center gap-3">
                  <div>
                    <p className="text-[10px] text-[#6A7A9B] uppercase tracking-wider">Stake</p>
                    <p className="text-sm font-semibold text-foreground">€{bet.amount}</p>
                  </div>
                  <div className="w-px h-6 bg-[#1A2845]" />
                  <div>
                    <p className="text-[10px] text-[#6A7A9B] uppercase tracking-wider">Odds</p>
                    <p className="text-sm font-semibold text-foreground">{bet.odds}</p>
                  </div>
                  <div className="w-px h-6 bg-[#1A2845]" />
                  <div>
                    <p className="text-[10px] text-[#6A7A9B] uppercase tracking-wider">Date</p>
                    <p className="text-sm font-semibold text-foreground">{bet.date}</p>
                  </div>
                </div>
                <div className="text-right">
                  <p className="text-[10px] text-[#6A7A9B] uppercase tracking-wider">P&amp;L</p>
                  {bet.outcome === "pending" ? (
                    <p className="text-sm font-bold text-[#FFD600]">Pending</p>
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
