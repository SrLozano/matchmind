"use client"

import { useCallback, useEffect, useMemo, useState } from "react"
import type { KeyboardEvent } from "react"
import { AlertCircle, CalendarDays, ChevronDown, Clock, Crown, Lock, MessageCircle, RefreshCw, Sparkles, TrendingUp } from "lucide-react"
import { getOddsMatches, getWorldCupFixtures, type OddsMatch, type OddsConsensusRow, type WorldCupFixture } from "@/lib/api"
import { displayTeamName, flagForTeam } from "@/lib/country-flags"
import { useLanguage } from "@/lib/i18n"
import { usePreferences } from "@/lib/preferences"
import { ConceptTip } from "./ConceptTip"
import SectionHeader from "./SectionHeader"

type FeedState = {
  matches: WorldCupFixture[]
  oddsMatches: OddsMatch[]
  lastUpdated: Date | null
}

const MATCH_ROTATION_TICK_MS = 60 * 1000
const FEED_REFRESH_INTERVAL_MS = 5 * 60 * 1000

export default function DailyFeed({
  isPremium,
  onShowUpgradePrompt,
  onBringToCoach,
}: {
  isPremium: boolean
  onShowUpgradePrompt: () => void
  onBringToCoach: (prompt: string) => void
}) {
  const { language, t } = useLanguage()
  const [feed, setFeed] = useState<FeedState>({ matches: [], oddsMatches: [], lastUpdated: null })
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [nowMs, setNowMs] = useState(() => Date.now())
  const locale = language === "es" ? "es-ES" : "en-US"
  const dateFormatter = useMemo(
    () =>
      new Intl.DateTimeFormat(locale, {
        weekday: "short",
        month: "short",
        day: "numeric",
      }),
    [locale]
  )
  const timeFormatter = useMemo(
    () =>
      new Intl.DateTimeFormat(locale, {
        hour: "2-digit",
        minute: "2-digit",
      }),
    [locale]
  )
  const today = useMemo(
    () =>
      new Date().toLocaleDateString(locale, {
        weekday: "long",
        month: "long",
        day: "numeric",
      }),
    [locale]
  )

  const loadFixtures = useCallback(async (showLoading = true) => {
    if (showLoading) {
      setIsLoading(true)
      setError(null)
    }

    try {
      const [fixturesResult, oddsResult] = await Promise.allSettled([
        getWorldCupFixtures(),
        getOddsMatches(),
      ])
      if (fixturesResult.status === "rejected") {
        throw fixturesResult.reason
      }
      setFeed({
        matches: fixturesResult.value.matches,
        oddsMatches: oddsResult.status === "fulfilled" ? oddsResult.value.matches : [],
        lastUpdated: new Date(),
      })
    } catch (err) {
      if (showLoading) setError(err instanceof Error ? err.message : t.feed.loadError)
    } finally {
      if (showLoading) setIsLoading(false)
    }
  }, [t.feed.loadError])

  useEffect(() => {
    void loadFixtures()
  }, [loadFixtures])

  useEffect(() => {
    const refreshTimer = window.setInterval(() => {
      void loadFixtures(false)
    }, FEED_REFRESH_INTERVAL_MS)

    return () => window.clearInterval(refreshTimer)
  }, [loadFixtures])

  useEffect(() => {
    const rotationTimer = window.setInterval(() => {
      setNowMs(Date.now())
    }, MATCH_ROTATION_TICK_MS)

    return () => window.clearInterval(rotationTimer)
  }, [])

  const sortedMatches = useMemo(() => {
    const byKickoff = [...feed.matches].sort((a, b) => {
      return getKickoffTimestamp(a) - getKickoffTimestamp(b)
    })
    const upcoming = byKickoff.filter((match) => {
      const kickoff = getKickoffTimestamp(match)
      return !Number.isFinite(kickoff) || kickoff >= nowMs
    })

    return upcoming.length > 0 ? upcoming : byKickoff
  }, [feed.matches, nowMs])

  const freeInsightCount = Math.min(sortedMatches.length, 2)
  const proInsightCount = Math.max(sortedMatches.length - freeInsightCount, 0)

  return (
    <div className="flex h-full flex-col overflow-y-auto">
      <SectionHeader
        icon={CalendarDays}
        title={t.feed.title}
        subtitle={`${today} · ${formatUpdatedAt(feed.lastUpdated, timeFormatter, t.feed.updated, t.feed.liveFixtureList)}`}
      />

      {isPremium ? (
        <PremiumSummaryBanner
          eyebrow={t.feed.passActive}
          title={t.feed.calendarUnlocked}
          value={sortedMatches.length.toString()}
          valueLabel={t.feed.matchesAvailable}
          detail={`${freeInsightCount} ${t.feed.highlighted} · ${proInsightCount} ${t.feed.includedAnalyses}`}
        />
      ) : (
        <div className="mx-4 mb-4 grid flex-shrink-0 grid-cols-3 overflow-hidden rounded-xl border border-[#1A2845] bg-[#0F1C35] sm:mx-5">
          <StatCell label={t.feed.upcoming} value={sortedMatches.length.toString()} />
          <StatCell label={t.feed.free} value={freeInsightCount.toString()} accent="text-[#00FF87]" />
          <StatCell label={t.feed.pro} value={proInsightCount.toString()} accent="text-[#E8D39A]" onClick={onShowUpgradePrompt} />
        </div>
      )}
      <p className="mx-4 mb-3 flex-shrink-0 text-[10px] leading-snug text-[#6A7A9B] sm:mx-5">
        {t.feed.disclaimer}
      </p>

      <div className="flex flex-col gap-3 px-4 pb-5 sm:px-5">
        {isLoading ? (
          <LoadingMatches />
        ) : error ? (
          <ErrorState message={error} onRetry={() => void loadFixtures()} />
        ) : sortedMatches.length === 0 ? (
          <EmptyState />
        ) : (
          sortedMatches.map((match, index) => (
            <MatchRow
              key={`${match.id ?? match.match}-${match.kickoff_time ?? index}`}
              match={match}
              access={getMatchAccess(match, index, isPremium)}
              isPremium={isPremium}
              onShowUpgradePrompt={onShowUpgradePrompt}
              onBringToCoach={onBringToCoach}
              odds={findOddsForFixture(match, feed.oddsMatches)}
              dateFormatter={dateFormatter}
              timeFormatter={timeFormatter}
            />
          ))
        )}
      </div>
    </div>
  )
}

