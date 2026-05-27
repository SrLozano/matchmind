"use client"

import { useState, useRef, useEffect } from "react"
import { Activity, Crown, History, Plus, Send, X, Zap } from "lucide-react"
import {
  getConversation,
  getConversations,
  sendChatMessage,
  type ChatMarketSignal,
  type ChatResponse,
  type ConversationSummary,
  type CurrentUser,
} from "@/lib/api"
import { useLanguage } from "@/lib/i18n"
import { usePreferences } from "@/lib/preferences"
import { ConceptTip } from "./ConceptTip"

type Message = {
  id: number
  role: "coach" | "user"
  text: string
  confidenceScore?: number | null
  verdict?: string | null
  impliedProbability?: number | null
  stakePosture?: string | null
  marketSignal?: ChatMarketSignal | null
}

export default function ChatCoach({
  currentUser,
  draftPrompt,
  onChatUsageUpdate,
  onShowUpgradePrompt,
}: {
  currentUser: CurrentUser | null
  draftPrompt: { id: number; text: string } | null
  onChatUsageUpdate: (result: ChatResponse) => void
  onShowUpgradePrompt: () => void
}) {
  const { language, t } = useLanguage()
  const { isBeginner, isAdvanced } = usePreferences()
  const getInitialMessages = () => [
    {
      id: 1,
      role: "coach" as const,
      text: t.chat.initialCoach,
    },
  ]
  const [messages, setMessages] = useState<Message[]>(getInitialMessages)
  const [input, setInput] = useState("")
  const [isSending, setIsSending] = useState(false)
  const [conversationId, setConversationId] = useState<string | null>(null)
  const [historyOpen, setHistoryOpen] = useState(false)
  const [history, setHistory] = useState<ConversationSummary[]>([])
  const [isLoadingHistory, setIsLoadingHistory] = useState(false)
  const [historyError, setHistoryError] = useState<string | null>(null)
  const bottomRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)
  const hasUserSentMessage = useRef(false)

  useEffect(() => {
    if (!hasUserSentMessage.current) {
      setMessages(getInitialMessages())
    }
  }, [language])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages])

  useEffect(() => {
    if (!draftPrompt?.text) return
    setInput(draftPrompt.text)
    window.setTimeout(() => inputRef.current?.focus(), 80)
  }, [draftPrompt?.id])

  const handleSend = async () => {
    const trimmed = input.trim()
    if (!trimmed || isSending) return
    if (currentUser?.plan === "free" && (currentUser.chats_remaining ?? 0) <= 0) {
      if (currentUser.plan === "free") onShowUpgradePrompt()
      return
    }
    hasUserSentMessage.current = true
    const userMsg: Message = { id: Date.now(), role: "user", text: trimmed }
    const pendingCoachMsg: Message = {
      id: Date.now() + 1,
      role: "coach",
      text: t.chat.pending,
    }
    setMessages((prev) => [...prev, userMsg, pendingCoachMsg])
    setInput("")
    setIsSending(true)

    try {
      const result = await sendChatMessage(trimmed, language, conversationId)
      setConversationId(result.conversation_id)
      onChatUsageUpdate(result)
      if (currentUser?.plan === "free" && (result.chats_remaining ?? 0) <= 0) {
        onShowUpgradePrompt()
      }
      void loadHistory()
      setMessages((prev) =>
        prev.map((message) =>
          message.id === pendingCoachMsg.id
            ? {
                ...message,
                text: result.response,
                confidenceScore: result.confidence_score,
                verdict: result.verdict,
                impliedProbability: result.implied_probability,
                stakePosture: result.stake_posture,
                marketSignal: result.market_signal,
              }
            : message
        )
      )
    } catch (error) {
      const rawErrorMessage = error instanceof Error ? error.message : t.chat.reachError
      const errorMessage =
        currentUser?.plan === "premium" && rawErrorMessage.toLowerCase().includes("limit")
          ? t.chat.temporaryUnavailable
          : rawErrorMessage
      if (currentUser?.plan === "free" && errorMessage.toLowerCase().includes("limit")) {
        onShowUpgradePrompt()
      }
      setMessages((prev) =>
        prev.map((message) =>
          message.id === pendingCoachMsg.id
            ? {
                ...message,
                text: `${t.chat.requestFailed}\n\n${errorMessage}`,
              }
            : message
        )
      )
    } finally {
      setIsSending(false)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") void handleSend()
  }

  const quotaLimit = currentUser?.chat_count_limit ?? currentUser?.daily_chat_count_limit ?? 5
  const quotaRemaining = currentUser?.chats_remaining ?? currentUser?.daily_chats_remaining ?? null
  const quotaPeriod = currentUser?.chat_limit_period ?? "day"
  const isPremium = currentUser?.plan === "premium"
  const isLowFreeQuota = currentUser?.plan === "free" && quotaRemaining !== null && quotaRemaining <= 1
  const quotaLabel =
    isPremium
      ? t.chat.fullAccess
      : quotaRemaining === null
      ? t.chat.dailyLimit
      : `${quotaRemaining}/${quotaLimit}`
  const quotaClass = isLowFreeQuota
    ? "border-[#FF4D4D]/40 bg-[#FF4D4D]/12 text-[#FF6B6B]"
    : isPremium
      ? "border-[#D8B866]/30 bg-[#D8B866]/8 text-[#E8D39A]"
      : "border-[#00FF87]/25 bg-[#00FF87]/10 text-[#00FF87]"
  const quotaTitle = isPremium
    ? t.chat.fullAccess
    : quotaRemaining === null
      ? t.chat.dailyLimit
      : `${quotaRemaining} ${t.chat.left}/${quotaPeriod === "week" ? t.chat.week : t.chat.day}`

  const sendDisabled = !input.trim() || isSending

  const handleExamplePrompt = (prompt: string) => {
    if (isSending) return
    setInput(prompt)
    inputRef.current?.focus()
  }

  const loadHistory = async () => {
    setIsLoadingHistory(true)
    setHistoryError(null)
    try {
      const result = await getConversations()
      setHistory(result.conversations)
    } catch (error) {
      setHistoryError(error instanceof Error ? error.message : t.chat.historyError)
    } finally {
      setIsLoadingHistory(false)
    }
  }

  const toggleHistory = () => {
    const nextOpen = !historyOpen
    setHistoryOpen(nextOpen)
    if (nextOpen) void loadHistory()
  }

  const handleNewChat = () => {
    setConversationId(null)
    setMessages(getInitialMessages())
    setInput("")
    hasUserSentMessage.current = false
    setHistoryOpen(false)
  }

  const handleOpenConversation = async (id: string) => {
    setHistoryError(null)
    try {
      const conversation = await getConversation(id)
      setConversationId(conversation.id)
      hasUserSentMessage.current = true
      setMessages(
        conversation.messages.map((message, index) => ({
          id: index + 1,
          role: message.role === "assistant" ? "coach" : "user",
          text: message.content,
          confidenceScore: message.confidence_score,
          verdict: message.verdict,
          impliedProbability: message.implied_probability,
          stakePosture: message.stake_posture,
        }))
      )
      setHistoryOpen(false)
    } catch (error) {
      setHistoryError(error instanceof Error ? error.message : t.chat.historyError)
    }
  }

  const renderText = (text: string) => {
    return text.split("\n").map((line, i) => {
      const parts = line.split(/\*\*(.*?)\*\*/g)
      return (
        <p key={i} className={i > 0 ? "mt-1.5" : ""}>
          {parts.map((part, j) =>
            j % 2 === 1 ? (
              <strong key={j} className="font-semibold text-foreground">
                {part}
              </strong>
            ) : (
              part
            )
          )}
        </p>
      )
    })
  }

  const formatPercent = (value: number | null | undefined) => {
    if (value === null || value === undefined) return "—"
    return `${(value * 100).toFixed(1)}%`
  }

  const formatScore = (value: number | null | undefined) => {
    if (value === null || value === undefined) return null
    return Number.isInteger(value) ? value.toFixed(0) : value.toFixed(1)
  }

  const formatVerdict = (value: string | null | undefined) => {
    if (!value) return null
    const labels: Record<string, { en: string; es: string }> = {
      "GOOD VALUE": { en: "Good value", es: "Buen valor" },
      FAIR: { en: "Fair", es: "Justa" },
      RISKY: { en: "Risky", es: "Arriesgada" },
      AVOID: { en: "Avoid", es: "Evitar" },
      "NOT ENOUGH INFO": { en: "Need more info", es: "No hay info suficiente" },
    }
    return labels[value]?.[language] ?? value
  }

  const verdictTone = (value: string | null | undefined) => {
    if (value === "GOOD VALUE") return "border-[#00FF87]/35 bg-[#00FF87]/10 text-[#00FF87]"
    if (value === "FAIR") return "border-[#6A7A9B]/35 bg-[#6A7A9B]/10 text-[#D7DEEF]"
    if (value === "RISKY") return "border-[#FFD600]/35 bg-[#FFD600]/10 text-[#FFD600]"
    if (value === "AVOID") return "border-[#FF5A7A]/35 bg-[#FF5A7A]/10 text-[#FF8AA1]"
    return "border-[#6A7A9B]/35 bg-[#6A7A9B]/10 text-[#D7DEEF]"
  }

  const formatStakePosture = (value: string | null | undefined) => {
    if (!value) return null
    const labels: Record<string, { en: string; es: string }> = {
      avoid: { en: "Avoid", es: "Evitar" },
      "very small": { en: "Very small", es: "Muy pequeño" },
      small: { en: "Small", es: "Pequeño" },
      medium: { en: "Medium", es: "Medio" },
    }
    return labels[value]?.[language] ?? value
  }

  const renderMetadataChips = (message: Message) => {
    if (message.role !== "coach") return null
    const verdict = formatVerdict(message.verdict)
    const confidence = formatScore(message.confidenceScore)
    const stakePosture = formatStakePosture(message.stakePosture)
    const impliedProbability =
      message.impliedProbability !== null && message.impliedProbability !== undefined
        ? formatPercent(message.impliedProbability)
        : null

    if (!verdict && !confidence && !stakePosture && !impliedProbability) return null

    return (
      <div className="mb-3 flex flex-wrap gap-2">
        {verdict && (
          <ConceptTip concept="verdict" subtle>
            <span className={`inline-flex min-h-7 items-center rounded-lg border px-2.5 py-1 text-[11px] font-semibold leading-none ${verdictTone(message.verdict)}`}>
              {t.chat.verdict}: {verdict}
            </span>
          </ConceptTip>
        )}
        {confidence && (
          <ConceptTip concept="confidence" subtle>
            <span className="inline-flex min-h-7 items-center rounded-lg border border-[#00FF87]/25 bg-[#00FF87]/5 px-2.5 py-1 text-[11px] font-semibold leading-none text-[#00FF87]">
              {t.chat.confidence}: {confidence}/10
            </span>
          </ConceptTip>
        )}
        {stakePosture && (
          <ConceptTip concept="stake" subtle>
            <span className="inline-flex min-h-7 items-center rounded-lg border border-[#FFD600]/25 bg-[#FFD600]/5 px-2.5 py-1 text-[11px] font-semibold leading-none text-[#FFD600]">
              {t.chat.stake}: {stakePosture}
            </span>
          </ConceptTip>
        )}
        {impliedProbability && (
          <ConceptTip concept="impliedProbability" subtle>
            <span className="inline-flex min-h-7 items-center rounded-lg border border-[#6A7A9B]/30 bg-[#6A7A9B]/10 px-2.5 py-1 text-[11px] font-semibold leading-none text-[#D7DEEF]">
              {t.chat.impliedProbability}: {impliedProbability}
            </span>
          </ConceptTip>
        )}
      </div>
    )
  }

  const formatMarketType = (value: string | null | undefined) => {
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

  const formatHistoryDate = (value: string | null) => {
    if (!value) return ""
    try {
      return new Intl.DateTimeFormat(language === "es" ? "es-ES" : "en-US", {
        month: "short",
        day: "numeric",
      }).format(new Date(value))
    } catch {
      return ""
    }
  }

  const renderMarketSignal = (signal: ChatMarketSignal | null | undefined) => {
    if (!signal) return null
    if (!signal.matched) {
      return (
        <div className="mt-3 rounded-lg border border-[#FFD600]/25 bg-[#FFD600]/5 px-3 py-2.5">
          <div className="flex items-center gap-2 text-[#FFD600]">
            <Activity className="h-3.5 w-3.5 flex-shrink-0" />
            <span className="text-[11px] font-semibold uppercase tracking-wider">
              {t.chat.marketSignal}
            </span>
          </div>
          <p className="mt-1.5 text-xs leading-relaxed text-[#A8B4D0]">
            {signal.note ?? t.chat.noMarketSignal}
          </p>
        </div>
      )
    }

    return (
      <div className="mt-3 rounded-lg border border-[#00FF87]/25 bg-[#00FF87]/5 px-3 py-2.5">
        <div className="flex items-center gap-2 text-[#00FF87]">
          <Activity className="h-3.5 w-3.5 flex-shrink-0" />
          <span className="text-[11px] font-semibold uppercase tracking-wider">
            {t.chat.marketSignal}
          </span>
        </div>
        {signal.question && (
          <p className="mt-1.5 text-xs leading-relaxed text-[#F0F4FF]">
            {signal.question}
          </p>
        )}
        <div className="mt-2 grid grid-cols-2 gap-2">
          <div className="min-w-0">
            <p className="text-[10px] uppercase tracking-wider text-[#6A7A9B]">
              <ConceptTip concept="crowdProbability" label={t.chat.crowdProbability} subtle />
            </p>
            <p className="text-sm font-semibold text-[#00FF87]">
              {formatPercent(signal.implied_probability)}
            </p>
          </div>
          <div className="min-w-0">
            <p className="text-[10px] uppercase tracking-wider text-[#6A7A9B]">
              <ConceptTip concept="signalQuality" label={t.chat.quality} subtle />
            </p>
            <p className="text-sm font-semibold text-foreground">
              {formatQualityLabel(signal.signal_quality_score, language, t)}
            </p>
          </div>
        </div>
        {(!isBeginner || isAdvanced) && (
          <details className="group mt-2 rounded-lg border border-[#1A2845] bg-[#0A1325]/70 px-3 py-2" open={isAdvanced}>
            <summary className="flex cursor-pointer list-none items-center justify-between text-[11px] font-semibold text-[#A8B4D0]">
              <span>{t.chat.details}</span>
              <span className="transition-transform group-open:rotate-180">⌄</span>
            </summary>
            <div className="mt-2 grid grid-cols-2 gap-2 border-t border-[#1A2845] pt-2">
          <div className="min-w-0">
            <p className="text-[10px] uppercase tracking-wider text-[#6A7A9B]">
              {t.chat.liquidity}
            </p>
            <p className="truncate text-sm font-semibold text-foreground">
              {signal.liquidity_label ?? "—"}
            </p>
          </div>
          <div className="min-w-0">
            <p className="text-[10px] uppercase tracking-wider text-[#6A7A9B]">
              {t.chat.market}
            </p>
            <p className="truncate text-xs font-medium text-[#A8B4D0]">
              {formatMarketType(signal.market_type)}
            </p>
          </div>
          <div className="min-w-0">
            <p className="text-[10px] uppercase tracking-wider text-[#6A7A9B]">
              {t.chat.quality}
            </p>
            <p className="text-xs font-medium text-[#A8B4D0]">
              {signal.signal_quality_score ?? "—"}/100
            </p>
          </div>
            </div>
          </details>
        )}
      </div>
    )
  }

  return (
    <div className="chat-keyboard-surface relative flex h-full min-h-0 flex-col overflow-hidden">
      {/* Header */}
      <div className="flex-shrink-0 border-b border-[#1A2845] px-4 pb-3 pt-[calc(1rem+env(safe-area-inset-top))] sm:px-5">
        <div className="flex items-center gap-3">
          <div className="relative w-10 h-10 rounded-full bg-gradient-to-br from-[#00FF87]/20 to-[#00FF87]/5 border border-[#00FF87]/30 flex items-center justify-center flex-shrink-0">
            <Zap className="w-5 h-5 text-[#00FF87]" />
            <div className="absolute -bottom-0.5 -right-0.5 w-3 h-3 rounded-full bg-[#00FF87] border-2 border-[#070D1A]" />
          </div>
          <div>
            <h2 className="text-base font-bold text-foreground leading-tight">{t.chat.title}</h2>
            <p className="text-xs text-[#00FF87]">{t.chat.status}</p>
          </div>
          <div className="ml-auto min-w-0">
            <div className="flex items-center gap-1.5">
              <button
                onClick={handleNewChat}
                className="h-8 w-8 rounded-lg border border-[#1A2845] bg-[#0F1C35] text-[#A8B4D0] hover:text-[#00FF87] transition-colors flex items-center justify-center"
                aria-label={t.chat.newChat}
                title={t.chat.newChat}
              >
                <Plus className="h-4 w-4" />
              </button>
              <button
                onClick={toggleHistory}
                className="h-8 w-8 rounded-lg border border-[#1A2845] bg-[#0F1C35] text-[#A8B4D0] hover:text-[#00FF87] transition-colors flex items-center justify-center"
                aria-label={t.chat.history}
                title={t.chat.history}
              >
                {historyOpen ? <X className="h-4 w-4" /> : <History className="h-4 w-4" />}
              </button>
              <span
                className={`inline-flex max-w-[108px] items-center gap-1 truncate rounded-full border px-2 py-1 text-[10px] font-semibold uppercase tracking-normal ${quotaClass}`}
                title={quotaTitle}
              >
                {isPremium && <Crown className="h-3 w-3 shrink-0" />}
                {quotaLabel}
              </span>
            </div>
          </div>
        </div>
      </div>

      {historyOpen && (
        <div className="absolute inset-0 z-20 flex justify-end bg-[#070D1A]/70 backdrop-blur-sm">
          <button
            className="absolute inset-0 cursor-default"
            onClick={() => setHistoryOpen(false)}
            aria-label={t.chat.closeHistory}
          />
          <aside className="relative z-10 flex h-full w-full max-w-[360px] flex-col border-l border-[#1A2845] bg-[#0B162B] shadow-2xl">
            <div className="flex items-center justify-between gap-3 border-b border-[#1A2845] px-4 py-4">
              <div>
                <p className="text-sm font-bold text-foreground">{t.chat.history}</p>
                <p className="text-xs text-[#6A7A9B]">{t.chat.historySubtitle}</p>
              </div>
              <button
                onClick={() => setHistoryOpen(false)}
                className="h-8 w-8 rounded-lg border border-[#1A2845] text-[#A8B4D0] hover:text-foreground flex items-center justify-center"
                aria-label={t.chat.closeHistory}
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            <div className="border-b border-[#1A2845] px-4 py-3">
              <button
                onClick={handleNewChat}
                className="flex w-full items-center justify-center gap-2 rounded-lg bg-[#00FF87] px-3 py-2 text-sm font-semibold text-[#070D1A] hover:bg-[#00e87a] transition-colors"
              >
                <Plus className="h-4 w-4" />
                {t.chat.newChat}
              </button>
            </div>

            <div className="flex-1 overflow-y-auto px-3 py-3">
              {isLoadingHistory && <p className="px-1 text-xs text-[#6A7A9B]">{t.chat.loadingHistory}</p>}
              {historyError && <p className="px-1 text-xs text-[#FFD600]">{historyError}</p>}
              {!isLoadingHistory && !historyError && history.length === 0 && (
                <p className="px-1 text-xs text-[#6A7A9B]">{t.chat.emptyHistory}</p>
              )}
              <div className="flex flex-col gap-2">
                {history.map((conversation) => (
                  <button
                    key={conversation.id}
                    onClick={() => void handleOpenConversation(conversation.id)}
                    className={`text-left rounded-lg border px-3 py-3 transition-colors ${
                      conversation.id === conversationId
                        ? "border-[#00FF87]/40 bg-[#00FF87]/10"
                        : "border-[#1A2845] bg-[#0F1C35] hover:border-[#00FF87]/30"
                    }`}
                  >
                    <div className="flex items-start justify-between gap-3">
                      <p className="line-clamp-2 text-sm font-semibold leading-snug text-foreground">
                        {conversation.title}
                      </p>
                      <span className="shrink-0 text-[10px] text-[#6A7A9B]">
                        {formatHistoryDate(conversation.updated_at)}
                      </span>
                    </div>
                    {conversation.last_message_preview && (
                      <p className="mt-1.5 line-clamp-2 text-xs leading-relaxed text-[#6A7A9B]">
                        {conversation.last_message_preview}
                      </p>
                    )}
                  </button>
                ))}
              </div>
            </div>
          </aside>
        </div>
      )}

      {/* Messages */}
      <div className="flex min-h-0 flex-1 flex-col gap-3 overflow-y-auto px-4 py-4">
        {messages.map((msg) => (
          <div
            key={msg.id}
            className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"} gap-2.5`}
          >
            {msg.role === "coach" && (
              <div className="w-7 h-7 rounded-full bg-[#00FF87]/10 border border-[#00FF87]/30 flex items-center justify-center flex-shrink-0 mt-0.5">
                <Zap className="w-3.5 h-3.5 text-[#00FF87]" />
              </div>
            )}
            <div
              className={`max-w-[86%] rounded-2xl px-3.5 py-3 text-sm leading-relaxed ${
                msg.role === "user"
                  ? "bg-[#00FF87] text-[#070D1A] font-medium rounded-br-md"
                  : "bg-[#0F1C35] border border-[#1A2845] text-[#A8B4D0] rounded-bl-md"
              }`}
            >
              {renderMetadataChips(msg)}
              {renderText(msg.text)}
              {msg.role === "coach" && renderMarketSignal(msg.marketSignal)}
            </div>
          </div>
        ))}
        {!hasUserSentMessage.current && (
          <div className="ml-9 flex flex-col gap-2">
            <p className="text-[11px] font-semibold uppercase tracking-wider text-[#6A7A9B]">
              {t.chat.exampleTitle}
            </p>
            <div className="flex flex-wrap gap-2">
              {t.chat.examplePrompts.map((prompt) => (
                <button
                  key={prompt}
                  onClick={() => handleExamplePrompt(prompt)}
                  className="rounded-lg border border-[#1A2845] bg-[#0F1C35] px-3 py-2 text-left text-xs leading-snug text-[#A8B4D0] transition-colors hover:border-[#00FF87]/40 hover:text-foreground"
                >
                  {prompt}
                </button>
              ))}
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Input bar */}
      <div className="flex-shrink-0 px-4 pb-[calc(0.75rem+env(safe-area-inset-bottom))]">
        <div className="flex items-center gap-2 rounded-2xl border border-[#1A2845] bg-[#0F1C35] px-3 py-2.5 transition-colors focus-within:border-[#00FF87]/50">
          <input
            ref={inputRef}
            className="min-w-0 flex-1 bg-transparent text-base text-foreground outline-none placeholder:text-[#6A7A9B] sm:text-sm"
            placeholder={t.chat.placeholder}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={isSending}
          />
          <button
            onClick={() => void handleSend()}
            className={`flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-xl bg-[#00FF87] transition-all ${
              sendDisabled ? "opacity-40" : "hover:bg-[#00e87a] active:scale-95"
            }`}
            aria-disabled={sendDisabled}
            aria-label={t.chat.send}
          >
            <Send className="w-4 h-4 text-[#070D1A]" />
          </button>
        </div>
        <p className="mt-2 text-center text-[10px] leading-snug text-[#6A7A9B]">
          {t.chat.disclaimer}
        </p>
      </div>
    </div>
  )
}

function formatQualityLabel(value: number | null, language: "en" | "es", t: ReturnType<typeof useLanguage>["t"]) {
  if (typeof value !== "number") return "—"
  if (value >= 75) return t.signals.strongSignal
  if (value >= 50) return t.signals.mediumSignal
  return t.signals.thinSignal
}
