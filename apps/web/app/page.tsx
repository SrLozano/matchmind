"use client"

import { useEffect, useState } from "react"
import type { FocusEvent } from "react"
import { Crown, Loader2, X } from "lucide-react"
import DailyFeed from "@/components/betcoach/DailyFeed"
import ChatCoach from "@/components/betcoach/ChatCoach"
import BetTracker from "@/components/betcoach/BetTracker"
import Profile from "@/components/betcoach/Profile"
import BottomNav from "@/components/betcoach/BottomNav"
import MarketSignals from "@/components/betcoach/MarketSignals"
import { createTournamentPassCheckoutSession, getCurrentUser, type ChatResponse, type CurrentUser } from "@/lib/api"
import { AuthProvider, useAuth } from "@/lib/auth"
import { LanguageProvider, useLanguage } from "@/lib/i18n"
import AuthGate from "@/components/betcoach/AuthGate"

export type Tab = "feed" | "signals" | "chat" | "tracker" | "profile"

export default function MatchmindApp() {
  return (
    <LanguageProvider>
      <AuthProvider>
        <AuthGate>
          <MatchmindShell />
        </AuthGate>
      </AuthProvider>
    </LanguageProvider>
  )
}

function MatchmindShell() {
  const [activeTab, setActiveTab] = useState<Tab>("chat")
  const [currentUser, setCurrentUser] = useState<CurrentUser | null>(null)
  const [isLoadingUser, setIsLoadingUser] = useState(true)
  const [userError, setUserError] = useState<string | null>(null)
  const [isEditing, setIsEditing] = useState(false)
  const [upgradePromptOpen, setUpgradePromptOpen] = useState(false)
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

  useEffect(() => {
    const setViewportHeight = () => {
      const visualHeight = window.visualViewport?.height ?? 0
      const layoutHeight = window.innerHeight || 0
      const clientHeight = document.documentElement.clientHeight || 0
      const keyboardIsOpen = visualHeight > 0 && layoutHeight > 0 && visualHeight < layoutHeight - 120
      const viewportHeight = keyboardIsOpen
        ? visualHeight
        : Math.max(visualHeight, layoutHeight, clientHeight)

      if (viewportHeight > 0) {
        document.documentElement.style.setProperty("--matchmind-viewport-height", `${Math.ceil(viewportHeight)}px`)
      }
    }

    setViewportHeight()
    window.addEventListener("resize", setViewportHeight)
    window.addEventListener("orientationchange", setViewportHeight)
    window.visualViewport?.addEventListener("resize", setViewportHeight)
    window.visualViewport?.addEventListener("scroll", setViewportHeight)

    return () => {
      window.removeEventListener("resize", setViewportHeight)
      window.removeEventListener("orientationchange", setViewportHeight)
      window.visualViewport?.removeEventListener("resize", setViewportHeight)
      window.visualViewport?.removeEventListener("scroll", setViewportHeight)
    }
  }, [])

  const handleFocusCapture = (event: FocusEvent<HTMLDivElement>) => {
    const tagName = (event.target as HTMLElement | null)?.tagName
    if (tagName === "INPUT" || tagName === "TEXTAREA" || tagName === "SELECT") {
      setIsEditing(true)
    }
  }

  const handleBlurCapture = () => {
    window.setTimeout(() => {
      const tagName = document.activeElement?.tagName
      setIsEditing(tagName === "INPUT" || tagName === "TEXTAREA" || tagName === "SELECT")
    }, 80)
  }

  const handleChatUsageUpdate = (result: ChatResponse) => {
    setCurrentUser((user) => {
      if (!user) return user
      return {
        ...user,
        daily_chat_count: result.chat_count,
        daily_chat_count_limit: result.chat_count_limit,
        daily_chats_remaining: result.daily_chats_remaining,
        chat_count_limit: result.chat_count_limit,
        chat_limit_period: result.chat_limit_period,
        chats_remaining: result.chats_remaining,
      }
    })
  }

  return (
      <div className="flex min-h-[var(--matchmind-viewport-height,100dvh)] items-stretch justify-center bg-[#040810] md:items-center">
        <div
          className="matchmind-shell relative flex h-[var(--matchmind-viewport-height,100dvh)] w-full max-w-[430px] flex-col overflow-hidden bg-background md:h-[min(844px,var(--matchmind-viewport-height,100dvh))] md:rounded-3xl md:shadow-[0_0_60px_rgba(0,255,135,0.08),0_0_120px_rgba(0,0,0,0.8)]"
          onFocusCapture={handleFocusCapture}
          onBlurCapture={handleBlurCapture}
        >
          <main className="relative min-h-0 flex-1 overflow-hidden bg-background">
            <div className="relative h-full overflow-hidden">
              <div className={activeTab === "feed" ? "h-full" : "hidden"}>
                <DailyFeed isPremium={isPremium} />
              </div>
              <div className={activeTab === "signals" ? "h-full" : "hidden"}>
                <MarketSignals isPremium={isPremium} />
              </div>
              <div className={activeTab === "chat" ? "h-full" : "hidden"}>
                <ChatCoach
                  currentUser={currentUser}
                  onChatUsageUpdate={handleChatUsageUpdate}
                  onShowUpgradePrompt={() => setUpgradePromptOpen(true)}
                />
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
                  onShowUpgradePrompt={() => setUpgradePromptOpen(true)}
                />
              </div>
            </div>
          </main>

          <BottomNav activeTab={activeTab} onTabChange={setActiveTab} isHidden={isEditing} />
          {upgradePromptOpen && !isPremium && (
            <UpgradePrompt onClose={() => setUpgradePromptOpen(false)} />
          )}
        </div>
      </div>
  )
}