function MatchRow({
  match,
  access,
  isPremium,
  onShowUpgradePrompt,
  onBringToCoach,
  odds,
  dateFormatter,
  timeFormatter,
}: {
  match: WorldCupFixture
  access: MatchAccess
  isPremium: boolean
  onShowUpgradePrompt: () => void
  onBringToCoach: (prompt: string) => void
  odds: OddsMatch | null
  dateFormatter: Intl.DateTimeFormat
  timeFormatter: Intl.DateTimeFormat
}) {
  const { language, t } = useLanguage()
  const homeTeam = match.home_team ?? match.match.split(" vs ")[0] ?? "Home"
  const awayTeam = match.away_team ?? match.match.split(" vs ")[1] ?? "Away"
  const kickoff = parseKickoff(match.kickoff_time)
  const hasPick = Boolean(match.pick || match.confidence_score || match.edge)

  const isLocked = access === "locked"
  const handleLockedKeyDown = (event: KeyboardEvent<HTMLElement>) => {
    if (!isLocked) return
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault()
      onShowUpgradePrompt()
    }
  }

  return (
    <article
      className={`overflow-hidden rounded-xl border border-[#1A2845] bg-card ${isLocked ? "cursor-pointer transition-colors hover:border-[#D8B866]/45" : ""}`}
      onClick={isLocked ? onShowUpgradePrompt : undefined}
      onKeyDown={handleLockedKeyDown}
      role={isLocked ? "button" : undefined}
      tabIndex={isLocked ? 0 : undefined}
    >
      <div className="flex items-start gap-3 px-3.5 py-3.5">
        <div className="flex w-[68px] shrink-0 flex-col items-center rounded-lg border border-[#1A2845] bg-[#0A1325] px-2 py-2 text-center">
          <span className="text-[10px] font-semibold uppercase tracking-wide text-[#6A7A9B]">
            {kickoff ? dateFormatter.format(kickoff).split(" ")[0] : t.feed.tbd}
          </span>
          <span className="mt-1 whitespace-nowrap text-xs font-bold text-foreground">
            {kickoff ? timeFormatter.format(kickoff) : "--:--"}
          </span>
        </div>

        <div className="min-w-0 flex-1">
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0">
              <TeamLine name={homeTeam} />
              <TeamLine name={awayTeam} />
            </div>
            <InsightBadge access={access} isPremium={isPremium} />
          </div>

          <div className="mt-2 flex flex-wrap items-center gap-x-2.5 gap-y-1 text-[11px] leading-snug text-[#6A7A9B]">
            <span className="inline-flex items-center gap-1">
              <CalendarDays className="h-3 w-3" />
              {kickoff ? dateFormatter.format(kickoff) : t.feed.datePending}
            </span>
            {match.stage && <span>{match.stage}</span>}
            {match.venue && <span>{match.venue}</span>}
          </div>
        </div>
      </div>

      <div className="border-t border-[#1A2845] bg-[#0A1325]/70 px-3.5 py-3">
        <div className="space-y-3">
          {access === "locked" ? (
            <LockedInsight />
          ) : (
            <UnlockedInsight match={match} hasPick={hasPick} access={access} isPremium={isPremium} />
          )}
          <BookmakerPanel odds={odds} homeTeam={homeTeam} awayTeam={awayTeam} access={access} />
          {access !== "locked" && (
            <button
              type="button"
              onClick={() => onBringToCoach(buildCoachPrompt(match, odds, homeTeam, awayTeam, language))}
              className="flex w-full items-center justify-center gap-2 rounded-lg border border-[#00FF87]/30 bg-[#00FF87]/10 px-3 py-2.5 text-xs font-bold text-[#00FF87] transition-colors hover:border-[#00FF87]/60 hover:bg-[#00FF87]/15"
            >
              <MessageCircle className="h-3.5 w-3.5" />
              {t.feed.bringToCoach}
            </button>
          )}
        </div>
      </div>
    </article>
  )
}

