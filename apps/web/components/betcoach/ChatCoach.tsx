"use client"

import { useState, useRef, useEffect } from "react"
import { Send, Zap } from "lucide-react"
import { sendChatMessage } from "@/lib/api"

type Message = {
  id: number
  role: "coach" | "user"
  text: string
}

const initialMessages: Message[] = [
  {
    id: 1,
    role: "coach",
    text: "Hey! Tell me about the bet you're thinking of placing. I'll give you my honest take.",
  },
  {
    id: 2,
    role: "user",
    text: "I'm thinking of betting €20 on Spain to win Group A at 1.8 odds",
  },
  {
    id: 3,
    role: "coach",
    text: `Good question. Let me break this down for you:\n\n📊 **Bookmaker odds:** 1.80 (implied prob: 55.6%)\n📈 **Polymarket consensus:** ~64% (fair odds: ~1.56)\n\nThe book is offering you WORSE value than the prediction market suggests — meaning the crowd thinks Spain is MORE likely to win than the bookmaker's price implies. That's actually a divergence working in your favour.\n\n⚠️ However, Spain face Morocco & Japan in Group A. Morocco are dangerous at home-continent odds and Japan are historically solid. The 1.80 price is stingy for what's a real risk group.\n\n**My recommendation: Pass or reduce stake.** If you must play, €10 max at these odds. Wait for post-matchday 1 odds which may open up.\n\n**Confidence score: 6/10**`,
  },
]

export default function ChatCoach() {
  const [messages, setMessages] = useState<Message[]>(initialMessages)
  const [input, setInput] = useState("")
  const [isSending, setIsSending] = useState(false)
  const [dailyChatsRemaining, setDailyChatsRemaining] = useState<number | null>(null)
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages])

  const handleSend = async () => {
    const trimmed = input.trim()
    if (!trimmed || isSending) return
    const userMsg: Message = { id: Date.now(), role: "user", text: trimmed }
    const pendingCoachMsg: Message = {
      id: Date.now() + 1,
      role: "coach",
      text: "Checking the bet and building a straight answer...",
    }
    setMessages((prev) => [...prev, userMsg, pendingCoachMsg])
    setInput("")
    setIsSending(true)

    try {
      const result = await sendChatMessage(trimmed)
      setDailyChatsRemaining(result.daily_chats_remaining)
      setMessages((prev) =>
        prev.map((message) =>
          message.id === pendingCoachMsg.id
            ? { ...message, text: result.response }
            : message
        )
      )
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : "Unable to reach the Matchmind coach."
      setMessages((prev) =>
        prev.map((message) =>
          message.id === pendingCoachMsg.id
            ? {
                ...message,
                text: `I couldn't complete that request.\n\n${errorMessage}`,
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
            <h2 className="text-base font-bold text-foreground leading-tight">BetCoach AI</h2>
            <p className="text-xs text-[#00FF87]">Online · World Cup 2026 expert</p>
          </div>
          <div className="ml-auto">
            <span className="text-[10px] font-semibold bg-[#FFD600]/10 border border-[#FFD600]/30 text-[#FFD600] rounded-full px-2.5 py-1 uppercase tracking-wider">
              {dailyChatsRemaining === null ? "5 chats/day" : `${dailyChatsRemaining} left`}
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
            placeholder="Ask about any World Cup bet..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={isSending}
          />
          <button
            onClick={() => void handleSend()}
            className="w-8 h-8 rounded-xl bg-[#00FF87] flex items-center justify-center flex-shrink-0 hover:bg-[#00e87a] active:scale-95 transition-all disabled:opacity-40"
            disabled={!input.trim() || isSending}
            aria-label="Send message"
          >
            <Send className="w-4 h-4 text-[#070D1A]" />
          </button>
        </div>
        <p className="text-center text-[10px] text-[#6A7A9B] mt-2">
          For entertainment purposes only. Always bet responsibly.
        </p>
      </div>
    </div>
  )
}
