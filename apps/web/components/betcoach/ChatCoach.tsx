"use client"

import { useState, useRef, useEffect } from "react"
import { Activity, Send, Zap } from "lucide-react"
import { sendChatMessage, type ChatMarketSignal } from "@/lib/api"
import { useLanguage } from "@/lib/i18n"

type Message = {
  id: number
  role: "coach" | "user"
  text: string
  marketSignal?: ChatMarketSignal | null
}

export default function ChatCoach() {
  const { language, t } = useLanguage()
  const getInitialMessages = () => [
    {
      id: 1,
      role: "coach" as const,
      text: t.chat.initialCoach,
    },
    {
      id: 2,
      role: "user" as const,
      text: t.chat.initialUser,
    },
    {
      id: 3,
      role: "coach" as const,
      text: t.chat.initialAnalysis,
    },
  ]
  const [messages, setMessages] = useState<Message[]>(getInitialMessages)
  const [input, setInput] = useState("")
  const [isSending, setIsSending] = useState(false)
  const [dailyChatsRemaining, setDailyChatsRemaining] = useState<number | null>(null)
  const bottomRef = useRef<HTMLDivElement>(null)
  const hasUserSentMessage = useRef(false)

  useEffect(() => {
    if (!hasUserSentMessage.current) {
      setMessages(getInitialMessages())
    }
  }, [language])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages])

  const handleSend = async () => {
    const trimmed = input.trim()
    if (!trimmed || isSending) return
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
      const result = await sendChatMessage(trimmed, language)
      setDailyChatsRemaining(result.daily_chats_remaining)
      setMessages((prev) =>
        prev.map((message) =>
          message.id === pendingCoachMsg.id
            ? { ...message, text: result.response, marketSignal: result.market_signal }
            : message
        )
      )
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : t.chat.reachError
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
              {t.chat.crowdProbability}
            </p>
            <p className="text-sm font-semibold text-[#00FF87]">
              {formatPercent(signal.implied_probability)}
            </p>
          </div>
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
      </div>
    )
  }

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="px-5 pt-6 pb-4 flex-shrink-0 border-b border-[#1A2845]">
        <div className="flex items-center gap-3">
          <div className="relative w-10 h-10 rounded-full bg-gradient-to-br from-[#00FF87]/20 to-[#00FF87]/5 border border-[#00FF87]/30 flex items-center justify-center flex-shrink-0">
            <Zap className="w-5 h-5 text-[#00FF87]" />
            <div className="absolute -bottom-0.5 -right-0.5 w-3 h-3 rounded-full bg-[#00FF87] border-2 border-[#070D1A]" />
          </div>
          <div>
            <h2 className="text-base font-bold text-foreground leading-tight">{t.chat.title}</h2>
            <p className="text-xs text-[#00FF87]">{t.chat.status}</p>
          </div>
          <div className="ml-auto">
            <span className="text-[10px] font-semibold bg-[#FFD600]/10 border border-[#FFD600]/30 text-[#FFD600] rounded-full px-2.5 py-1 uppercase tracking-wider">
              {dailyChatsRemaining === null ? t.chat.dailyLimit : `${dailyChatsRemaining} ${t.chat.left}`}
            </span>
          </div>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-4 py-4 flex flex-col gap-4">
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
              className={`max-w-[82%] rounded-2xl px-4 py-3 text-sm leading-relaxed ${
                msg.role === "user"
                  ? "bg-[#00FF87] text-[#070D1A] font-medium rounded-br-md"
                  : "bg-[#0F1C35] border border-[#1A2845] text-[#A8B4D0] rounded-bl-md"
              }`}
            >
              {renderText(msg.text)}
              {msg.role === "coach" && renderMarketSignal(msg.marketSignal)}
            </div>
          </div>
        ))}
        <div ref={bottomRef} />
      </div>

      {/* Input bar */}
      <div className="px-4 pb-4 flex-shrink-0">
        <div className="flex items-center gap-2 bg-[#0F1C35] border border-[#1A2845] rounded-2xl px-4 py-2.5 focus-within:border-[#00FF87]/50 transition-colors">
          <input
            className="flex-1 bg-transparent text-sm text-foreground placeholder:text-[#6A7A9B] outline-none"
            placeholder={t.chat.placeholder}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={isSending}
          />
          <button
            onClick={() => void handleSend()}
            className="w-8 h-8 rounded-xl bg-[#00FF87] flex items-center justify-center flex-shrink-0 hover:bg-[#00e87a] active:scale-95 transition-all disabled:opacity-40"
            disabled={!input.trim() || isSending}
            aria-label={t.chat.send}
          >
            <Send className="w-4 h-4 text-[#070D1A]" />
          </button>
        </div>
        <p className="text-center text-[10px] text-[#6A7A9B] mt-2">
          {t.chat.disclaimer}
        </p>
      </div>
    </div>
  )
}