function TeamLine({ name }: { name: string }) {
  const { language } = useLanguage()
  const displayName = displayTeamName(name, language)

  return (
    <div className="flex min-w-0 items-center gap-2 py-0.5">
      <span className="w-5 shrink-0 text-lg leading-none">{flagForTeam(name)}</span>
      <span className="truncate text-sm font-semibold text-foreground">{displayName}</span>
    </div>
  )
}

type MatchAccess = "free" | "premium" | "locked"

function InsightBadge({ access, isPremium }: { access: MatchAccess; isPremium: boolean }) {
  const { t } = useLanguage()

  if (isPremium) return null

  if (access === "free") {
    return (
      <span className="inline-flex shrink-0 items-center gap-1 rounded-full border border-[#00FF87]/30 bg-[#00FF87]/10 px-2.5 py-1 text-[10px] font-bold uppercase tracking-wide text-[#00FF87]">
        <Sparkles className="h-3 w-3" />
        {t.feed.free}
      </span>
    )
  }

  if (access === "premium") {
    return (
      <span className="inline-flex shrink-0 items-center gap-1 rounded-full border border-[#D8B866]/30 bg-[#D8B866]/8 px-2.5 py-1 text-[10px] font-bold uppercase tracking-wide text-[#E8D39A]">
        <Sparkles className="h-3 w-3" />
        {t.feed.proUnlocked}
      </span>
    )
  }

  return (
    <span className="inline-flex shrink-0 items-center gap-1 rounded-full border border-[#D8B866]/30 bg-[#D8B866]/8 px-2.5 py-1 text-[10px] font-bold uppercase tracking-wide text-[#E8D39A]">
      <Crown className="h-3 w-3" />
      {t.feed.pass}
    </span>
  )
}

