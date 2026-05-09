"use client"

import { useEffect, useMemo, useState } from "react"
import { AlertCircle, CalendarDays, Clock, Lock, RefreshCw, Sparkles } from "lucide-react"
import { getWorldCupFixtures, type WorldCupFixture } from "@/lib/api"
import { displayTeamName, flagForTeam } from "@/lib/country-flags"
import { useLanguage } from "@/lib/i18n"

type FeedState = {
  matches: WorldCupFixture[]
  lastUpdated: Date | null
}

export default function DailyFeed({ isPremium }: { isPremium: boolean }) {
  const { language, t } = useLanguage()
  const [feed, setFeed] = useState<FeedState>({ matches: [], lastUpdated: null })
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
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

  const loadFixtures = async () => {
    setIsLoading(true)
    setError(null)

    try {
      const result = await getWorldCupFixtures()
      setFeed({
        matches: result.matches,
        lastUpdated: new Date(),
      })
    } catch (err) {
      setError(err instanceof Error ? err.message : t.feed.loadError)
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    void loadFixtures()
  }, [])

  const sortedMatches = useMemo(() => {
    const now = Date.now()
    const byKickoff = [...feed.matches].sort((a, b) => {
      return getKickoffTimestamp(a) - getKickoffTimestamp(b)
    })
    const upcoming = byKickoff.filter((match) => {
      const kickoff = getKickoffTimestamp(match)
      return !Number.isFinite(kickoff) || kickoff >= now
    })

    return upcoming.length > 0 ? upcoming : byKickoff
  }, [feed.matches])

  const freeInsightCount = Math.min(sortedMatches.length, 2)
  const proInsightCount = Math.max(sortedMatches.length - freeInsightCount, 0)

  return (
    <div className="flex h-full flex-col overflow-y-auto">
      <div className="flex-shrink-0 px-5 pb-4 pt-6">
        <p className="mb-1 text-xs font-medium uppercase tracking-widest text-[#6A7A9B]">
          {today}
        </p>
        <h1 className="text-2xl font-bold tracking-tight text-foreground">
          {t.feed.title}
        </h1>
        <div className="mt-2 flex items-center gap-2">
          <div className="h-1.5 w-1.5 rounded-full bg-[#00FF87] animate-pulse" />
          <span className="text-xs text-[#6A7A9B]">
            {formatUpdatedAt(feed.lastUpdated, timeFormatter, t.feed.updated, t.feed.liveFixtureList)}
          </span>
        </div>
      </div>

      <div className="mx-5 mb-5 grid flex-shrink-0 grid-cols-3 overflow-hidden rounded-xl border border-[#1A2845] bg-[#0F1C35]">
        <StatCell label={t.feed.upcoming} value={sortedMatches.length.toString()} />
        <StatCell label={t.feed.free} value={freeInsightCount.toString()} accent="text-[#00FF87]" />
        <StatCell label={t.feed.pro} value={proInsightCount.toString()} accent="text-[#FFD600]" />
      </div>

      <div className="flex flex-col gap-3 px-5 pb-6">
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
  dateFormatter,
  timeFormatter,
}: {
  match: WorldCupFixture
  access: MatchAccess
  dateFormatter: Intl.DateTimeFormat
  timeFormatter: Intl.DateTimeFormat
}) {
  const { t } = useLanguage()
  const homeTeam = match.home_team ?? match.match.split(" vs ")[0] ?? "Home"
  const awayTeam = match.away_team ?? match.match.split(" vs ")[1] ?? "Away"
  const kickoff = parseKickoff(match.kickoff_time)
  const hasPick = Boolean(match.pick || match.confidence_score || match.edge)

  return (
    <article className="overflow-hidden rounded-xl border border-[#1A2845] bg-card">
      <div className="flex items-start gap-3 px-4 py-4">
        <div className="flex w-[54px] shrink-0 flex-col items-center rounded-lg border border-[#1A2845] bg-[#0A1325] px-2 py-2 text-center">
          <span className="text-[10px] font-semibold uppercase tracking-wide text-[#6A7A9B]">
            {kickoff ? dateFormatter.format(kickoff).split(" ")[0] : t.feed.tbd}
          </span>
          <span className="mt-1 text-sm font-bold text-foreground">
            {kickoff ? timeFormatter.format(kickoff) : "--:--"}
          </span>
        </div>

        <div className="min-w-0 flex-1">
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0">
              <TeamLine name={homeTeam} />
              <TeamLine name={awayTeam} />
            </div>
            <InsightBadge access={access} />
          </div>

          <div className="mt-3 flex flex-wrap items-center gap-x-3 gap-y-1 text-[11px] text-[#6A7A9B]">
            <span className="inline-flex items-center gap-1">
              <CalendarDays className="h-3 w-3" />
              {kickoff ? dateFormatter.format(kickoff) : t.feed.datePending}
            </span>
            {match.stage && <span>{match.stage}</span>}
            {match.venue && <span>{match.venue}</span>}
          </div>
        </div>
      </div>

      <div className="border-t border-[#1A2845] bg-[#0A1325]/70 px-4 py-3">
        {access === "locked" ? (
          <LockedInsight teaser={match.teaser} />
        ) : (
          <UnlockedInsight match={match} hasPick={hasPick} access={access} />
        )}
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

function InsightBadge({ access }: { access: MatchAccess }) {
  const { t } = useLanguage()

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
      <span className="inline-flex shrink-0 items-center gap-1 rounded-full border border-[#FFD600]/30 bg-[#FFD600]/10 px-2.5 py-1 text-[10px] font-bold uppercase tracking-wide text-[#FFD600]">
        <Sparkles className="h-3 w-3" />
        {t.feed.proUnlocked}
      </span>
    )
  }

  return (
    <span className="inline-flex shrink-0 items-center gap-1 rounded-full border border-[#FFD600]/30 bg-[#FFD600]/10 px-2.5 py-1 text-[10px] font-bold uppercase tracking-wide text-[#FFD600]">
      <Lock className="h-3 w-3" />
      {t.feed.pro}
    </span>
  )
}

