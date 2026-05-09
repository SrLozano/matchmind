"use client"

import { useEffect, useMemo, useState } from "react"
import type { ReactNode } from "react"
import { Activity, AlertCircle, Lock, RefreshCw } from "lucide-react"

import { getMarketSignals, type MarketSignal } from "@/lib/api"
import { flagForTeam } from "@/lib/country-flags"
import { useLanguage, type Language } from "@/lib/i18n"

const FREE_SIGNAL_COUNT = 3

export default function MarketSignals() {
  const { language, t } = useLanguage()
  const [signals, setSignals] = useState<MarketSignal[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const visibleSignals = useMemo(() => {
    return signals
      .filter((signal) => signal.matched && signal.active !== false && signal.closed !== true)
      .sort(compareMarketSignals)
      .slice(0, 12)
  }, [signals])

  const headlineSignals = visibleSignals.filter(isHeadlineSignal).slice(0, FREE_SIGNAL_COUNT)
  const headlineSlugs = new Set(headlineSignals.map((signal) => signal.slug ?? signal.question ?? signal.team))
  const premiumSignals = visibleSignals.filter((signal) => !headlineSlugs.has(signal.slug ?? signal.question ?? signal.team))

  const loadSignals = async () => {
    setIsLoading(true)
    setError(null)

    try {
      const result = await getMarketSignals()
      setSignals(result.signals)
    } catch (err) {
      setError(err instanceof Error ? err.message : t.feed.marketSignalsLoadError)
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    void loadSignals()
  }, [])

  return (
    <div className="flex h-full flex-col overflow-y-auto">
      <div className="flex-shrink-0 px-5 pb-4 pt-6">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl border border-[#00FF87]/25 bg-[#00FF87]/10 text-[#00FF87]">
            <Activity className="h-5 w-5" />
          </div>
          <div className="min-w-0">
            <h1 className="text-2xl font-bold tracking-tight text-foreground">{t.feed.marketSignals}</h1>
            <p className="mt-0.5 text-xs leading-relaxed text-[#6A7A9B]">
              {t.feed.marketSignalsSubtitle}
            </p>
          </div>
        </div>
      </div>

      <div className="mx-5 mb-5 grid flex-shrink-0 grid-cols-3 overflow-hidden rounded-xl border border-[#1A2845] bg-[#0F1C35]">
        <StatCell label={t.signals.available} value={visibleSignals.length.toString()} />
        <StatCell label={t.feed.free} value={headlineSignals.length.toString()} accent="text-[#00FF87]" />
        <StatCell label={t.feed.pro} value={premiumSignals.length.toString()} accent="text-[#FFD600]" />
      </div>

      <div className="flex flex-col gap-3 px-5 pb-6">
        {isLoading ? (
          <LoadingSignals />
        ) : error ? (
          <SignalsError message={error} onRetry={() => void loadSignals()} />
        ) : visibleSignals.length === 0 ? (
          <SignalsEmpty />
        ) : (
          <>
            {headlineSignals.length > 0 ? (
              <SignalGroup title={t.signals.headline} count={headlineSignals.length}>
                {headlineSignals.map((signal, index) => (
                  <SignalRow
                    key={signal.slug ?? `${signal.question ?? signal.team}-${index}`}
                    signal={signal}
                    language={language}
                    locked={false}
                  />
                ))}
              </SignalGroup>
            ) : (
              <NoHeadlineSignals />
            )}

            {premiumSignals.length > 0 && (
              <SignalGroup title={t.signals.premium} count={premiumSignals.length}>
                {premiumSignals.map((signal, index) => (
                  <SignalRow
                    key={signal.slug ?? `${signal.question ?? signal.team}-locked-${index}`}
                    signal={signal}
                    language={language}
                    locked
                  />
                ))}
              </SignalGroup>
            )}
          </>
        )}
      </div>
    </div>
  )
}

function SignalGroup({
  title,
  count,
  children,
}: {
  title: string
  count: number
  children: ReactNode
}) {
  return (
    <section>
      <div className="mb-2 flex items-center justify-between">
        <h2 className="text-xs font-bold uppercase tracking-widest text-[#6A7A9B]">{title}</h2>
        <span className="text-[11px] font-semibold text-[#A8B4D0]">{count}</span>
      </div>
      <div className="flex flex-col gap-2">{children}</div>
    </section>
  )
}

function SignalRow({
  signal,
  language,
  locked,
}: {
  signal: MarketSignal
  language: Language
  locked: boolean
}) {
  const { t } = useLanguage()
  const title = signal.question ?? signal.team ?? signal.teams[0] ?? t.feed.unknownTeam
  const teamLabel = signal.team ?? signal.teams[0]
  const quality = signal.signal_quality_score
  const displayTitle = locked ? t.signals.lockedSignal : title
  const metricValue = locked ? t.feed.locked : undefined

  return (
    <article className={`overflow-hidden rounded-xl border bg-card px-4 py-3 ${locked ? "border-[#FFD600]/25" : "border-[#1A2845]"}`}>
      <div>
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0 flex-1">
            <div className="flex min-w-0 items-start gap-2">
              {!locked && teamLabel && <span className="mt-0.5 shrink-0 text-base leading-none">{flagForTeam(teamLabel)}</span>}
              <p className="min-w-0 break-words text-sm font-semibold leading-snug text-foreground">
                {displayTitle}
              </p>
            </div>
            <p className="mt-1 text-[11px] font-medium text-[#6A7A9B]">
              {locked ? t.signals.lockedCopy : formatMarketType(signal.market_type, language)}
            </p>
          </div>

          {locked ? (
            <div className="inline-flex shrink-0 items-center gap-1.5 rounded-full border border-[#FFD600]/30 bg-[#FFD600]/10 px-2.5 py-1.5 text-[10px] font-bold uppercase tracking-wide text-[#FFD600]">
              <Lock className="h-3 w-3" />
              {t.signals.unlockPremium}
            </div>
          ) : (
            <div className="shrink-0 text-right">
              <p className="text-[10px] uppercase tracking-wider text-[#6A7A9B]">
                {t.feed.crowdProbability}
              </p>
              <p className="text-lg font-bold text-[#00FF87]">
                {formatPercent(signal.implied_probability, t.feed.noValue)}
              </p>
            </div>
          )}
        </div>

        <div className="mt-3 grid grid-cols-3 gap-2">
          <SignalMetric label={t.feed.liquidity} value={metricValue ?? signal.liquidity_label ?? t.feed.noValue} />
          <SignalMetric
            label={t.feed.signalQuality}
            value={metricValue ?? (typeof quality === "number" ? `${quality}/100` : t.feed.noValue)}
            accent={locked ? "text-[#FFD600]" : getSignalQualityClass(quality)}
          />
          <SignalMetric label={t.feed.marketType} value={metricValue ?? formatMarketType(signal.market_type, language)} />
        </div>
      </div>
    </article>
  )
}

function SignalMetric({
  label,
  value,
  accent = "text-[#A8B4D0]",
}: {
  label: string
  value: string
  accent?: string
}) {
  return (
    <div className="min-w-0">
      <p className="truncate text-[9px] uppercase tracking-wider text-[#6A7A9B]">{label}</p>
      <p className={`mt-0.5 truncate text-[11px] font-semibold ${accent}`}>{value}</p>
    </div>
  )
}

function LoadingSignals() {
  const { t } = useLanguage()

  return (
    <div className="flex flex-col gap-2">
      <p className="px-1 text-[11px] font-medium text-[#6A7A9B]">{t.feed.marketSignalsLoading}</p>
      {[0, 1, 2, 3].map((item) => (
        <div key={item} className="rounded-xl border border-[#1A2845] bg-card p-4">
          <div className="h-4 w-5/6 animate-pulse rounded bg-[#111E38]" />
          <div className="mt-3 grid grid-cols-3 gap-2">
            <div className="h-7 animate-pulse rounded bg-[#111E38]" />
            <div className="h-7 animate-pulse rounded bg-[#111E38]" />
            <div className="h-7 animate-pulse rounded bg-[#111E38]" />
          </div>
        </div>
      ))}
    </div>
  )
}

function SignalsError({ message, onRetry }: { message: string; onRetry: () => void }) {
  const { t } = useLanguage()

  return (
    <div className="rounded-xl border border-[#FF4D4D]/30 bg-[#FF4D4D]/10 p-4">
      <div className="flex items-start gap-3">
        <AlertCircle className="mt-0.5 h-5 w-5 shrink-0 text-[#FF4D4D]" />
        <div className="min-w-0 flex-1">
          <p className="text-sm font-semibold text-foreground">{t.feed.marketSignalsUnavailable}</p>
          <p className="mt-1 text-xs leading-relaxed text-[#A8B4D0]">{message}</p>
          <button
            onClick={onRetry}
            className="mt-3 inline-flex items-center gap-1.5 rounded-lg border border-[#1A2845] bg-[#0F1C35] px-3 py-2 text-xs font-semibold text-foreground transition-colors hover:border-[#00FF87]/50"
          >
            <RefreshCw className="h-3.5 w-3.5" />
            {t.feed.retry}
          </button>
        </div>
      </div>
    </div>
  )
}

function SignalsEmpty() {
  const { t } = useLanguage()

  return (
    <div className="rounded-xl border border-[#1A2845] bg-card p-5 text-center">
      <Activity className="mx-auto h-6 w-6 text-[#6A7A9B]" />
      <p className="mt-3 text-sm font-semibold text-foreground">{t.feed.marketSignalsEmptyTitle}</p>
      <p className="mt-1 text-xs leading-relaxed text-[#6A7A9B]">
        {t.feed.marketSignalsEmptyCopy}
      </p>
    </div>
  )
}

function NoHeadlineSignals() {
  const { t } = useLanguage()

  return (
    <section className="rounded-xl border border-[#1A2845] bg-card p-4">
      <div className="flex items-start gap-3">
        <Activity className="mt-0.5 h-5 w-5 shrink-0 text-[#6A7A9B]" />
        <div className="min-w-0">
          <p className="text-sm font-semibold text-foreground">{t.signals.noHeadlineTitle}</p>
          <p className="mt-1 text-xs leading-relaxed text-[#6A7A9B]">
            {t.signals.noHeadlineCopy}
          </p>
        </div>
      </div>
    </section>
  )
}

function StatCell({
  label,
  value,
  accent = "text-foreground",
}: {
  label: string
  value: string
  accent?: string
}) {
  return (
    <div className="border-r border-[#1A2845] p-3 text-center last:border-r-0">
      <p className="mb-0.5 text-[10px] uppercase tracking-wider text-[#6A7A9B]">{label}</p>
      <p className={`text-lg font-bold ${accent}`}>{value}</p>
    </div>
  )
}

function compareMarketSignals(a: MarketSignal, b: MarketSignal) {
  const probabilityDelta = (b.implied_probability ?? 0) - (a.implied_probability ?? 0)
  if (Math.abs(probabilityDelta) > 0.005) return probabilityDelta

  const typeDelta = getMarketTypePriority(b.market_type) - getMarketTypePriority(a.market_type)
  if (typeDelta !== 0) return typeDelta

  return (b.signal_quality_score ?? 0) - (a.signal_quality_score ?? 0)
}

function isHeadlineSignal(signal: MarketSignal) {
  return (signal.implied_probability ?? 0) >= 0.02
}

function getMarketTypePriority(value: string | null) {
  if (value === "tournament_outright") return 4
  if (value === "group_winner") return 3
  if (value === "advance_to_knockout" || value === "reach_stage") return 2
  return 1
}

function formatPercent(value: number | null, fallback: string) {
  if (typeof value !== "number") return fallback
  if (value < 0.01 && value > 0) return "<1%"
  return `${Math.round(value * 100)}%`
}

function formatMarketType(value: string | null, language: Language) {
  if (!value) return language === "es" ? "Mercado" : "Market"

  const labels: Record<string, { en: string; es: string }> = {
    tournament_outright: { en: "World Cup winner", es: "Ganador del Mundial" },
    group_winner: { en: "Group winner", es: "Ganador de grupo" },
    advance_to_knockout: { en: "Advance to knockouts", es: "Clasifica a eliminatorias" },
    reach_stage: { en: "Reach stage", es: "Llegar a ronda" },
    squad_inclusion: { en: "Squad market", es: "Convocatoria" },
    top_goalscorer: { en: "Top goalscorer", es: "Máximo goleador" },
  }

  return labels[value]?.[language] ?? value.replaceAll("_", " ")
}

function getSignalQualityClass(value: number | null) {
  if (typeof value !== "number") return "text-[#A8B4D0]"
  if (value >= 75) return "text-[#00FF87]"
  if (value >= 50) return "text-[#FFD600]"
  return "text-[#A8B4D0]"
}