function UnlockedInsight({
  match,
  hasPick,
  access,
  isPremium,
}: {
  match: WorldCupFixture
  hasPick: boolean
  access: MatchAccess
  isPremium: boolean
}) {
  const { t } = useLanguage()
  const { isAdvanced } = usePreferences()
  const isPremiumAccess = access === "premium"
  const isFullAccess = isPremium && isPremiumAccess

  return (
    <div className="grid grid-cols-[1fr_auto] items-center gap-3">
      <div className="min-w-0">
        <p className="text-xs font-semibold leading-snug text-foreground">
          {match.pick ?? (isFullAccess ? t.feed.fullInsight : isPremiumAccess ? t.feed.proInsightUnlocked : t.feed.freeInsight)}
        </p>
        <p className="mt-1 line-clamp-2 text-[11px] leading-relaxed text-[#6A7A9B]">
          {match.coach_summary ??
            (hasPick
              ? t.feed.coachAvailable
              : isFullAccess
                ? t.feed.fullFixture
                : isPremiumAccess
                ? t.feed.premiumFixture
                : t.feed.unlockedFixture)}
        </p>
      </div>
      <div className="flex min-w-[74px] flex-col items-end">
        <span className="text-[10px] font-semibold uppercase tracking-wide text-[#6A7A9B]">
          {t.feed.confidence}
        </span>
        <span className="text-sm font-bold text-[#00FF87]">
          {match.confidence_score ? `${match.confidence_score}/10` : t.feed.open}
        </span>
        {isAdvanced && typeof match.edge === "number" && (
          <span className="text-[10px] font-semibold text-[#00FF87]">
            {match.edge > 0 ? "+" : ""}
            {match.edge.toFixed(1)}% {t.feed.edge}
          </span>
        )}
      </div>
    </div>
  )
}

