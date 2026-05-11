"use client"

import { useEffect, useState } from "react"
import DailyFeed from "@/components/betcoach/DailyFeed"
import ChatCoach from "@/components/betcoach/ChatCoach"
import BetTracker from "@/components/betcoach/BetTracker"
import Profile from "@/components/betcoach/Profile"
import BottomNav from "@/components/betcoach/BottomNav"
import MarketSignals from "@/components/betcoach/MarketSignals"
import { getCurrentUser, type CurrentUser } from "@/lib/api"
import { AuthProvider, useAuth } from "@/lib/auth"
import { LanguageProvider } from "@/lib/i18n"
import AuthGate from "@/components/betcoach/AuthGate"

export type Tab = "feed" | "signals" | "chat" | "tracker" | "profile"

export default function BetCoachApp() {
  return (
    <LanguageProvider>
      <AuthProvider>
        <AuthGate>
          <BetCoachShell />
        </AuthGate>
      </AuthProvider>
    </LanguageProvider>
  )
}

function BetCoachShell() {
  const [activeTab, setActiveTab] = useState<Tab>("chat")
  const [currentUser, setCurrentUser] = useState<CurrentUser | null>(null)
  const [isLoadingUser, setIsLoadingUser] = useState(true)
  const [userError, setUserError] = useState<string | null>(null)
  const { session } = useAuth()
  const isPremium = currentUser?.plan === "premium"

  const loadCurrentUser = async () => {
    setIsLoadingUser(true)
    setUserError(null)

    try {
      setCurrentUser(await getCurrentUser())
    } catch (err) {
      setUserError(err instanceof Error ? err.message : "Unable to load your profile.")
    } finally {
      setIsLoadingUser(false)
    }
  }

  useEffect(() => {
    void loadCurrentUser()
  }, [session?.access_token])

  useEffect(() => {
    const refreshOnFocus = () => {
      void loadCurrentUser()
    }

    window.addEventListener("focus", refreshOnFocus)
    return () => window.removeEventListener("focus", refreshOnFocus)
  }, [])

  return (
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
                <DailyFeed isPremium={isPremium} />
              </div>
              <div className={activeTab === "signals" ? "h-full" : "hidden"}>
                <MarketSignals isPremium={isPremium} />
              </div>
              <div className={activeTab === "chat" ? "h-full" : "hidden"}>
                <ChatCoach />
              </div>
              <div className={activeTab === "tracker" ? "h-full" : "hidden"}>
                <BetTracker />
              </div>
              <div className={activeTab === "profile" ? "h-full" : "hidden"}>
                <Profile
                  currentUser={currentUser}
                  isLoadingUser={isLoadingUser}
                  userError={userError}
                  onRetryUser={() => void loadCurrentUser()}
                />
              </div>
            </div>
          </main>

          {/* Bottom navigation */}
          <BottomNav activeTab={activeTab} onTabChange={setActiveTab} />
        </div>
      </div>
  )
}
