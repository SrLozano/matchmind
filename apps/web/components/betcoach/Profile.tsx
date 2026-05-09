"use client"

import { useState } from "react"
import { AlertCircle, Check, ChevronDown, ChevronRight, Lock, RefreshCw } from "lucide-react"
import type { CurrentUser } from "@/lib/api"
import { useLanguage } from "@/lib/i18n"

export default function Profile({
  currentUser,
  isLoadingUser,
  userError,
  onRetryUser,
}: {
  currentUser: CurrentUser | null
  isLoadingUser: boolean
  userError: string | null
  onRetryUser: () => void
}) {
  const { language, setLanguage, t } = useLanguage()
  const [notificationsOpen, setNotificationsOpen] = useState(true)
  const isPremium = currentUser?.plan === "premium"
  const chatLimit = currentUser?.daily_chat_count_limit ?? 5
  const chatsUsed = currentUser?.daily_chat_count ?? 0
  const chatsRemaining = currentUser?.daily_chats_remaining
  const usagePercent = isPremium ? 100 : Math.min((chatsUsed / chatLimit) * 100, 100)
  const menuItems = [
    { label: t.profile.responsibleGambling, icon: ChevronRight },
    { label: t.profile.help, icon: ChevronRight },
    { label: t.profile.privacy, icon: ChevronRight },
  ]

  return (
    <div className="flex flex-col h-full overflow-y-auto pb-6">
      {/* Header */}
      <div className="px-5 pt-6 pb-5 flex-shrink-0">
        <h1 className="text-2xl font-bold text-foreground tracking-tight">{t.profile.title}</h1>
      </div>

      {/* User card */}
      <div className="mx-5 mb-5 rounded-2xl bg-[#0F1C35] border border-[#1A2845] p-4 flex items-center gap-4">
        <div className="relative">
          <div className="w-14 h-14 rounded-full bg-gradient-to-br from-[#00FF87]/30 to-[#0F1C35] border-2 border-[#00FF87]/40 flex items-center justify-center flex-shrink-0">
            <span className="text-2xl">👤</span>
          </div>
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-base font-bold text-foreground">Alex Rivera</p>
          <p className="text-xs text-[#6A7A9B]">{currentUser?.email ?? t.profile.devUser}</p>
          <div className="flex items-center gap-1.5 mt-1.5">
            <div className={`rounded-full px-2.5 py-0.5 ${isPremium ? "border border-[#00FF87]/25 bg-[#00FF87]/10" : "bg-[#1A2845]"}`}>
              <span className={`text-[10px] font-semibold uppercase tracking-wider ${isPremium ? "text-[#00FF87]" : "text-[#6A7A9B]"}`}>
                {isLoadingUser ? t.profile.loadingPlan : isPremium ? t.profile.premiumPlan : t.profile.freePlan}
              </span>
            </div>
          </div>
        </div>
        <button
          className="text-[#6A7A9B] transition-colors hover:text-foreground"
          aria-label={t.profile.refreshPlan}
          onClick={onRetryUser}
          type="button"
        >
          <RefreshCw className={`h-5 w-5 ${isLoadingUser ? "animate-spin" : ""}`} />
        </button>
      </div>

      {userError && (
        <div className="mx-5 mb-5 rounded-xl border border-[#FF4D4D]/30 bg-[#FF4D4D]/10 p-4">
          <div className="flex items-start gap-3">
            <AlertCircle className="mt-0.5 h-5 w-5 shrink-0 text-[#FF4D4D]" />
            <div className="min-w-0 flex-1">
              <p className="text-sm font-semibold text-foreground">{t.profile.planUnavailable}</p>
              <p className="mt-1 text-xs leading-relaxed text-[#A8B4D0]">{userError}</p>
              <button
                onClick={onRetryUser}
                className="mt-3 inline-flex items-center gap-1.5 rounded-lg border border-[#1A2845] bg-[#0F1C35] px-3 py-2 text-xs font-semibold text-foreground transition-colors hover:border-[#00FF87]/50"
                type="button"
              >
                <RefreshCw className="h-3.5 w-3.5" />
                {t.profile.refreshPlan}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Usage */}
      <div className="mx-5 mb-5 rounded-2xl bg-card border border-[#1A2845] p-4">
        <div className="flex items-center justify-between mb-3">
          <p className="text-sm font-semibold text-foreground">{t.profile.dailyChats}</p>
          <span className="text-xs text-[#6A7A9B]">{t.profile.resets}</span>
        </div>
        <div className="flex items-center gap-3">
          <div className="flex-1 h-2 rounded-full bg-[#1A2845] overflow-hidden">
            <div
              className="h-full rounded-full bg-[#00FF87] transition-all"
              style={{ width: `${usagePercent}%` }}
            />
          </div>
          <span className="text-sm font-bold text-foreground flex-shrink-0">
            {isPremium ? t.profile.unlimited : `${chatsUsed}/${chatLimit}`}
          </span>
        </div>
        <p className="text-[11px] text-[#6A7A9B] mt-2">
          {isPremium
            ? t.profile.unlimitedChats
            : chatsRemaining === null
              ? t.profile.remaining
              : `${chatsRemaining} ${t.chat.left}`}
        </p>
      </div>

      {/* Upgrade card */}
      <div className="mx-5 mb-5 rounded-2xl overflow-hidden border border-[#00FF87]/30 relative">
        {/* Glow effect */}
        <div className="absolute inset-0 bg-gradient-to-br from-[#00FF87]/5 to-transparent pointer-events-none" />

        <div className="relative p-5">
          <div className="flex items-center justify-between mb-1">
            <div className="flex items-center gap-2">
              <Lock className="w-4 h-4 text-[#00FF87]" />
              <span className="text-[10px] font-bold tracking-widest uppercase text-[#00FF87]">{t.profile.pass}</span>
            </div>
            <div className="flex items-baseline gap-0.5">
              <span className="text-2xl font-black text-foreground">€9.99</span>
              <span className="text-xs text-[#6A7A9B]">{t.profile.oneTime}</span>
            </div>
          </div>
          <p className="text-lg font-bold text-foreground mb-4">
            {isPremium ? t.profile.premiumActive : t.profile.unlock}
          </p>

          <ul className="flex flex-col gap-2.5 mb-5">
            {t.profile.features.map((text) => (
              <li key={text} className="flex items-center gap-3">
                <div className="w-5 h-5 rounded-full bg-[#00FF87]/15 border border-[#00FF87]/30 flex items-center justify-center flex-shrink-0">
                  <Check className="w-3 h-3 text-[#00FF87]" />
                </div>
                <span className="text-sm text-[#A8B4D0]">{text}</span>
              </li>
            ))}
          </ul>

          {isPremium ? (
            <div className="w-full rounded-xl border border-[#00FF87]/30 bg-[#00FF87]/10 py-3.5 text-center text-sm font-bold text-[#00FF87]">
              {t.profile.included}
            </div>
          ) : (
            <>
              <button className="w-full bg-[#00FF87] text-[#070D1A] font-bold text-sm py-3.5 rounded-xl hover:bg-[#00e87a] active:scale-[0.98] transition-all shadow-[0_0_20px_rgba(0,255,135,0.3)]">
                {t.profile.upgrade}
              </button>
              <p className="text-center text-[10px] text-[#6A7A9B] mt-2.5">
                {t.profile.stripe}
              </p>
            </>
          )}
        </div>
      </div>

      {/* Menu items */}
      <div className="mx-5 rounded-2xl bg-card border border-[#1A2845] overflow-hidden">
        <div className="border-b border-[#1A2845]">
          <button
            onClick={() => setNotificationsOpen((open) => !open)}
            className="w-full flex items-center justify-between px-4 py-3.5 text-sm text-[#A8B4D0] hover:bg-[#0F1C35] active:bg-[#0F1C35] transition-colors"
            aria-expanded={notificationsOpen}
          >
            <span>{t.profile.notificationSettings}</span>
            {notificationsOpen ? (
              <ChevronDown className="w-4 h-4 text-[#6A7A9B]" />
            ) : (
              <ChevronRight className="w-4 h-4 text-[#6A7A9B]" />
            )}
          </button>
          {notificationsOpen && (
            <div className="border-t border-[#1A2845] bg-[#0A1325]/70 px-4 py-4">
              <p className="text-xs leading-relaxed text-[#6A7A9B]">{t.profile.notificationCopy}</p>
              <div className="mt-4 flex items-center justify-between gap-3">
                <span className="text-sm font-semibold text-foreground">{t.profile.language}</span>
                <div className="grid grid-cols-2 rounded-xl border border-[#1A2845] bg-[#070D1A] p-1">
                  <LanguageButton
                    isActive={language === "en"}
                    label={t.profile.english}
                    onClick={() => setLanguage("en")}
                  />
                  <LanguageButton
                    isActive={language === "es"}
                    label={t.profile.spanish}
                    onClick={() => setLanguage("es")}
                  />
                </div>
              </div>
            </div>
          )}
        </div>
        {menuItems.map(({ label, icon: Icon }, index) => (
          <button
            key={label}
            className={`w-full flex items-center justify-between px-4 py-3.5 text-sm text-[#A8B4D0] hover:bg-[#0F1C35] active:bg-[#0F1C35] transition-colors ${
              index < menuItems.length - 1 ? "border-b border-[#1A2845]" : ""
            }`}
          >
            <span>{label}</span>
            <Icon className="w-4 h-4 text-[#6A7A9B]" />
          </button>
        ))}
      </div>
    </div>
  )
}

function LanguageButton({
  isActive,
  label,
  onClick,
}: {
  isActive: boolean
  label: string
  onClick: () => void
}) {
  return (
    <button
      onClick={onClick}
      className={`min-w-[72px] rounded-lg px-3 py-1.5 text-xs font-bold transition-colors ${
        isActive
          ? "bg-[#00FF87] text-[#070D1A]"
          : "text-[#6A7A9B] hover:text-[#A8B4D0]"
      }`}
    >
      {label}
    </button>
  )
}