function BookmakerPanel({
  odds,
  homeTeam,
  awayTeam,
  access,
}: {
  odds: OddsMatch | null
  homeTeam: string
  awayTeam: string
  access: MatchAccess
}) {
  const { language, t } = useLanguage()
  const { isBeginner, isAdvanced } = usePreferences()
  const home = findOutcome(odds?.h2h ?? [], homeTeam)
  const away = findOutcome(odds?.h2h ?? [], awayTeam)
  const draw = odds?.h2h.find((row) => row.outcome_name === "Draw") ?? null
  const favorite = getFavorite([home, draw, away])
  const hasExpandedMarkets = Boolean((odds?.featured_markets.totals?.length ?? 0) + (odds?.featured_markets.spreads?.length ?? 0))

  if (access === "locked") {
    return (
      <div className="rounded-lg border border-[#D8B866]/25 bg-[#071022] px-3 py-3">
        <div className="flex items-start gap-2">
          <Lock className="mt-0.5 h-3.5 w-3.5 shrink-0 text-[#E8D39A]" />
          <div className="min-w-0">
            <p className="text-[11px] font-semibold uppercase tracking-wide text-[#E8D39A]">{t.feed.bookmakerOdds}</p>
            <p className="mt-1 text-xs leading-relaxed text-[#A8B4D0]">{t.feed.lockedCopy}</p>
          </div>
        </div>
      </div>
    )
  }

  if (!odds || odds.h2h.length === 0) {
    return (
      <div className="rounded-lg border border-dashed border-[#1A2845] px-3 py-3">
        <p className="text-[11px] font-semibold uppercase tracking-wide text-[#6A7A9B]">{t.feed.bookmakerOdds}</p>
        <p className="mt-1 text-xs leading-relaxed text-[#A8B4D0]">{t.feed.noBookmakerOdds}</p>
      </div>
    )
  }

  return (
    <div className="rounded-lg border border-[#1A2845] bg-[#071022]">
      <div className="flex items-center justify-between gap-3 border-b border-[#1A2845] px-3 py-2.5">
        <div className="flex min-w-0 items-center gap-2">
          <TrendingUp className="h-3.5 w-3.5 shrink-0 text-[#00FF87]" />
          <div className="min-w-0">
            <p className="text-[11px] font-bold uppercase tracking-wide text-[#A8B4D0]">{t.feed.bookmakerOdds}</p>
            <p className="line-clamp-1 text-[10px] text-[#6A7A9B]">
              {favorite?.outcome_name ? `${t.feed.marketFavorite} ${formatOutcomeName(favorite.outcome_name, language)}` : t.feed.marketSnapshot}
            </p>
          </div>
        </div>
        <div className="shrink-0 text-right">
          <p className="text-[9px] font-semibold uppercase tracking-wide text-[#6A7A9B]">{t.feed.updated}</p>
          <p className="text-[10px] font-semibold leading-tight text-[#A8B4D0]">{formatShortDate(odds.last_fetched_at, language, t.feed.noValue)}</p>
        </div>
      </div>

      {favorite && (
        <div className="flex items-center justify-between gap-3 px-3 py-2.5">
          <div className="min-w-0">
            <p className="text-[10px] font-semibold uppercase tracking-wide text-[#6A7A9B]">{t.feed.marketFavorite}</p>
            <p className="truncate text-sm font-bold text-foreground">{formatOutcomeName(favorite.outcome_name, language)}</p>
          </div>
          <div className="shrink-0 text-right">
            <p className="text-[10px] font-semibold uppercase tracking-wide text-[#6A7A9B]">
              <ConceptTip concept="bestPrice" label={t.feed.bestPrice} subtle />
            </p>
            <p className="text-sm font-bold text-[#00FF87]">{formatPrice(favorite.best_price, t.feed.noValue)}</p>
          </div>
        </div>
      )}

      {!isBeginner && (
        <div className="grid grid-cols-3 divide-x divide-[#1A2845] border-t border-[#1A2845]">
          <PriceCell label={displayTeamName(homeTeam, language)} row={home} highlighted={favorite === home} />
          <PriceCell label={t.feed.draw} row={draw} highlighted={favorite === draw} />
          <PriceCell label={displayTeamName(awayTeam, language)} row={away} highlighted={favorite === away} />
        </div>
      )}

      {favorite && !isBeginner && (
        <div className="grid grid-cols-3 gap-2 border-t border-[#1A2845] px-3 py-2.5">
          <MiniMetric label={t.feed.bestPrice} value={formatPrice(favorite.best_price, t.feed.noValue)} accent="text-[#00FF87]" concept="bestPrice" />
          <MiniMetric label={t.feed.fairProbability} value={formatPercent(favorite.no_vig_probability, t.feed.noValue)} concept="fairProbability" />
          <MiniMetric label={t.feed.bookmakers} value={formatBookmakerCount(favorite.bookmaker_count, t.feed.noValue)} />
        </div>
      )}

      {(isBeginner || hasExpandedMarkets) && (
        <details className="group border-t border-[#1A2845]" open={isAdvanced}>
          <summary className="flex cursor-pointer list-none items-center justify-between px-3 py-2.5 text-[11px] font-semibold text-[#A8B4D0] transition-colors hover:text-foreground">
            <span>{isBeginner ? t.feed.details : t.feed.moreMarkets}</span>
            <ChevronDown className="h-3.5 w-3.5 transition-transform group-open:rotate-180" />
          </summary>
          <div className="space-y-3 px-3 pb-3">
            {isBeginner && (
              <>
                <div className="grid grid-cols-3 divide-x divide-[#1A2845] overflow-hidden rounded-lg border border-[#1A2845]">
                  <PriceCell label={displayTeamName(homeTeam, language)} row={home} highlighted={favorite === home} />
                  <PriceCell label={t.feed.draw} row={draw} highlighted={favorite === draw} />
                  <PriceCell label={displayTeamName(awayTeam, language)} row={away} highlighted={favorite === away} />
                </div>
                {favorite && (
                  <div className="grid grid-cols-3 gap-2">
                    <MiniMetric label={t.feed.bestPrice} value={formatPrice(favorite.best_price, t.feed.noValue)} accent="text-[#00FF87]" concept="bestPrice" />
                    <MiniMetric label={t.feed.fairProbability} value={formatPercent(favorite.no_vig_probability, t.feed.noValue)} concept="fairProbability" />
                    <MiniMetric label={t.feed.bookmakers} value={formatBookmakerCount(favorite.bookmaker_count, t.feed.noValue)} />
                  </div>
                )}
              </>
            )}
            {hasExpandedMarkets && (
              <>
                <MarketRows title={t.feed.totals} rows={odds.featured_markets.totals ?? []} language={language} emptyLabel={t.feed.noValue} />
                <MarketRows title={t.feed.handicap} rows={odds.featured_markets.spreads ?? []} language={language} emptyLabel={t.feed.noValue} />
              </>
            )}
          </div>
        </details>
      )}
    </div>
  )
}

