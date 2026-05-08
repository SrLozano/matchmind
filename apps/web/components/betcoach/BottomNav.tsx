"use client"

import { Home, MessageCircle, BarChart2, User } from "lucide-react"
import { useLanguage } from "@/lib/i18n"

type Tab = "feed" | "chat" | "tracker" | "profile"

interface BottomNavProps {
  activeTab: Tab
  onTabChange: (tab: Tab) => void
}

const tabs: { id: Tab; labelKey: "picks" | "coach" | "tracker" | "profile"; icon: React.ElementType }[] = [
  { id: "feed", labelKey: "picks", icon: Home },
  { id: "chat", labelKey: "coach", icon: MessageCircle },
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
      {tabs.map(({ id, labelKey, icon: Icon }) => {
        const isActive = activeTab === id
        const label = t.nav[labelKey]
        return (
          <button
            key={id}
            onClick={() => onTabChange(id)}
            className={`flex-1 flex flex-col items-center justify-center gap-1 py-3 transition-colors ${
              isActive ? "text-[#00FF87]" : "text-[#6A7A9B] hover:text-[#A8B4D0]"
            }`}
            aria-label={label}
            aria-current={isActive ? "page" : undefined}
          >
            <div className="relative">
              <Icon className={`w-5 h-5 ${isActive ? "drop-shadow-[0_0_6px_rgba(0,255,135,0.7)]" : ""}`} />
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