function UpgradePrompt({ onClose }: { onClose: () => void }) {
  const { language, t } = useLanguage()
  const [isStartingCheckout, setIsStartingCheckout] = useState(false)
  const [checkoutError, setCheckoutError] = useState<string | null>(null)

  const startCheckout = async () => {
    setIsStartingCheckout(true)
    setCheckoutError(null)

    try {
      const checkoutSession = await createTournamentPassCheckoutSession()
      window.location.assign(checkoutSession.url)
    } catch (err) {
      setCheckoutError(err instanceof Error ? err.message : "Unable to start checkout.")
      setIsStartingCheckout(false)
    }
  }

  return (
    <div className="absolute inset-0 z-50 flex items-end bg-[#040810]/75 px-4 pb-[calc(1rem+env(safe-area-inset-bottom))] backdrop-blur-sm sm:items-center sm:justify-center">
      <div className="w-full rounded-2xl border border-[#00FF87]/30 bg-[#0B162B] p-4 shadow-[0_24px_80px_rgba(0,0,0,0.55)]">
        <div className="flex items-start justify-between gap-3">
          <div className="flex min-w-0 gap-3">
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl border border-[#00FF87]/30 bg-[#00FF87]/15">
              <Crown className="h-5 w-5 text-[#00FF87]" />
            </div>
            <div className="min-w-0">
              <p className="text-lg font-black leading-tight text-foreground">{t.profile.upgradeModalTitle}</p>
              <p className="mt-1 text-sm leading-relaxed text-[#A8B4D0]">{t.profile.upgradeModalCopy}</p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg border border-[#1A2845] text-[#6A7A9B] transition-colors hover:text-foreground"
            aria-label={language === "es" ? "Cerrar" : "Close"}
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        <div className="mt-4 flex items-center justify-between rounded-xl border border-[#1A2845] bg-[#070D1A] px-3 py-3">
          <span className="text-sm font-semibold text-[#A8B4D0]">{t.profile.pass}</span>
          <span className="text-xl font-black text-foreground">€9.99</span>
        </div>

        <button
          className="mt-4 flex w-full items-center justify-center gap-2 rounded-xl bg-[#00FF87] py-3.5 text-sm font-bold text-[#070D1A] shadow-[0_0_20px_rgba(0,255,135,0.3)] transition-all hover:bg-[#00e87a] active:scale-[0.98] disabled:cursor-not-allowed disabled:opacity-70"
          type="button"
          onClick={() => void startCheckout()}
          disabled={isStartingCheckout}
        >
          {isStartingCheckout && <Loader2 className="h-4 w-4 animate-spin" />}
          {isStartingCheckout ? (language === "es" ? "Abriendo Stripe..." : "Opening Stripe...") : t.profile.upgrade}
        </button>
        {checkoutError && <p className="mt-2.5 text-center text-[11px] font-semibold text-[#FF4D4D]">{checkoutError}</p>}
        <p className="mt-2.5 text-center text-[10px] text-[#6A7A9B]">{t.profile.stripe}</p>
      </div>
    </div>
  )
}
