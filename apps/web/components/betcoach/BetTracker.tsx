"use client"

import { FormEvent, useEffect, useMemo, useState } from "react"
import { BarChart3, CheckCircle2, Clock3, Plus, Trash2, TrendingDown, TrendingUp, XCircle } from "lucide-react"

import {
  createTrackedBet,
  deleteTrackedBet,
  getTrackedBets,
  updateTrackedBetOutcome,
  type BetListResponse,
  type BetOutcome,
  type TrackedBet,
} from "@/lib/api"
import { useLanguage } from "@/lib/i18n"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { ConceptTip } from "./ConceptTip"
import SectionHeader from "./SectionHeader"

const emptyTracker: BetListResponse = {
  bets: [],
  summary: {
    total_bets: 0,
    pending_bets: 0,
    wins: 0,
    losses: 0,
    win_rate: 0,
    total_staked: 0,
    profit_loss: 0,
    roi: 0,
  },
}

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

function formatCurrency(value: number) {
  return `${value >= 0 ? "+" : ""}€${Math.abs(value).toFixed(2)}`
}

function formatDate(value: string, locale: string) {
  return new Intl.DateTimeFormat(locale, {
    month: "short",
    day: "numeric",
  }).format(new Date(value))
}

function parseDecimalInput(value: string) {
  return Number(value.replace(",", "."))
}

function recomputeSummary(bets: TrackedBet[]): BetListResponse["summary"] {
  const wins = bets.filter((bet) => bet.outcome === "win").length
  const losses = bets.filter((bet) => bet.outcome === "loss").length
  const pendingBets = bets.filter((bet) => bet.outcome === "pending").length
  const settledBets = wins + losses
  const totalStaked = bets.reduce((sum, bet) => sum + bet.amount, 0)
  const profitLoss = bets.reduce((sum, bet) => sum + bet.profit_loss, 0)

  return {
    total_bets: bets.length,
    pending_bets: pendingBets,
    wins,
    losses,
    win_rate: settledBets > 0 ? wins / settledBets : 0,
    total_staked: Number(totalStaked.toFixed(2)),
    profit_loss: Number(profitLoss.toFixed(2)),
    roi: totalStaked > 0 ? Number((profitLoss / totalStaked).toFixed(4)) : 0,
  }
}

