"use client"

import { useEffect, useMemo, useState } from "react"
import { AlertCircle, CalendarDays, Clock, Lock, RefreshCw, Sparkles } from "lucide-react"
import { getWorldCupFixtures, type WorldCupFixture } from "@/lib/api"
import { flagForTeam } from "@/lib/country-flags"

type FeedState = {
  matches: WorldCupFixture[]
  lastUpdated: Date | null
}

const dateFormatter = new Intl.DateTimeFormat("en-US", {
  weekday: "short",
  month: "short",
  day: "numeric",
})

const timeFormatter = new Intl.DateTimeFormat("en-US", {
  hour: "2-digit",
  minute: "2-digit",
})

const today = new Date().toLocaleDateString("en-US", {
  weekday: "long",
  month: "long",
  day: "numeric",
})

export default function DailyFeed() {
  const [feed, setFeed] = useState<FeedState>({ matches: [], lastUpdated: null })
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

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
      setError(err instanceof Error ? err.message : "Unable to load matches.")
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
  const lockedInsightCount = Math.max(sortedMatches.length - freeInsightCount, 0)

  return (
    <div className="flex h-full flex-col overflow-y-auto">
      <div className="flex-shrink-0 px-5 pb-4 pt-6">
        <p className="mb-1 text-xs font-medium uppercase tracking-widest text-[#6A7A9B]">
          {today}
        </p>
        <h1 className="text-2xl font-bold tracking-tight text-foreground">
          Match Radar
        </h1>
        <div className="mt-2 flex items-center gap-2">
          <div className="h-1.5 w-1.5 rounded-full bg-[#00FF87] animate-pulse" />
          <span className="text-xs text-[#6A7A9B]">
            {formatUpdatedAt(feed.lastUpdated)}
          </span>
        </div>
      </div>

      <div className="mx-5 mb-5 grid flex-shrink-0 grid-cols-3 overflow-hidden rounded-xl border border-[#1A2845] bg-[#0F1C35]">
        <StatCell label="Upcoming" value={sortedMatches.length.toString()} />
        <StatCell label="Free" value={freeInsightCount.toString()} accent="text-[#00FF87]" />
        <StatCell label="Pro" value={lockedInsightCount.toString()} accent="text-[#FFD600]" />
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
              isFreeInsight={isFreeMatch(match, index)}
            />
          ))
        )}
      </div>
    </div>
  )
}

function MatchRow({
  match,
  isFreeInsight,
}: {
  match: WorldCupFixture
  isFreeInsight: boolean
}) {
  const homeTeam = match.home_team ?? match.match.split(" vs ")[0] ?? "Home"
  const awayTeam = match.away_team ?? match.match.split(" vs ")[1] ?? "Away"
  const kickoff = parseKickoff(match.kickoff_time)
  const hasPick = Boolean(match.pick || match.confidence_score || match.edge)

  return (
    <article className="overflow-hidden rounded-xl border border-[#1A2845] bg-card">
      <div className="flex items-start gap-3 px-4 py-4">
        <div className="flex w-[54px] shrink-0 flex-col items-center rounded-lg border border-[#1A2845] bg-[#0A1325] px-2 py-2 text-center">
          <span className="text-[10px] font-semibold uppercase tracking-wide text-[#6A7A9B]">
            {kickoff ? dateFormatter.format(kickoff).split(" ")[0] : "TBD"}
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
            <InsightBadge isFreeInsight={isFreeInsight} />
          </div>

          <div className="mt-3 flex flex-wrap items-center gap-x-3 gap-y-1 text-[11px] text-[#6A7A9B]">
            <span className="inline-flex items-center gap-1">
              <CalendarDays className="h-3 w-3" />
              {kickoff ? dateFormatter.format(kickoff) : "Date pending"}
            </span>
            {match.stage && <span>{match.stage}</span>}
            {match.venue && <span>{match.venue}</span>}
          </div>
        </div>
      </div>

      <div className="border-t border-[#1A2845] bg-[#0A1325]/70 px-4 py-3">
        {isFreeInsight ? (
          <UnlockedInsight match={match} hasPick={hasPick} />
        ) : (
          <LockedInsight teaser={match.teaser} />
        )}
      </div>
    </article>
  )
}

function TeamLine({ name }: { name: string }) {
  return (
    <div className="flex min-w-0 items-center gap-2 py-0.5">
      <span className="w-5 shrink-0 text-lg leading-none">{flagForTeam(name)}</span>
      <span className="truncate text-sm font-semibold text-foreground">{name}</span>
    </div>
  )
}