function PriceCell({
  label,
  row,
  highlighted,
}: {
  label: string
  row: OddsConsensusRow | null
  highlighted: boolean
}) {
  const { t } = useLanguage()

  return (
    <div className={`min-w-0 px-1.5 py-2.5 text-center ${highlighted ? "bg-[#00FF87]/8" : ""}`}>
      <p className="line-clamp-2 min-h-[24px] text-[10px] font-semibold leading-tight text-[#6A7A9B]">{label}</p>
      <p className={`mt-1 text-sm font-bold ${highlighted ? "text-[#00FF87]" : "text-foreground"}`}>
        {formatPrice(row?.best_price ?? null, t.feed.noValue)}
      </p>
      <p className="mt-0.5 truncate text-[9px] text-[#6A7A9B]">{row?.best_bookmaker_title ?? t.feed.noValue}</p>
    </div>
  )
}

function MarketRows({
  title,
  rows,
  language,
  emptyLabel,
}: {
  title: string
  rows: OddsConsensusRow[]
  language: "en" | "es"
  emptyLabel: string
}) {
  if (rows.length === 0) return null

  return (
    <div>
      <p className="mb-1.5 text-[10px] font-bold uppercase tracking-wide text-[#6A7A9B]">{title}</p>
      <div className="grid grid-cols-2 gap-2">
        {rows.slice(0, 6).map((row, index) => (
          <div key={`${row.market_key}-${row.outcome_name}-${row.point}-${index}`} className="min-w-0 rounded-md border border-[#1A2845] bg-[#0A1325] px-2.5 py-2">
            <div className="flex items-center justify-between gap-2">
              <p className="truncate text-[11px] font-semibold text-foreground">
                {formatOutcomeName(row.outcome_name, language)}
                {row.point !== null ? ` ${formatPoint(row.point)}` : ""}
              </p>
              <p className="shrink-0 text-xs font-bold text-[#00FF87]">{formatPrice(row.best_price, emptyLabel)}</p>
            </div>
            <p className="mt-1 truncate text-[9px] text-[#6A7A9B]">
              {formatPercent(row.no_vig_probability, emptyLabel)} · {formatBookmakerCount(row.bookmaker_count, emptyLabel)}
            </p>
          </div>
        ))}
      </div>
    </div>
  )
}

function MiniMetric({
  label,
  value,
  accent = "text-foreground",
  concept,
}: {
  label: string
  value: string
  accent?: string
  concept?: "bestPrice" | "fairProbability"
}) {
  return (
    <div className="min-w-0">
      <p className="truncate text-[9px] font-semibold uppercase tracking-wide text-[#6A7A9B]">
        {concept ? <ConceptTip concept={concept} label={label} subtle /> : label}
      </p>
      <p className={`mt-0.5 truncate text-xs font-bold ${accent}`}>{value}</p>
    </div>
  )
}

function LockedInsight() {
  const { t } = useLanguage()

  return (
    <div className="grid grid-cols-[1fr_auto] items-center gap-3">
      <div className="min-w-0">
        <p className="truncate text-xs font-semibold text-foreground">
          {t.feed.proInsight}
        </p>
        <p className="mt-1 text-[11px] leading-relaxed text-[#6A7A9B]">
          {t.feed.lockedCopy}
        </p>
      </div>
      <div className="flex min-w-[74px] flex-col items-end">
        <span className="text-[10px] font-semibold uppercase tracking-wide text-[#6A7A9B]">
          {t.feed.confidence}
        </span>
        <span className="inline-flex items-center gap-1 text-sm font-bold text-[#E8D39A]">
          <Lock className="h-3.5 w-3.5" />
          {t.feed.locked}
        </span>
      </div>
    </div>
  )
}

function StatCell({
  label,
  value,
  accent = "text-foreground",
  onClick,
}: {
  label: string
  value: string
  accent?: string
  onClick?: () => void
}) {
  if (onClick) {
    return (
      <button
        type="button"
        onClick={onClick}
        className="border-r border-[#1A2845] px-2 py-3 text-center transition-colors last:border-r-0 hover:bg-[#D8B866]/5"
      >
        <p className="mb-0.5 text-[10px] uppercase tracking-wider text-[#6A7A9B]">{label}</p>
        <p className={`text-lg font-bold ${accent}`}>{value}</p>
      </button>
    )
  }

  return (
    <div className="border-r border-[#1A2845] px-2 py-3 text-center last:border-r-0">
      <p className="mb-0.5 text-[10px] uppercase tracking-wider text-[#6A7A9B]">{label}</p>
      <p className={`text-lg font-bold ${accent}`}>{value}</p>
    </div>
  )
}