export default function BetTracker() {
  const { language, t } = useLanguage()
  const [tracker, setTracker] = useState<BetListResponse>(emptyTracker)
  const [isLoading, setIsLoading] = useState(true)
  const [isDialogOpen, setIsDialogOpen] = useState(false)
  const [match, setMatch] = useState("")
  const [amount, setAmount] = useState("")
  const [odds, setOdds] = useState("")
  const [error, setError] = useState<string | null>(null)
  const [isSaving, setIsSaving] = useState(false)
  const [activeBetId, setActiveBetId] = useState<string | null>(null)

  const locale = language === "es" ? "es-ES" : "en-US"
  const totalPnl = tracker.summary.profit_loss
  const winRate = Math.round(tracker.summary.win_rate * 100)
  const sortedBets = useMemo(
    () => [...tracker.bets].sort((first, second) => Date.parse(second.created_at) - Date.parse(first.created_at)),
    [tracker.bets],
  )

  useEffect(() => {
    let isMounted = true

    async function loadBets() {
      try {
        setIsLoading(true)
        const data = await getTrackedBets()
        if (isMounted) {
          setTracker(data)
          setError(null)
        }
      } catch (loadError) {
        if (isMounted) {
          setError(loadError instanceof Error ? loadError.message : t.tracker.unavailable)
        }
      } finally {
        if (isMounted) {
          setIsLoading(false)
        }
      }
    }

    void loadBets()

    return () => {
      isMounted = false
    }
  }, [t.tracker.unavailable])

  const refreshTracker = (bets: TrackedBet[]) => {
    setTracker({
      bets,
      summary: recomputeSummary(bets),
    })
  }

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setError(null)

    try {
      setIsSaving(true)
      const createdBet = await createTrackedBet({
        match,
        amount: parseDecimalInput(amount),
        odds: parseDecimalInput(odds),
      })
      refreshTracker([createdBet, ...tracker.bets])
      setMatch("")
      setAmount("")
      setOdds("")
      setIsDialogOpen(false)
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : t.tracker.unavailable)
    } finally {
      setIsSaving(false)
    }
  }

  const handleOutcome = async (betId: string, outcome: BetOutcome) => {
    setError(null)
    setActiveBetId(betId)

    try {
      const updatedBet = await updateTrackedBetOutcome(betId, outcome)
      refreshTracker(tracker.bets.map((bet) => (bet.id === updatedBet.id ? updatedBet : bet)))
    } catch (updateError) {
      setError(updateError instanceof Error ? updateError.message : t.tracker.unavailable)
    } finally {
      setActiveBetId(null)
    }
  }

  const handleDelete = async (betId: string) => {
    setError(null)
    setActiveBetId(betId)

    try {
      await deleteTrackedBet(betId)
      refreshTracker(tracker.bets.filter((bet) => bet.id !== betId))
    } catch (deleteError) {
      setError(deleteError instanceof Error ? deleteError.message : t.tracker.unavailable)
    } finally {
      setActiveBetId(null)
    }
  }

  return (
    <div className="flex h-full flex-col overflow-y-auto">
      <SectionHeader
        icon={BarChart3}
        title={t.tracker.title}
        subtitle={t.tracker.subtitle}
        action={
          <button
            className="flex items-center gap-1.5 rounded-lg border border-[#00FF87]/30 bg-[#00FF87]/10 px-3 py-2 text-xs font-semibold text-[#00FF87] transition-all hover:bg-[#00FF87]/20 active:scale-95"
            type="button"
            onClick={() => setIsDialogOpen(true)}
          >
            <Plus className="h-3.5 w-3.5" />
            {t.tracker.logBet}
          </button>
        }
      />

      <div className="mx-4 mb-4 flex-shrink-0 rounded-lg border border-[#1A2845] bg-[#0F1C35] p-3.5 sm:mx-5">
        <div className="flex items-center justify-between">
          <div className="flex-1 text-center">
            <p className="mb-1 text-[10px] uppercase tracking-wider text-[#6A7A9B]">{t.tracker.totalBets}</p>
            <p className="text-xl font-bold text-foreground">{tracker.summary.total_bets}</p>
          </div>
          <div className="h-10 w-px bg-[#1A2845]" />
          <div className="flex-1 text-center">
            <p className="mb-1 text-[10px] uppercase tracking-wider text-[#6A7A9B]">
              <ConceptTip concept="winRate" label={t.tracker.winRate} subtle />
            </p>
            <p className="text-xl font-bold text-[#00FF87]">{winRate}%</p>
          </div>
          <div className="h-10 w-px bg-[#1A2845]" />
          <div className="flex-1 text-center">
            <p className="mb-1 text-[10px] uppercase tracking-wider text-[#6A7A9B]">
              <ConceptTip concept="pnl" label={t.tracker.profitLoss} subtle />
            </p>
            <div className="flex items-center justify-center gap-1">
              {totalPnl >= 0 ? (
                <TrendingUp className="h-4 w-4 text-[#00FF87]" />
              ) : (
                <TrendingDown className="h-4 w-4 text-[#FF4D4D]" />
              )}
              <p className={`text-xl font-bold ${totalPnl >= 0 ? "text-[#00FF87]" : "text-[#FF4D4D]"}`}>
                {formatCurrency(totalPnl)}
              </p>
            </div>
          </div>
        </div>
      </div>
      <p className="mx-4 mb-3 flex-shrink-0 text-[10px] leading-snug text-[#6A7A9B] sm:mx-5">
        {t.tracker.disclaimer}
      </p>

      {error ? (
        <div className="mx-5 mb-4 rounded-lg border border-[#FF4D4D]/25 bg-[#FF4D4D]/10 px-4 py-3 text-xs text-[#FF8A8A]">
          {error}
        </div>
      ) : null}

      <div className="flex flex-col gap-3 px-4 pb-5 sm:px-5">
        {isLoading ? (
          <div className="rounded-lg border border-[#1A2845] bg-card p-5 text-center text-sm text-[#6A7A9B]">
            {t.tracker.loading}
          </div>
        ) : sortedBets.length === 0 ? (
          <div className="rounded-lg border border-[#1A2845] bg-card p-5 text-center">
            <p className="text-sm font-semibold text-foreground">{t.tracker.emptyTitle}</p>
            <p className="mt-1 text-xs leading-5 text-[#6A7A9B]">{t.tracker.emptyCopy}</p>
          </div>
        ) : (
          sortedBets.map((bet) => {
            const cfg = outcomeConfig[bet.outcome]
            const Icon = cfg.icon
            const isBetBusy = activeBetId === bet.id

            return (
              <div key={bet.id} className="rounded-lg border border-[#1A2845] bg-card p-4">
                <div className="mb-3 flex items-start justify-between gap-3">
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-xs font-semibold text-foreground">{bet.match}</p>
                    <p className="mt-0.5 text-[11px] text-[#6A7A9B]">{formatDate(bet.created_at, locale)}</p>
                  </div>
                  <div
                    className={`flex flex-shrink-0 items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-semibold ${cfg.bg} ${cfg.color}`}
                  >
                    <Icon className="h-3.5 w-3.5" />
                    {t.tracker[cfg.labelKey]}
                  </div>
                </div>

                <div className="flex items-center justify-between border-t border-[#1A2845] pt-2.5">
                  <div className="flex items-center gap-3">
                    <div>
                      <p className="text-[10px] uppercase tracking-wider text-[#6A7A9B]">
                        <ConceptTip concept="stake" label={t.tracker.stake} subtle />
                      </p>
                      <p className="text-sm font-semibold text-foreground">€{bet.amount.toFixed(2)}</p>
                    </div>
                    <div className="h-6 w-px bg-[#1A2845]" />
                    <div>
                      <p className="text-[10px] uppercase tracking-wider text-[#6A7A9B]">
                        <ConceptTip concept="bookmakerOdds" label={t.tracker.odds} subtle />
                      </p>
                      <p className="text-sm font-semibold text-foreground">{bet.odds.toFixed(2)}</p>
                    </div>
                  </div>
                  <div className="text-right">
                    <p className="text-[10px] uppercase tracking-wider text-[#6A7A9B]">
                      <ConceptTip concept="pnl" label={t.tracker.profitLoss} subtle />
                    </p>
                    {bet.outcome === "pending" ? (
                      <p className="text-sm font-bold text-[#FFD600]">{t.tracker.pending}</p>
                    ) : (
                      <p className={`text-sm font-bold ${bet.profit_loss >= 0 ? "text-[#00FF87]" : "text-[#FF4D4D]"}`}>
                        {formatCurrency(bet.profit_loss)}
                      </p>
                    )}
                  </div>
                </div>

                <div className="mt-3 flex items-center gap-2 border-t border-[#1A2845] pt-3">
                  {bet.outcome === "pending" ? (
                    <>
                      <button
                        className="flex flex-1 items-center justify-center gap-1.5 rounded-lg bg-[#00FF87]/10 px-3 py-2 text-xs font-semibold text-[#00FF87] disabled:opacity-50"
                        type="button"
                        disabled={isBetBusy}
                        onClick={() => void handleOutcome(bet.id, "win")}
                      >
                        <CheckCircle2 className="h-3.5 w-3.5" />
                        {t.tracker.markWin}
                      </button>
                      <button
                        className="flex flex-1 items-center justify-center gap-1.5 rounded-lg bg-[#FF4D4D]/10 px-3 py-2 text-xs font-semibold text-[#FF4D4D] disabled:opacity-50"
                        type="button"
                        disabled={isBetBusy}
                        onClick={() => void handleOutcome(bet.id, "loss")}
                      >
                        <XCircle className="h-3.5 w-3.5" />
                        {t.tracker.markLoss}
                      </button>
                    </>
                  ) : (
                    <button
                      className="flex flex-1 items-center justify-center gap-1.5 rounded-lg bg-[#FFD600]/10 px-3 py-2 text-xs font-semibold text-[#FFD600] disabled:opacity-50"
                      type="button"
                      disabled={isBetBusy}
                      onClick={() => void handleOutcome(bet.id, "pending")}
                    >
                      <Clock3 className="h-3.5 w-3.5" />
                      {t.tracker.pending}
                    </button>
                  )}
                  <button
                    className="flex h-8 w-9 items-center justify-center rounded-lg bg-[#1A2845] text-[#6A7A9B] transition-colors hover:text-foreground disabled:opacity-50"
                    type="button"
                    aria-label={t.tracker.delete}
                    disabled={isBetBusy}
                    onClick={() => void handleDelete(bet.id)}
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </button>
                </div>
              </div>
            )
          })
        )}
      </div>

      <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
        <DialogContent className="max-w-[390px] border-[#1A2845] bg-[#071021] text-foreground">
          <DialogHeader>
            <DialogTitle>{t.tracker.logBet}</DialogTitle>
            <DialogDescription className="text-[#6A7A9B]">{t.tracker.subtitle}</DialogDescription>
          </DialogHeader>

          <form className="flex flex-col gap-3" onSubmit={(event) => void handleSubmit(event)}>
            <label className="flex flex-col gap-1.5 text-xs font-semibold text-[#6A7A9B]">
              {t.tracker.betDescription}
              <Input
                className="border-[#1A2845] bg-[#0F1C35] text-base text-foreground sm:text-sm"
                maxLength={200}
                placeholder={t.tracker.betPlaceholder}
                value={match}
                onChange={(event) => setMatch(event.target.value)}
                required
              />
            </label>

            <div className="grid grid-cols-2 gap-3">
              <label className="flex flex-col gap-1.5 text-xs font-semibold text-[#6A7A9B]">
                {t.tracker.stake}
                <Input
                  className="border-[#1A2845] bg-[#0F1C35] text-base text-foreground sm:text-sm"
                  inputMode="decimal"
                  pattern="[0-9]+([.,][0-9]+)?"
                  value={amount}
                  onChange={(event) => setAmount(event.target.value)}
                  required
                />
              </label>
              <label className="flex flex-col gap-1.5 text-xs font-semibold text-[#6A7A9B]">
                {t.tracker.odds}
                <Input
                  className="border-[#1A2845] bg-[#0F1C35] text-base text-foreground sm:text-sm"
                  inputMode="decimal"
                  pattern="[0-9]+([.,][0-9]+)?"
                  value={odds}
                  onChange={(event) => setOdds(event.target.value)}
                  required
                />
              </label>
            </div>

            <DialogFooter className="mt-2 flex-row justify-end">
              <button
                className="rounded-lg px-4 py-2 text-xs font-semibold text-[#6A7A9B] transition-colors hover:text-foreground"
                type="button"
                onClick={() => setIsDialogOpen(false)}
              >
                {t.tracker.cancel}
              </button>
              <button
                className="rounded-lg bg-[#00FF87] px-4 py-2 text-xs font-bold text-[#04110A] transition-opacity disabled:opacity-50"
                type="submit"
                disabled={isSaving}
              >
                {isSaving ? t.tracker.saving : t.tracker.saveBet}
              </button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  )
}
