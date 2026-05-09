"use client"

import { useState } from "react"
import DailyFeed from "@/components/betcoach/DailyFeed"
import ChatCoach from "@/components/betcoach/ChatCoach"
import BetTracker from "@/components/betcoach/BetTracker"
import Profile from "@/components/betcoach/Profile"
import BottomNav from "@/components/betcoach/BottomNav"
import MarketSignals from "@/components/betcoach/MarketSignals"
import { LanguageProvider } from "@/lib/i18n"

export type Tab = "feed" | "signals" | "chat" | "tracker" | "profile"

export default function BetCoachApp() {
  const [activeTab, setActiveTab] = useState<Tab>("chat")

  return (
    <LanguageProvider>
      <div className="flex items-center justify-center min-h-screen bg-[#040810]">
        {/* Phone frame — max-width 430px, full height on mobile */}
        <div
          className="relative w-full max-w-[430px] flex flex-col overflow-hidden md:rounded-3xl md:shadow-[0_0_60px_rgba(0,255,135,0.08),0_0_120px_rgba(0,0,0,0.8)]"
          style={{ height: "min(844px, 100dvh)" }}
        >
          {/* Screen content */}
          <main className="flex-1 overflow-hidden bg-background relative">
            <div className="relative h-full overflow-hidden">
              <div className={activeTab === "feed" ? "h-full" : "hidden"}>
                <DailyFeed />
              </div>
              <div className={activeTab === "signals" ? "h-full" : "hidden"}>
                <MarketSignals />
              </div>
              <div className={activeTab === "chat" ? "h-full" : "hidden"}>
                <ChatCoach />
              </div>
              <div className={activeTab === "tracker" ? "h-full" : "hidden"}>
                <BetTracker />
              </div>
              <div className={activeTab === "profile" ? "h-full" : "hidden"}>
                <Profile />
              </div>
            </div>
          </main>

          {/* Bottom navigation */}
          <BottomNav activeTab={activeTab} onTabChange={setActiveTab} />
        </div>
      </div>
    </LanguageProvider>
  )
}