function PremiumSummaryBanner({
  eyebrow,
  title,
  value,
  valueLabel,
  detail,
}: {
  eyebrow: string
  title: string
  value: string
  valueLabel: string
  detail: string
}) {
  return (
    <div className="mx-4 mb-4 flex shrink-0 items-center justify-between gap-4 rounded-xl border border-[#1A2845] bg-[#0F1C35] px-4 py-3.5 sm:mx-5">
      <div className="min-w-0">
        <div className="mb-1 inline-flex items-center gap-1.5 rounded-full border border-[#D8B866]/25 bg-[#D8B866]/8 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide text-[#E8D39A]">
          <Crown className="h-3 w-3" />
          {eyebrow}
        </div>
        <p className="truncate text-sm font-bold text-foreground">{title}</p>
        <p className="mt-0.5 text-xs leading-relaxed text-[#6A7A9B]">{detail}</p>
      </div>
      <div className="shrink-0 text-right">
        <p className="text-3xl font-black leading-none text-[#00FF87]">{value}</p>
        <p className="mt-1 text-[10px] font-semibold uppercase tracking-wide text-[#6A7A9B]">{valueLabel}</p>
      </div>
    </div>
  )
}

function LoadingMatches() {
  return (
    <>
      {[0, 1, 2, 3].map((item) => (
        <div key={item} className="rounded-xl border border-[#1A2845] bg-card p-4">
          <div className="flex gap-3">
            <div className="h-14 w-[54px] animate-pulse rounded-lg bg-[#111E38]" />
            <div className="flex-1 space-y-2">
              <div className="h-4 w-2/3 animate-pulse rounded bg-[#111E38]" />
              <div className="h-4 w-1/2 animate-pulse rounded bg-[#111E38]" />
              <div className="h-3 w-5/6 animate-pulse rounded bg-[#111E38]" />
            </div>
          </div>
        </div>
      ))}
    </>
  )
}