function UnlockedInsight({
  match,
  hasPick,
  access,
}: {
  match: WorldCupFixture
  hasPick: boolean
  access: MatchAccess
}) {
  const { t } = useLanguage()
  const isPremiumAccess = access === "premium"

  return (
    <div className="grid grid-cols-[1fr_auto] items-center gap-3">
      <div className="min-w-0">
        <p className="truncate text-xs font-semibold text-foreground">
          {match.pick ?? (isPremiumAccess ? t.feed.proInsightUnlocked : t.feed.freeInsight)}
        </p>
        <p className="mt-1 line-clamp-2 text-[11px] leading-relaxed text-[#6A7A9B]">
          {match.coach_summary ??
            (hasPick
              ? t.feed.coachAvailable
              : isPremiumAccess
                ? t.feed.premiumFixture
                : t.feed.unlockedFixture)}
        </p>
      </div>
      <div className="flex min-w-[74px] flex-col items-end">
        <span className="text-[10px] font-semibold uppercase tracking-wide text-[#6A7A9B]">
          {t.feed.confidence}
        </span>
        <span className={`text-sm font-bold ${isPremiumAccess ? "text-[#FFD600]" : "text-[#00FF87]"}`}>
          {match.confidence_score ? `${match.confidence_score}/10` : t.feed.open}
        </span>
        {typeof match.edge === "number" && (
          <span className="text-[10px] font-semibold text-[#00FF87]">
            {match.edge > 0 ? "+" : ""}
            {match.edge.toFixed(1)}% {t.feed.edge}
          </span>
        )}
      </div>
    </div>
  )
}

function LockedInsight({ teaser }: { teaser?: string | null }) {
  const { t } = useLanguage()

  return (
    <div className="grid grid-cols-[1fr_auto] items-center gap-3">
      <div className="min-w-0">
        <p className="truncate text-xs font-semibold text-foreground">
          {teaser ?? t.feed.proInsight}
        </p>
        <p className="mt-1 text-[11px] leading-relaxed text-[#6A7A9B]">
          {t.feed.lockedCopy}
        </p>
      </div>
      <div className="flex min-w-[74px] flex-col items-end">
        <span className="text-[10px] font-semibold uppercase tracking-wide text-[#6A7A9B]">
          {t.feed.confidence}
        </span>
        <span className="inline-flex items-center gap-1 text-sm font-bold text-[#FFD600]">
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

function formatUpdatedAt(
  value: Date | null,
  timeFormatter: Intl.DateTimeFormat,
  updatedLabel: string,
  liveLabel: string
) {
  if (!value) return liveLabel
  return `${updatedLabel} ${timeFormatter.format(value)}`
}