function InsightBadge({ isFreeInsight }: { isFreeInsight: boolean }) {
  if (isFreeInsight) {
    return (
      <span className="inline-flex shrink-0 items-center gap-1 rounded-full border border-[#00FF87]/30 bg-[#00FF87]/10 px-2.5 py-1 text-[10px] font-bold uppercase tracking-wide text-[#00FF87]">
        <Sparkles className="h-3 w-3" />
        Free
      </span>
    )
  }

  return (
    <span className="inline-flex shrink-0 items-center gap-1 rounded-full border border-[#FFD600]/30 bg-[#FFD600]/10 px-2.5 py-1 text-[10px] font-bold uppercase tracking-wide text-[#FFD600]">
      <Lock className="h-3 w-3" />
      Pro
    </span>
  )
}

function UnlockedInsight({
  match,
  hasPick,
}: {
  match: WorldCupFixture
  hasPick: boolean
}) {
  return (
    <div className="grid grid-cols-[1fr_auto] items-center gap-3">
      <div className="min-w-0">
        <p className="truncate text-xs font-semibold text-foreground">
          {match.pick ?? "Free match insight"}
        </p>
        <p className="mt-1 line-clamp-2 text-[11px] leading-relaxed text-[#6A7A9B]">
          {match.coach_summary ??
            (hasPick
              ? "Coach analysis is available for this match."
              : "Fixture unlocked. Confidence and edge will appear here when market data is attached.")}
        </p>
      </div>
      <div className="flex min-w-[74px] flex-col items-end">
        <span className="text-[10px] font-semibold uppercase tracking-wide text-[#6A7A9B]">
          Confidence
        </span>
        <span className="text-sm font-bold text-[#00FF87]">
          {match.confidence_score ? `${match.confidence_score}/10` : "Open"}
        </span>
        {typeof match.edge === "number" && (
          <span className="text-[10px] font-semibold text-[#00FF87]">
            {match.edge > 0 ? "+" : ""}
            {match.edge.toFixed(1)}% edge
          </span>
        )}
      </div>
    </div>
  )
}

function LockedInsight({ teaser }: { teaser?: string | null }) {
  return (
    <div className="grid grid-cols-[1fr_auto] items-center gap-3">
      <div className="min-w-0">
        <p className="truncate text-xs font-semibold text-foreground">
          {teaser ?? "Pro insight available"}
        </p>
        <p className="mt-1 text-[11px] leading-relaxed text-[#6A7A9B]">
          Unlock the pick, confidence score, Polymarket edge, and coach take.
        </p>
      </div>
      <div className="flex min-w-[74px] flex-col items-end">
        <span className="text-[10px] font-semibold uppercase tracking-wide text-[#6A7A9B]">
          Confidence
        </span>
        <span className="inline-flex items-center gap-1 text-sm font-bold text-[#FFD600]">
          <Lock className="h-3.5 w-3.5" />
          Locked
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
  return (
    <div className="rounded-xl border border-[#FF4D4D]/30 bg-[#FF4D4D]/10 p-4">
      <div className="flex items-start gap-3">
        <AlertCircle className="mt-0.5 h-5 w-5 shrink-0 text-[#FF4D4D]" />
        <div className="min-w-0 flex-1">
          <p className="text-sm font-semibold text-foreground">Match radar is unavailable</p>
          <p className="mt-1 text-xs leading-relaxed text-[#A8B4D0]">{message}</p>
          <button
            onClick={onRetry}
            className="mt-3 inline-flex items-center gap-1.5 rounded-lg border border-[#1A2845] bg-[#0F1C35] px-3 py-2 text-xs font-semibold text-foreground transition-colors hover:border-[#00FF87]/50"
          >
            <RefreshCw className="h-3.5 w-3.5" />
            Retry
          </button>
        </div>
      </div>
    </div>
  )
}

function EmptyState() {
  return (
    <div className="rounded-xl border border-[#1A2845] bg-card p-5 text-center">
      <Clock className="mx-auto h-6 w-6 text-[#6A7A9B]" />
      <p className="mt-3 text-sm font-semibold text-foreground">No matches loaded yet</p>
      <p className="mt-1 text-xs leading-relaxed text-[#6A7A9B]">
        The radar will fill in as soon as World Cup fixtures are available.
      </p>
    </div>
  )
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

function formatUpdatedAt(value: Date | null) {
  if (!value) return "Live fixture list"
  return `Updated ${timeFormatter.format(value)}`
}