function ErrorState({ message, onRetry }: { message: string; onRetry: () => void }) {
  const { t } = useLanguage()

  return (
    <div className="rounded-xl border border-[#FF4D4D]/30 bg-[#FF4D4D]/10 p-4">
      <div className="flex items-start gap-3">
        <AlertCircle className="mt-0.5 h-5 w-5 shrink-0 text-[#FF4D4D]" />
        <div className="min-w-0 flex-1">
          <p className="text-sm font-semibold text-foreground">{t.feed.unavailable}</p>
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

function EmptyState() {
  const { t } = useLanguage()

  return (
    <div className="rounded-xl border border-[#1A2845] bg-card p-5 text-center">
      <Clock className="mx-auto h-6 w-6 text-[#6A7A9B]" />
      <p className="mt-3 text-sm font-semibold text-foreground">{t.feed.emptyTitle}</p>
      <p className="mt-1 text-xs leading-relaxed text-[#6A7A9B]">
        {t.feed.emptyCopy}
      </p>
    </div>
  )
}

function getMatchAccess(match: WorldCupFixture, index: number, isPremium: boolean): MatchAccess {
  if (isFreeMatch(match, index)) return "free"
  return isPremium ? "premium" : "locked"
}

function isFreeMatch(match: WorldCupFixture, index: number) {
  if (match.access === "free") return true
  if (match.access === "locked") return false
  return index < 2
}

function parseKickoff(value: string | null) {
  if (!value) return null
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? null : date
}

function getKickoffTimestamp(match: WorldCupFixture) {
  const date = parseKickoff(match.kickoff_time)
  return date ? date.getTime() : Number.POSITIVE_INFINITY
}

function findOddsForFixture(match: WorldCupFixture, oddsMatches: OddsMatch[]) {
  const key = fixtureKey(match.home_team, match.away_team, match.kickoff_time)
  return oddsMatches.find((odds) => fixtureKey(odds.home_team, odds.away_team, odds.commence_time) === key) ?? null
}

function fixtureKey(homeTeam: string | null, awayTeam: string | null, kickoffTime: string | null) {
  const teams = [homeTeam, awayTeam].map(normalizeTeam).sort().join("|")
  return `${teams}|${(kickoffTime ?? "").slice(0, 10)}`
}

function normalizeTeam(value: string | null) {
  return (value ?? "")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, " ")
    .trim()
}

function formatPrice(value: number | null, fallback: string) {
  return typeof value === "number" ? value.toFixed(2) : fallback
}

function formatPercent(value: number | null, fallback: string) {
  return typeof value === "number" ? `${(value * 100).toFixed(1)}%` : fallback
}

function findOutcome(rows: OddsConsensusRow[], team: string) {
  const normalized = normalizeTeam(team)
  return rows.find((row) => normalizeTeam(row.outcome_name) === normalized) ?? null
}

function getFavorite(rows: Array<OddsConsensusRow | null>) {
  return rows
    .filter((row): row is OddsConsensusRow => Boolean(row))
    .sort((a, b) => (b.no_vig_probability ?? 0) - (a.no_vig_probability ?? 0))[0] ?? null
}

function formatOutcomeName(value: string | null, language: "en" | "es") {
  if (!value) return ""
  if (value === "Draw") return language === "es" ? "Empate" : "Draw"
  if (value === "Over") return language === "es" ? "Más de" : "Over"
  if (value === "Under") return language === "es" ? "Menos de" : "Under"
  return displayTeamName(value, language)
}

function formatPoint(value: number) {
  return Number.isInteger(value) ? value.toFixed(0) : value.toFixed(2).replace(/0$/, "")
}

function formatBookmakerCount(value: number, fallback: string) {
  return value > 0 ? value.toString() : fallback
}

function formatShortDate(value: string | null, language: "en" | "es", fallback: string) {
  if (!value) return fallback
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return fallback
  return new Intl.DateTimeFormat(language === "es" ? "es-ES" : "en-US", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date)
}

function buildCoachPrompt(
  match: WorldCupFixture,
  odds: OddsMatch | null,
  homeTeam: string,
  awayTeam: string,
  language: "en" | "es"
) {
  const matchName = `${displayTeamName(homeTeam, language)} vs ${displayTeamName(awayTeam, language)}`
  const stageText = match.stage ? ` (${match.stage})` : ""
  const h2hRows = [
    findOutcome(odds?.h2h ?? [], homeTeam),
    odds?.h2h.find((row) => row.outcome_name === "Draw") ?? null,
    findOutcome(odds?.h2h ?? [], awayTeam),
  ].filter((row): row is OddsConsensusRow => Boolean(row))
  const h2hText = h2hRows
    .map((row) => {
      const label = formatOutcomeName(row.outcome_name, language)
      const price = formatPrice(row.best_price, "")
      const probability = formatPercent(row.no_vig_probability, "")
      return `${label}${price ? ` @ ${price}` : ""}${probability ? ` (${probability})` : ""}`
    })
    .join(", ")

  if (language === "es") {
    return h2hText
      ? `Analiza este partido del Feed: ${matchName}${stageText}. Las cuotas de la app muestran las mejores cuotas cacheadas por resultado: ${h2hText}. Dime primero si estos precios están bien comprados frente al mercado, luego si hay valor real, qué cuota mínima buscarías para entrar y qué evitarías.`
      : `Analiza este partido del Feed: ${matchName}${stageText}. No tengo una cuota elegida todavía. ¿Qué mercados mirarías primero, qué precio mínimo buscarías y qué evitarías?`
  }

  return h2hText
    ? `Analyze this Feed match: ${matchName}${stageText}. The in-app odds board shows the best cached prices by outcome: ${h2hText}. First tell me whether these are well-bought prices versus the market, then whether there is real value, what minimum price you would want before entering, and what you would avoid.`
    : `Analyze this Feed match: ${matchName}${stageText}. I have not picked specific odds yet. Which markets would you inspect first, what minimum price would you want, and what would you avoid?`
}

function formatUpdatedAt(
  value: Date | null,
  timeFormatter: Intl.DateTimeFormat,
  updatedLabel: string,
  liveLabel: string
) {
  if (!value) return liveLabel
  return `${updatedLabel} ${timeFormatter.format(value)}`
}
