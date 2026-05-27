"use client"

import { FormEvent, useEffect, useMemo, useState } from "react"
import {
  BarChart3,
  CheckCircle2,
  CircleDollarSign,
  Clock3,
  Pencil,
  Plus,
  Ticket,
  Trash2,
  TrendingDown,
  TrendingUp,
  XCircle,
} from "lucide-react"

import {
  createTrackedBet,
  deleteTrackedBet,
  getTrackedBets,
  updateTrackedBet,
  updateTrackedBetOutcome,
  type BetListResponse,
  type BetOutcome,
  type CreateBetPayload,
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
import { ConceptTip, type ConceptKey } from "./ConceptTip"
import SectionHeader from "./SectionHeader"

const marketTypes = [
  "match_winner",
  "total_goals",
  "handicap",
  "both_teams_score",
  "player_prop",
  "futures",
  "other",
] as const

type MarketType = (typeof marketTypes)[number]

const defaultForm = {
  match: "",
  pick: "",
  market_type: "match_winner" as MarketType,
  bookmaker: "",
  amount: "",
  odds: "",
  outcome: "pending" as BetOutcome,
}

const emptyTracker: BetListResponse = {
  bets: [],
  summary: {
    total_bets: 0,
    pending_bets: 0,
    wins: 0,
    losses: 0,
    win_rate: 0,
    total_staked: 0,
    pending_exposure: 0,
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
    labelKey: "pending" as const,
  },
}

function formatCurrency(value: number, options: { signed?: boolean } = {}) {
  const sign = options.signed && value > 0 ? "+" : value < 0 ? "-" : ""
  return `${sign}€${Math.abs(value).toFixed(2)}`
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
  const pendingExposure = bets
    .filter((bet) => bet.outcome === "pending")
    .reduce((sum, bet) => sum + bet.amount, 0)
  const profitLoss = bets.reduce((sum, bet) => sum + bet.profit_loss, 0)

  return {
    total_bets: bets.length,
    pending_bets: pendingBets,
    wins,
    losses,
    win_rate: settledBets > 0 ? wins / settledBets : 0,
    total_staked: Number(totalStaked.toFixed(2)),
    pending_exposure: Number(pendingExposure.toFixed(2)),
    profit_loss: Number(profitLoss.toFixed(2)),
    roi: totalStaked > 0 ? Number((profitLoss / totalStaked).toFixed(4)) : 0,
  }
}

export default function BetTracker() {
  const { language, t } = useLanguage()
  const [tracker, setTracker] = useState<BetListResponse>(emptyTracker)
  const [isLoading, setIsLoading] = useState(true)
  const [isDialogOpen, setIsDialogOpen] = useState(false)
  const [editingBet, setEditingBet] = useState<TrackedBet | null>(null)
  const [form, setForm] = useState(defaultForm)
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
          setTracker({
            bets: data.bets,
            summary: {
              ...data.summary,
              pending_exposure: data.summary.pending_exposure ?? recomputeSummary(data.bets).pending_exposure,
            },
          })
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

  const openCreateDialog = () => {
    setEditingBet(null)
    setForm(defaultForm)
    setError(null)
    setIsDialogOpen(true)
  }

  const openEditDialog = (bet: TrackedBet) => {
    setEditingBet(bet)
    setForm({
      match: bet.match,
      pick: bet.pick ?? bet.match,
      market_type: (marketTypes.includes(bet.market_type as MarketType) ? bet.market_type : "other") as MarketType,
      bookmaker: bet.bookmaker ?? "",
      amount: String(bet.amount),
      odds: String(bet.odds),
      outcome: bet.outcome === "cashed_out" ? "pending" : bet.outcome,
    })
    setError(null)
    setIsDialogOpen(true)
  }

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setError(null)

    const amount = parseDecimalInput(form.amount)
    const odds = parseDecimalInput(form.odds)
    if (!Number.isFinite(amount) || !Number.isFinite(odds)) {
      setError(t.tracker.invalidNumbers)
      return
    }

    const payload: CreateBetPayload = {
      match: form.match,
      pick: form.pick,
      market_type: form.market_type,
      bookmaker: form.bookmaker.trim() || null,
      amount,
      odds,
      outcome: form.outcome,
    }

    try {
      setIsSaving(true)
      if (editingBet) {
        const updatedBet = await updateTrackedBet(editingBet.id, payload)
        refreshTracker(tracker.bets.map((bet) => (bet.id === updatedBet.id ? updatedBet : bet)))
      } else {
        const createdBet = await createTrackedBet(payload)
        refreshTracker([createdBet, ...tracker.bets])
      }
      setForm(defaultForm)
      setEditingBet(null)
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

  const summaryChips = [
    {
      label: t.tracker.totalStaked,
      value: formatCurrency(tracker.summary.total_staked),
      icon: CircleDollarSign,
      className: "text-foreground",
      concept: "stake" as ConceptKey,
    },
    {
      label: t.tracker.profitLoss,
      value: formatCurrency(totalPnl, { signed: true }),
      icon: totalPnl >= 0 ? TrendingUp : TrendingDown,
      className: totalPnl >= 0 ? "text-[#00FF87]" : "text-[#FF4D4D]",
      concept: "pnl" as ConceptKey,
    },
    {
      label: t.tracker.winRate,
      value: `${winRate}%`,
      icon: BarChart3,
      className: "text-[#00FF87]",
      concept: "winRate" as ConceptKey,
    },
    {
      label: t.tracker.pendingExposure,
      value: formatCurrency(tracker.summary.pending_exposure),
      icon: Clock3,
      className: "text-[#FFD600]",
      concept: "pendingExposure" as ConceptKey,
    },
  ]

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
            onClick={openCreateDialog}
          >
            <Plus className="h-3.5 w-3.5" />
            {t.tracker.logBet}
          </button>
        }
      />

      <div className="mx-4 mb-3 grid grid-cols-2 gap-2 sm:mx-5">
        {summaryChips.map((chip) => {
          const Icon = chip.icon
          return (
            <div
              key={chip.label}
              className="min-w-0 rounded-lg border border-[#1A2845]/80 bg-[#0D172B] px-3 py-2 shadow-[inset_0_1px_0_rgba(255,255,255,0.03)]"
            >
              <div className="flex min-w-0 items-center gap-1.5 text-[9px] font-semibold uppercase tracking-wider text-[#6A7A9B]">
                <Icon className="h-3 w-3 flex-shrink-0" />
                <ConceptTip concept={chip.concept} label={chip.label} subtle />
              </div>
              <p className={`mt-0.5 truncate text-base font-bold ${chip.className}`}>{chip.value}</p>
            </div>
          )
        })}
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
            const displayOutcome = bet.outcome === "cashed_out" ? "pending" : bet.outcome
            const cfg = outcomeConfig[displayOutcome]
            const Icon = cfg.icon
            const isBetBusy = activeBetId === bet.id
            const marketType = marketTypes.includes(bet.market_type as MarketType)
              ? (bet.market_type as MarketType)
              : "other"

            return (
              <article
                key={bet.id}
                className="overflow-hidden rounded-lg border border-[#1A2845] bg-card shadow-[0_10px_30px_rgba(0,0,0,0.18)]"
              >
                <div className="flex items-start justify-between gap-3 border-b border-[#1A2845] bg-[#0F1C35] px-3.5 py-3">
                  <div className="min-w-0">
                    <div className="flex min-w-0 items-center gap-1.5 text-[11px] font-semibold uppercase tracking-wider text-[#6A7A9B]">
                      <Ticket className="h-3.5 w-3.5 flex-shrink-0" />
                      <span className="truncate">{t.tracker.marketTypes[marketType]}</span>
                    </div>
                    <p className="mt-1 truncate text-sm font-bold text-foreground">{bet.pick ?? bet.match}</p>
                    <p className="mt-0.5 truncate text-xs text-[#6A7A9B]">{bet.match}</p>
                  </div>
                  <div
                    className={`flex flex-shrink-0 items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-semibold ${cfg.bg} ${cfg.color}`}
                  >
                    <Icon className="h-3.5 w-3.5" />
                    {t.tracker[cfg.labelKey]}
                  </div>
                </div>

                <div className="grid grid-cols-4 gap-2 px-3.5 py-3">
                  <div>
                    <p className="text-[10px] uppercase tracking-wider text-[#6A7A9B]">
                      <ConceptTip concept="stake" label={t.tracker.stake} subtle />
                    </p>
                    <p className="mt-0.5 text-sm font-semibold text-foreground">{formatCurrency(bet.amount)}</p>
                  </div>
                  <div>
                    <p className="text-[10px] uppercase tracking-wider text-[#6A7A9B]">
                      <ConceptTip concept="bookmakerOdds" label={t.tracker.odds} subtle />
                    </p>
                    <p className="mt-0.5 text-sm font-semibold text-foreground">{bet.odds.toFixed(2)}</p>
                  </div>
                  <div>
                    <p className="text-[10px] uppercase tracking-wider text-[#6A7A9B]">{t.tracker.bookmaker}</p>
                    <p className="mt-0.5 truncate text-sm font-semibold text-foreground">
                      {bet.bookmaker || t.tracker.noBookmaker}
                    </p>
                  </div>
                  <div className="text-right">
                    <p className="text-[10px] uppercase tracking-wider text-[#6A7A9B]">
                      <ConceptTip concept="pnl" label={t.tracker.profitLoss} subtle />
                    </p>
                    {bet.outcome === "pending" ? (
                      <p className="mt-0.5 text-sm font-bold text-[#FFD600]">{t.tracker.pending}</p>
                    ) : (
                      <p
                        className={`mt-0.5 text-sm font-bold ${
                          bet.profit_loss >= 0 ? "text-[#00FF87]" : "text-[#FF4D4D]"
                        }`}
                      >
                        {formatCurrency(bet.profit_loss, { signed: true })}
                      </p>
                    )}
                  </div>
                </div>

                <div className="flex items-center gap-1.5 border-t border-[#1A2845] px-2.5 py-2">
                  <button
                    className="flex h-8 flex-1 items-center justify-center gap-1.5 rounded-lg bg-[#00FF87]/10 px-2 text-xs font-semibold text-[#00FF87] disabled:opacity-50"
                    type="button"
                    disabled={isBetBusy}
                    onClick={() => void handleOutcome(bet.id, "win")}
                  >
                    <CheckCircle2 className="h-3.5 w-3.5" />
                    {t.tracker.markWin}
                  </button>
                  <button
                    className="flex h-8 flex-1 items-center justify-center gap-1.5 rounded-lg bg-[#FF4D4D]/10 px-2 text-xs font-semibold text-[#FF4D4D] disabled:opacity-50"
                    type="button"
                    disabled={isBetBusy}
                    onClick={() => void handleOutcome(bet.id, "loss")}
                  >
                    <XCircle className="h-3.5 w-3.5" />
                    {t.tracker.markLoss}
                  </button>
                  <button
                    className="flex h-8 w-9 items-center justify-center rounded-lg bg-[#1A2845] text-[#6A7A9B] transition-colors hover:text-foreground disabled:opacity-50"
                    type="button"
                    aria-label={t.tracker.edit}
                    disabled={isBetBusy}
                    onClick={() => openEditDialog(bet)}
                  >
                    <Pencil className="h-3.5 w-3.5" />
                  </button>
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

                <div className="border-t border-[#1A2845] px-3.5 py-2 text-[11px] text-[#6A7A9B]">
                  {formatDate(bet.created_at, locale)}
                </div>
              </article>
            )
          })
        )}
      </div>

      <Dialog
        open={isDialogOpen}
        onOpenChange={(open) => {
          setIsDialogOpen(open)
          if (!open) {
            setEditingBet(null)
            setForm(defaultForm)
          }
        }}
      >
        <DialogContent className="max-w-[410px] border-[#1A2845] bg-[#071021] text-foreground">
          <DialogHeader>
            <DialogTitle>{editingBet ? t.tracker.editBet : t.tracker.logBet}</DialogTitle>
            <DialogDescription className="text-[#6A7A9B]">{t.tracker.subtitle}</DialogDescription>
          </DialogHeader>

          <form className="flex flex-col gap-3" onSubmit={(event) => void handleSubmit(event)}>
            <label className="flex flex-col gap-1.5 text-xs font-semibold text-[#6A7A9B]">
              {t.tracker.match}
              <Input
                className="border-[#1A2845] bg-[#0F1C35] text-base text-foreground sm:text-sm"
                maxLength={200}
                placeholder={t.tracker.matchPlaceholder}
                value={form.match}
                onChange={(event) => setForm((current) => ({ ...current, match: event.target.value }))}
                required
              />
            </label>

            <label className="flex flex-col gap-1.5 text-xs font-semibold text-[#6A7A9B]">
              {t.tracker.pick}
              <Input
                className="border-[#1A2845] bg-[#0F1C35] text-base text-foreground sm:text-sm"
                maxLength={160}
                placeholder={t.tracker.pickPlaceholder}
                value={form.pick}
                onChange={(event) => setForm((current) => ({ ...current, pick: event.target.value }))}
                required
              />
            </label>

            <div className="grid grid-cols-2 gap-3">
              <label className="flex flex-col gap-1.5 text-xs font-semibold text-[#6A7A9B]">
                {t.tracker.marketType}
                <select
                  className="h-10 rounded-lg border border-[#1A2845] bg-[#0F1C35] px-2 text-sm font-semibold text-foreground outline-none"
                  value={form.market_type}
                  onChange={(event) =>
                    setForm((current) => ({ ...current, market_type: event.target.value as MarketType }))
                  }
                >
                  {marketTypes.map((marketType) => (
                    <option key={marketType} value={marketType}>
                      {t.tracker.marketTypes[marketType]}
                    </option>
                  ))}
                </select>
              </label>
              <label className="flex flex-col gap-1.5 text-xs font-semibold text-[#6A7A9B]">
                {t.tracker.status}
                <select
                  className="h-10 rounded-lg border border-[#1A2845] bg-[#0F1C35] px-2 text-sm font-semibold text-foreground outline-none"
                  value={form.outcome}
                  onChange={(event) => setForm((current) => ({ ...current, outcome: event.target.value as BetOutcome }))}
                >
                  <option value="pending">{t.tracker.pending}</option>
                  <option value="win">{t.tracker.won}</option>
                  <option value="loss">{t.tracker.lost}</option>
                </select>
              </label>
            </div>

            <div className="grid grid-cols-3 gap-3">
              <label className="flex flex-col gap-1.5 text-xs font-semibold text-[#6A7A9B]">
                {t.tracker.stake}
                <Input
                  className="border-[#1A2845] bg-[#0F1C35] text-base text-foreground sm:text-sm"
                  inputMode="decimal"
                  pattern="[0-9]+([.,][0-9]+)?"
                  value={form.amount}
                  onChange={(event) => setForm((current) => ({ ...current, amount: event.target.value }))}
                  required
                />
              </label>
              <label className="flex flex-col gap-1.5 text-xs font-semibold text-[#6A7A9B]">
                {t.tracker.odds}
                <Input
                  className="border-[#1A2845] bg-[#0F1C35] text-base text-foreground sm:text-sm"
                  inputMode="decimal"
                  pattern="[0-9]+([.,][0-9]+)?"
                  value={form.odds}
                  onChange={(event) => setForm((current) => ({ ...current, odds: event.target.value }))}
                  required
                />
              </label>
              <label className="flex flex-col gap-1.5 text-xs font-semibold text-[#6A7A9B]">
                {t.tracker.bookmaker}
                <Input
                  className="border-[#1A2845] bg-[#0F1C35] text-base text-foreground sm:text-sm"
                  maxLength={120}
                  value={form.bookmaker}
                  onChange={(event) => setForm((current) => ({ ...current, bookmaker: event.target.value }))}
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
                {isSaving ? t.tracker.saving : editingBet ? t.tracker.updateBet : t.tracker.saveBet}
              </button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  )
}
