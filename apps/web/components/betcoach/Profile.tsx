"use client"

import { useState } from "react"
import { AlertCircle, Bell, Check, ChevronDown, ChevronRight, Crown, Globe2, MessageCircleMore, RefreshCw, ShieldCheck, UserRound } from "lucide-react"
import { type CurrentUser } from "@/lib/api"
import { useAuth } from "@/lib/auth"
import { useLanguage } from "@/lib/i18n"
import SectionHeader from "./SectionHeader"

export default function Profile({
  currentUser,
  isLoadingUser,
  userError,
  onRetryUser,
  onShowUpgradePrompt,
}: {
  currentUser: CurrentUser | null
  isLoadingUser: boolean
  userError: string | null
  onRetryUser: () => void
  onShowUpgradePrompt: () => void
}) {
  const { language, setLanguage, t } = useLanguage()
  const { isConfigured, signOut } = useAuth()
  const [notificationsOpen, setNotificationsOpen] = useState(false)
  const isPremium = currentUser?.plan === "premium"
  const chatLimit = currentUser?.chat_count_limit ?? currentUser?.daily_chat_count_limit ?? 5
  const chatsUsed = currentUser?.daily_chat_count ?? 0
  const chatsRemaining = currentUser?.chats_remaining ?? currentUser?.daily_chats_remaining
  const visibleChatsRemaining = chatsRemaining ?? Math.max(chatLimit - chatsUsed, 0)
  const usagePercent = isPremium ? 100 : Math.min((chatsUsed / chatLimit) * 100, 100)
  const isLowFreeQuota = !isPremium && visibleChatsRemaining <= 1
  const periodLabel = currentUser?.chat_limit_period === "week" ? t.chat.week : t.chat.day
  const accountLabel = currentUser?.email ?? t.profile.matchmindUser
  const menuItems = [
    { label: t.profile.responsibleGambling, description: t.profile.responsibleCopy, icon: ShieldCheck },
    { label: t.profile.help, description: t.profile.helpCopy, icon: ChevronRight },
    { label: t.profile.privacy, description: t.profile.privacyCopy, icon: ChevronRight },
  ]

  return (
    <div className="flex h-full flex-col overflow-y-auto pb-[calc(5.75rem+env(safe-area-inset-bottom))]">
      <SectionHeader icon={UserRound} title={t.profile.title} subtitle={t.profile.subtitle} />

      {/* User card */}
      <div className="mx-4 mb-3 flex shrink-0 items-center gap-3 rounded-2xl border border-[#1A2845] bg-[#0F1C35] p-4 sm:mx-5 sm:gap-4">
        <div className="relative shrink-0">
          <div className="flex h-14 w-14 items-center justify-center rounded-full border-2 border-[#00FF87]/40 bg-gradient-to-br from-[#00FF87]/30 to-[#0F1C35]">
            <span className="text-2xl">👤</span>
          </div>
        </div>
        <div className="min-w-0 flex-1">
          <p className="truncate text-base font-bold text-foreground">{accountLabel}</p>
          <p className="text-xs text-[#6A7A9B]">{t.profile.account}</p>
          <div className="mt-1.5 flex flex-wrap items-center gap-1.5">
            <div className={`rounded-full px-2.5 py-0.5 ${isPremium ? "border border-[#00FF87]/25 bg-[#00FF87]/10" : "bg-[#1A2845]"}`}>
              <span className={`text-[10px] font-semibold uppercase tracking-wide ${isPremium ? "text-[#00FF87]" : "text-[#6A7A9B]"}`}>
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
        <div className="mx-4 mb-3 shrink-0 rounded-xl border border-[#FF4D4D]/30 bg-[#FF4D4D]/10 p-4 sm:mx-5">
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

      {isPremium ? (
        <div className="mx-4 mb-3 shrink-0 divide-y divide-[#1A2845] overflow-hidden rounded-2xl border border-[#1A2845] bg-card sm:mx-5">
          <StatusRow
            title={t.profile.fairUseChatsTitle}
            description={t.profile.noDailyCap}
            value={t.profile.unlimited}
            tone="green"
          />
          <StatusRow
            title={t.profile.pass}
            description={t.profile.premiumSummary}
            value={t.profile.paidBadge}
            tone="gold"
          />
        </div>
      ) : (
        <>
          {/* Usage */}
          <div className="mx-4 mb-3 shrink-0 rounded-2xl border border-[#1A2845] bg-card p-4 sm:mx-5">
            <div className="mb-3 flex flex-wrap items-center justify-between gap-1.5">
              <p className="text-sm font-semibold text-foreground">{t.profile.dailyChats}</p>
              <span className="text-right text-xs text-[#6A7A9B]">{t.profile.resets}</span>
            </div>
            <div className="flex items-center gap-3">
              <div className="h-2 min-w-[120px] flex-1 overflow-hidden rounded-full bg-[#1A2845]">
                <div
                  className={`h-full rounded-full transition-all ${isLowFreeQuota ? "bg-[#FF4D4D]" : "bg-[#00FF87]"}`}
                  style={{ width: `${usagePercent}%` }}
                />
              </div>
              <span className={`flex-shrink-0 text-sm font-bold ${isLowFreeQuota ? "text-[#FF6B6B]" : "text-foreground"}`}>
                {chatsUsed}/{chatLimit}
              </span>
            </div>
            <div className="mt-3 flex flex-wrap items-center justify-between gap-2">
              <p className={`text-[11px] font-semibold ${isLowFreeQuota ? "text-[#FF6B6B]" : "text-[#6A7A9B]"}`}>
                {visibleChatsRemaining} {t.chat.left}/{periodLabel}
              </p>
              <button
                type="button"
                onClick={onShowUpgradePrompt}
                className="inline-flex items-center gap-1.5 rounded-lg border border-[#00FF87]/25 bg-[#00FF87]/10 px-2.5 py-1.5 text-[11px] font-bold text-[#00FF87] transition-colors hover:bg-[#00FF87]/15"
              >
                <MessageCircleMore className="h-3.5 w-3.5" />
                {t.profile.moreMessages}
              </button>
            </div>
          </div>

          {/* Upgrade card */}
          <div className="mx-4 mb-3 shrink-0 rounded-2xl border border-[#00FF87]/30 bg-card p-4 sm:mx-5">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div className="min-w-[190px] flex-1">
                <div className="mb-2 flex items-center gap-2">
                  <Crown className="h-4 w-4 shrink-0 text-[#00FF87]" />
                  <span className="text-[10px] font-bold uppercase tracking-widest text-[#00FF87]">
                    {t.profile.pass}
                  </span>
                </div>
                <p className="text-base font-bold leading-snug text-foreground">
                  {t.profile.unlock}
                </p>
              </div>
              <div className="shrink-0 text-right">
                <p className="text-xl font-black leading-none text-foreground">€9.99</p>
                <p className="mt-1 text-[10px] text-[#6A7A9B]">{t.profile.oneTime}</p>
              </div>
            </div>

            <p className="mt-3 text-xs leading-relaxed text-[#A8B4D0]">
              {t.profile.upgradeCopy}
            </p>

            <div className="mt-4">
              <ul className="mb-4 flex flex-col gap-2.5">
                {t.profile.features.slice(0, 3).map((text) => (
                  <li key={text} className="flex items-start gap-3">
                    <div className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full border border-[#00FF87]/30 bg-[#00FF87]/15">
                      <Check className="h-3 w-3 text-[#00FF87]" />
                    </div>
                    <span className="min-w-0 text-sm leading-snug text-[#A8B4D0]">{text}</span>
                  </li>
                ))}
              </ul>
              <button
                className="flex w-full items-center justify-center gap-2 rounded-xl bg-[#00FF87] py-3.5 text-sm font-bold text-[#070D1A] shadow-[0_0_20px_rgba(0,255,135,0.3)] transition-all hover:bg-[#00e87a] active:scale-[0.98] disabled:cursor-not-allowed disabled:opacity-70"
                type="button"
                onClick={onShowUpgradePrompt}
              >
                {t.profile.upgrade}
              </button>
              <p className="mt-2.5 text-center text-[10px] text-[#6A7A9B]">
                {t.profile.stripe}
              </p>
            </div>
          </div>
        </>
      )}

      {/* Settings */}
      <div className="mx-4 shrink-0 overflow-hidden rounded-2xl border border-[#1A2845] bg-card sm:mx-5">
        <div className="flex flex-col gap-3 border-b border-[#1A2845] px-4 py-3.5 min-[390px]:flex-row min-[390px]:items-center min-[390px]:justify-between">
          <div className="flex min-w-0 items-center gap-2">
            <Globe2 className="h-4 w-4 shrink-0 text-[#00FF87]" />
            <span className="text-sm font-semibold text-[#A8B4D0]">{t.profile.language}</span>
          </div>
          <div className="grid w-full grid-cols-2 rounded-xl border border-[#1A2845] bg-[#070D1A] p-1 min-[390px]:w-auto min-[390px]:shrink-0">
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

        <button
          onClick={() => setNotificationsOpen((open) => !open)}
          className="flex w-full items-center justify-between gap-3 border-b border-[#1A2845] px-4 py-3.5 text-left text-sm text-[#A8B4D0] transition-colors hover:bg-[#0F1C35] active:bg-[#0F1C35]"
          aria-expanded={notificationsOpen}
        >
          <span className="flex min-w-0 items-center gap-2">
            <Bell className="h-4 w-4 shrink-0 text-[#6A7A9B]" />
            {t.profile.notificationSettings}
          </span>
          {notificationsOpen ? (
            <ChevronDown className="w-4 h-4 text-[#6A7A9B]" />
          ) : (
            <ChevronRight className="w-4 h-4 text-[#6A7A9B]" />
          )}
        </button>
        {notificationsOpen && (
          <div className="border-b border-[#1A2845] bg-[#0A1325]/70 px-4 py-3">
            <p className="text-xs leading-relaxed text-[#6A7A9B]">{t.profile.notificationCopy}</p>
          </div>
        )}
        {menuItems.map(({ label, description, icon: Icon }, index) => (
          <button
            key={label}
            className={`flex w-full items-center justify-between gap-3 px-4 py-3.5 text-left transition-colors hover:bg-[#0F1C35] active:bg-[#0F1C35] ${
              index < menuItems.length - 1 ? "border-b border-[#1A2845]" : ""
            }`}
          >
            <span className="min-w-0">
              <span className="flex items-center gap-2 text-sm font-semibold text-[#A8B4D0]">
                {Icon === ShieldCheck && <Icon className="h-4 w-4 shrink-0 text-[#00FF87]" />}
                {label}
              </span>
              <span className="mt-0.5 block text-xs leading-relaxed text-[#6A7A9B]">{description}</span>
            </span>
            <ChevronRight className="w-4 h-4 shrink-0 text-[#6A7A9B]" />
          </button>
        ))}
      </div>
      {isConfigured && (
        <button
          className="mx-4 mt-3 shrink-0 rounded-2xl border border-[#1A2845] bg-card px-4 py-3 text-sm font-semibold text-[#A8B4D0] transition-colors hover:bg-[#0F1C35] sm:mx-5"
          type="button"
          onClick={() => void signOut()}
        >
          {language === "es" ? "Cerrar sesión" : "Sign out"}
        </button>
      )}
    </div>
  )
}

function StatusRow({
  title,
  description,
  value,
  tone,
}: {
  title: string
  description: string
  value: string
  tone: "green" | "gold"
}) {
  const toneClass =
    tone === "green"
      ? "border-[#00FF87]/25 bg-[#00FF87]/10 text-[#00FF87]"
      : "border-[#D8B866]/25 bg-[#D8B866]/8 text-[#E8D39A]"

  return (
    <div className="flex flex-wrap items-center justify-between gap-3 px-4 py-3.5">
      <div className="min-w-[180px] flex-1">
        <p className="text-sm font-semibold text-[#A8B4D0]">{title}</p>
        <p className="mt-0.5 text-xs leading-relaxed text-[#6A7A9B]">{description}</p>
      </div>
      <div className={`shrink-0 rounded-full border px-3 py-1 ${toneClass}`}>
        <span className="text-[11px] font-bold">{value}</span>
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
      className={`min-w-0 rounded-lg px-3 py-2 text-xs font-bold transition-colors ${
        isActive
          ? "bg-[#00FF87] text-[#070D1A]"
          : "text-[#6A7A9B] hover:text-[#A8B4D0]"
      }`}
    >
      {label}
    </button>
  )
}
