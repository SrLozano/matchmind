"use client"

import { Activity, BarChart2, Home, MessageCircle, User } from "lucide-react"
import type { ElementType } from "react"
import { useLanguage } from "@/lib/i18n"

type Tab = "feed" | "signals" | "chat" | "tracker" | "profile"

interface BottomNavProps {
  activeTab: Tab
  onTabChange: (tab: Tab) => void
}

const tabs: { id: Tab; labelKey: "picks" | "signals" | "coach" | "tracker" | "profile"; icon: ElementType; featured?: boolean }[] = [
  { id: "feed", labelKey: "picks", icon: Home },
  { id: "signals", labelKey: "signals", icon: Activity },
  { id: "chat", labelKey: "coach", icon: MessageCircle, featured: true },
  { id: "tracker", labelKey: "tracker", icon: BarChart2 },
  { id: "profile", labelKey: "profile", icon: User },
]

export default function BottomNav({ activeTab, onTabChange }: BottomNavProps) {
  const { t } = useLanguage()

  return (
    <nav
      className="flex-shrink-0 flex items-center border-t border-[#1A2845] bg-[#080E1E]"
      style={{ paddingBottom: "env(safe-area-inset-bottom, 0px)" }}
      aria-label={t.nav.aria}
    >
      {tabs.map(({ id, labelKey, icon: Icon, featured }) => {
        const isActive = activeTab === id
        const label = t.nav[labelKey]
        return (
          <button
            key={id}
            onClick={() => onTabChange(id)}
            className={`relative flex flex-1 flex-col items-center justify-center gap-1 transition-colors ${
              isActive ? "text-[#00FF87]" : "text-[#6A7A9B] hover:text-[#A8B4D0]"
            } ${featured ? "pb-2 pt-1" : "py-3"}`}
            aria-label={label}
            aria-current={isActive ? "page" : undefined}
          >
            <div
              className={`relative flex items-center justify-center ${
                featured
                  ? `-mt-5 h-12 w-12 rounded-full border bg-[#0A1325] shadow-[0_8px_24px_rgba(0,0,0,0.35)] ${
                      isActive ? "border-[#00FF87]/60 text-[#00FF87]" : "border-[#1A2845] text-[#A8B4D0]"
                    }`
                  : ""
              }`}
            >
              <Icon className={`${featured ? "h-6 w-6" : "h-5 w-5"} ${isActive ? "drop-shadow-[0_0_6px_rgba(0,255,135,0.7)]" : ""}`} />
              {isActive && (
                <span className="absolute -top-1 -right-1 w-1.5 h-1.5 rounded-full bg-[#00FF87]" />
              )}
            </div>
            <span className={`text-[10px] font-semibold tracking-wide ${isActive ? "text-[#00FF87]" : "text-[#6A7A9B]"}`}>
              {label}
            </span>
          </button>
        )
      })}
    </nav>
  )
}
