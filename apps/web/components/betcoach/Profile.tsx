"use client"

import { useEffect, useState } from "react"
import { AlertCircle, Check, ChevronDown, ChevronRight, Clipboard, Copy, Crown, FileText, Globe2, GraduationCap, Handshake, LockKeyhole, MessageCircleMore, Pencil, PlayCircle, RefreshCw, Save, ShieldCheck, Store, UserRound, UsersRound, X } from "lucide-react"
import { applyReferralCode, createBarReferralPartner, getMyReferralDashboard, type CurrentUser, type ReferralDashboardResponse, updateCurrentUserName, updateCurrentUserProfile } from "@/lib/api"
import { useAuth } from "@/lib/auth"
import { useLanguage } from "@/lib/i18n"
import { usePreferences } from "@/lib/preferences"
import { displayUserName } from "@/lib/user-display"
import SectionHeader from "./SectionHeader"

export default function Profile({
  currentUser,
  isLoadingUser,
  userError,
  onRetryUser,
  onShowUpgradePrompt,
  onReplayOnboarding,
}: {
  currentUser: CurrentUser | null
  isLoadingUser: boolean
  userError: string | null
  onRetryUser: () => void
  onShowUpgradePrompt: () => void
  onReplayOnboarding: () => void
}) {
  const { language, setLanguage, t } = useLanguage()
  const { explanationLevel, setExplanationLevel } = usePreferences()
  const { isConfigured, signOut } = useAuth()
  const [openInfoSection, setOpenInfoSection] = useState<string | null>(null)
  const [isEditingName, setIsEditingName] = useState(false)
  const [nameDraft, setNameDraft] = useState(currentUser?.name ?? "")
  const [isSavingName, setIsSavingName] = useState(false)
  const [nameError, setNameError] = useState<string | null>(null)
  const [isEditingAvatar, setIsEditingAvatar] = useState(false)
  const [avatarDraft, setAvatarDraft] = useState(currentUser?.avatar_emoji ?? "👤")
  const [isSavingAvatar, setIsSavingAvatar] = useState(false)
  const [avatarError, setAvatarError] = useState<string | null>(null)
  const [referralDashboard, setReferralDashboard] = useState<ReferralDashboardResponse | null>(null)
  const [isLoadingReferrals, setIsLoadingReferrals] = useState(false)
  const [referralError, setReferralError] = useState<string | null>(null)
  const [referralRefreshKey, setReferralRefreshKey] = useState(0)
  const isPremium = currentUser?.plan === "premium"
  const chatLimit = currentUser?.chat_count_limit ?? currentUser?.daily_chat_count_limit ?? 5
  const chatsUsed = currentUser?.daily_chat_count ?? 0
  const chatsRemaining = currentUser?.chats_remaining ?? currentUser?.daily_chats_remaining
  const visibleChatsRemaining = chatsRemaining ?? Math.max(chatLimit - chatsUsed, 0)
  const usagePercent = isPremium ? 100 : Math.min((chatsUsed / chatLimit) * 100, 100)
  const isLowFreeQuota = !isPremium && visibleChatsRemaining <= 1
  const periodLabel = currentUser?.chat_limit_period === "week" ? t.chat.week : t.chat.day
  const appliedReferral = referralDashboard?.applied_referral ?? null
  const hasAppliedReferral = Boolean(appliedReferral)
  const standardPassPrice = 9.99
  const referralPassPrice = Math.max(standardPassPrice - (appliedReferral?.discount_amount ?? 0), 0)
  const displayName = displayUserName({
    name: currentUser?.name,
    email: currentUser?.email,
    fallback: t.profile.matchmindUser,
  })
  const accountLabel = currentUser?.email ?? t.profile.account
  const avatarEmoji = currentUser?.avatar_emoji || "👤"
  const menuItems = [
    {
      id: "responsible",
      label: t.profile.responsibleGambling,
      description: t.profile.responsibleCopy,
      details: t.profile.responsibleDetails,
      icon: ShieldCheck,
      link: { href: "https://www.ordenacionjuego.es/participantes-juego/juego-seguro/rgiaj", label: t.profile.responsibleSpain },
    },
    { id: "privacy", label: t.profile.privacy, description: t.profile.privacyCopy, details: t.profile.privacyDetails, icon: LockKeyhole },
    {
      id: "terms",
      label: t.profile.termsDisclaimer,
      description: t.profile.termsDisclaimerCopy,
      details: t.profile.termsDisclaimerDetails,
      icon: FileText,
    },
  ]

  useEffect(() => {
    setNameDraft(currentUser?.name ?? "")
  }, [currentUser?.name])

  useEffect(() => {
    setAvatarDraft(currentUser?.avatar_emoji ?? "👤")
  }, [currentUser?.avatar_emoji])

  useEffect(() => {
    if (!currentUser) return

    let isMounted = true
    setIsLoadingReferrals(true)
    setReferralError(null)
    getMyReferralDashboard()
      .then((dashboard) => {
        if (isMounted) setReferralDashboard(dashboard)
      })
      .catch((error) => {
        if (isMounted) setReferralError(error instanceof Error ? error.message : "No pudimos cargar tus referidos.")
      })
      .finally(() => {
        if (isMounted) setIsLoadingReferrals(false)
      })

    return () => {
      isMounted = false
    }
  }, [currentUser, referralRefreshKey])

  const refreshReferrals = () => setReferralRefreshKey((key) => key + 1)

  const saveName = async () => {
    const nextName = nameDraft.trim()
    if (!nextName) {
      setNameError(t.profile.nameRequired)
      return
    }
    setIsSavingName(true)
    setNameError(null)
    try {
      await updateCurrentUserName(nextName)
      setIsEditingName(false)
      onRetryUser()
    } catch (error) {
      setNameError(error instanceof Error ? error.message : t.profile.nameSaveError)
    } finally {
      setIsSavingName(false)
    }
  }

  const saveAvatar = async () => {
    const nextAvatar = avatarDraft.trim()
    if (!isSingleAvatarCharacter(nextAvatar)) {
      setAvatarError(t.profile.avatarRequired)
      return
    }
    setIsSavingAvatar(true)
    setAvatarError(null)
    try {
      await updateCurrentUserProfile({ avatar_emoji: nextAvatar })
      setIsEditingAvatar(false)
      onRetryUser()
    } catch (error) {
      setAvatarError(error instanceof Error ? error.message : t.profile.avatarSaveError)
    } finally {
      setIsSavingAvatar(false)
    }
  }

  return (
    <div className="flex h-full flex-col overflow-y-auto pb-[calc(5.75rem+env(safe-area-inset-bottom))]">
      <SectionHeader icon={UserRound} title={t.profile.title} subtitle={t.profile.subtitle} />

      {/* User card */}
      <div className="mx-4 mb-3 flex shrink-0 items-center gap-3 rounded-2xl border border-[#1A2845] bg-[#0F1C35] p-4 sm:mx-5 sm:gap-4">
        <div className="relative shrink-0">
          <div className="flex h-14 w-14 items-center justify-center rounded-full border-2 border-[#00FF87]/40 bg-gradient-to-br from-[#00FF87]/30 to-[#0F1C35]">
            {isEditingAvatar ? (
              <input
                className="h-10 w-10 rounded-full border border-[#00FF87]/30 bg-[#070D1A] text-center text-2xl outline-none focus:border-[#00FF87]"
                value={avatarDraft}
                onChange={(event) => {
                  const nextAvatar = event.target.value.trim()
                  if (!nextAvatar || isSingleAvatarCharacter(nextAvatar)) {
                    setAvatarDraft(nextAvatar)
                    setAvatarError(null)
                    return
                  }
                  setAvatarError(t.profile.avatarRequired)
                }}
                onKeyDown={(event) => {
                  if (event.key === "Enter") void saveAvatar()
                  if (event.key === "Escape") {
                    setIsEditingAvatar(false)
                    setAvatarDraft(currentUser?.avatar_emoji ?? "👤")
                    setAvatarError(null)
                  }
                }}
                maxLength={16}
                aria-label={t.profile.avatarEmoji}
                autoFocus
              />
            ) : (
              <span className="text-2xl">{avatarEmoji}</span>
            )}
          </div>
          <button
            className="absolute -bottom-1 -right-1 flex h-7 w-7 items-center justify-center rounded-lg border border-[#1A2845] bg-[#070D1A] text-[#6A7A9B] transition-colors hover:border-[#00FF87]/50 hover:text-[#00FF87]"
            aria-label={isEditingAvatar ? t.profile.saveAvatarEmoji : t.profile.editAvatarEmoji}
            onClick={() => {
              if (isEditingAvatar) {
                void saveAvatar()
              } else {
                setIsEditingAvatar(true)
              }
            }}
            disabled={isSavingAvatar}
            type="button"
          >
            {isSavingAvatar ? <RefreshCw className="h-3.5 w-3.5 animate-spin" /> : isEditingAvatar ? <Save className="h-3.5 w-3.5" /> : <Pencil className="h-3.5 w-3.5" />}
          </button>
        </div>
        <div className="min-w-0 flex-1">
          {isEditingName ? (
            <div className="flex min-w-0 items-center gap-2">
              <input
                className="min-w-0 flex-1 rounded-lg border border-[#1A2845] bg-[#070D1A] px-3 py-2 text-sm font-semibold text-foreground outline-none focus:border-[#00FF87]/60"
                value={nameDraft}
                onChange={(event) => setNameDraft(event.target.value)}
                maxLength={80}
                aria-label={t.profile.name}
              />
              <button
                className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-[#00FF87] text-[#070D1A] disabled:cursor-not-allowed disabled:opacity-60"
                aria-label={t.profile.saveName}
                onClick={() => void saveName()}
                disabled={isSavingName}
                type="button"
              >
                {isSavingName ? <RefreshCw className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
              </button>
              <button
                className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border border-[#1A2845] text-[#6A7A9B] transition-colors hover:text-foreground"
                aria-label={t.profile.cancelNameEdit}
                onClick={() => {
                  setIsEditingName(false)
                  setNameDraft(currentUser?.name ?? "")
                  setNameError(null)
                }}
                type="button"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
          ) : (
            <div className="flex min-w-0 items-center gap-2">
              <p className="truncate text-base font-bold text-foreground">{displayName}</p>
              <button
                className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg border border-[#1A2845] text-[#6A7A9B] transition-colors hover:border-[#00FF87]/50 hover:text-[#00FF87]"
                aria-label={t.profile.editName}
                onClick={() => setIsEditingName(true)}
                type="button"
              >
                <Pencil className="h-3.5 w-3.5" />
              </button>
            </div>
          )}
          <p className="truncate text-xs text-[#6A7A9B]">{accountLabel}</p>
          {avatarError && <p className="mt-1 text-xs font-semibold text-[#FF6B6B]">{avatarError}</p>}
          {nameError && <p className="mt-1 text-xs font-semibold text-[#FF6B6B]">{nameError}</p>}
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
          <div className={`mx-4 mb-3 shrink-0 rounded-2xl bg-card p-4 sm:mx-5 ${hasAppliedReferral ? "referral-banner-glow border border-[#00FF87]/50" : "border border-[#00FF87]/30"}`}>
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
              <div className="shrink-0 text-right" aria-live="polite">
                {hasAppliedReferral ? (
                  <div className="referral-price-pop">
                    <p className="text-[11px] font-bold uppercase text-[#00FF87]">Codigo {appliedReferral?.code}</p>
                    <div className="mt-1 flex items-end justify-end gap-2">
                      <span className="text-sm font-bold leading-none text-[#6A7A9B] line-through">{formatEuro(standardPassPrice)}</span>
                      <span className="text-2xl font-black leading-none text-[#00FF87]">{formatEuro(referralPassPrice)}</span>
                    </div>
                    <p className="mt-1 text-[10px] text-[#A8B4D0]">{formatEuro(appliedReferral?.discount_amount ?? 0)} de descuento</p>
                  </div>
                ) : (
                  <>
                    <p className="text-xl font-black leading-none text-foreground">{formatEuro(standardPassPrice)}</p>
                    <p className="mt-1 text-[10px] text-[#6A7A9B]">{t.profile.oneTime}</p>
                  </>
                )}
              </div>
            </div>

            <p className="mt-3 text-xs leading-relaxed text-[#A8B4D0]">
              {t.profile.upgradeCopy}
            </p>
            <p className="mt-2 text-[11px] leading-relaxed text-[#6A7A9B]">
              {t.profile.upgradeDisclaimer}
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

      <ReferralsSection
        dashboard={referralDashboard}
        isLoading={isLoadingReferrals}
        error={referralError}
        onRefresh={refreshReferrals}
      />

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
          onClick={onReplayOnboarding}
          className="flex w-full items-center justify-between gap-3 border-b border-[#1A2845] px-4 py-3.5 text-left text-sm text-[#A8B4D0] transition-colors hover:bg-[#0F1C35] active:bg-[#0F1C35]"
          type="button"
        >
          <span className="min-w-0">
            <span className="flex items-center gap-2 text-sm font-semibold text-[#A8B4D0]">
              <PlayCircle className="h-4 w-4 shrink-0 text-[#00FF87]" />
              {t.profile.replayTutorial}
            </span>
            <span className="mt-0.5 block text-xs leading-relaxed text-[#6A7A9B]">{t.profile.replayTutorialCopy}</span>
          </span>
          <ChevronRight className="w-4 h-4 shrink-0 text-[#6A7A9B]" />
        </button>

        <div className="border-b border-[#1A2845] px-4 py-3.5">
          <div className="mb-3 flex min-w-0 items-center gap-2">
            <GraduationCap className="h-4 w-4 shrink-0 text-[#00FF87]" />
            <span className="text-sm font-semibold text-[#A8B4D0]">{t.profile.explanationLevel}</span>
          </div>
          <div className="grid grid-cols-3 rounded-xl border border-[#1A2845] bg-[#070D1A] p-1">
            <ExplanationButton
              isActive={explanationLevel === "beginner"}
              label={t.profile.beginner}
              onClick={() => setExplanationLevel("beginner")}
            />
            <ExplanationButton
              isActive={explanationLevel === "standard"}
              label={t.profile.standard}
              onClick={() => setExplanationLevel("standard")}
            />
            <ExplanationButton
              isActive={explanationLevel === "advanced"}
              label={t.profile.advanced}
              onClick={() => setExplanationLevel("advanced")}
            />
          </div>
        </div>

        {menuItems.map(({ id, label, description, details, icon: Icon, link }, index) => (
          <div
            key={id}
            className={index < menuItems.length - 1 ? "border-b border-[#1A2845]" : ""}
          >
            <button
              className="flex w-full items-center justify-between gap-3 px-4 py-3.5 text-left transition-colors hover:bg-[#0F1C35] active:bg-[#0F1C35]"
              type="button"
              onClick={() => setOpenInfoSection((open) => (open === id ? null : id))}
              aria-expanded={openInfoSection === id}
            >
              <span className="min-w-0">
                <span className="flex items-center gap-2 text-sm font-semibold text-[#A8B4D0]">
                  <Icon className="h-4 w-4 shrink-0 text-[#00FF87]" />
                  {label}
                </span>
                <span className="mt-0.5 block text-xs leading-relaxed text-[#6A7A9B]">{description}</span>
              </span>
              {openInfoSection === id ? (
                <ChevronDown className="w-4 h-4 shrink-0 text-[#6A7A9B]" />
              ) : (
                <ChevronRight className="w-4 h-4 shrink-0 text-[#6A7A9B]" />
              )}
            </button>
            {openInfoSection === id && (
              <div className="bg-[#0A1325]/70 px-4 pb-4">
                <p className="text-xs leading-relaxed text-[#A8B4D0]">{details}</p>
                {link && (
                  <a
                    className="mt-2 inline-flex text-xs font-semibold text-[#00FF87] transition-colors hover:text-[#8DFFC2]"
                    href={link.href}
                    target="_blank"
                    rel="noreferrer"
                  >
                    {link.label}
                  </a>
                )}
              </div>
            )}
          </div>
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

function ReferralsSection({
  dashboard,
  isLoading,
  error,
  onRefresh,
}: {
  dashboard: ReferralDashboardResponse | null
  isLoading: boolean
  error: string | null
  onRefresh: () => void
}) {
  const [activeTab, setActiveTab] = useState<"bars" | "users">("bars")
  const [form, setForm] = useState({
    business_name: "",
    location: "",
    responsible_name: "",
    phone: "",
    terms_accepted: false,
  })
  const [formError, setFormError] = useState<string | null>(null)
  const [isCreating, setIsCreating] = useState(false)
  const [codeDraft, setCodeDraft] = useState("")
  const [applyStatus, setApplyStatus] = useState<string | null>(null)
  const [applyError, setApplyError] = useState<string | null>(null)
  const [isApplying, setIsApplying] = useState(false)
  const hasPartner = Boolean(dashboard?.has_bar_partner)
  const appliedReferral = dashboard?.applied_referral ?? null

  const updateField = (field: keyof typeof form, value: string | boolean) => {
    setForm((current) => ({ ...current, [field]: value }))
    setFormError(null)
  }

  const createPartner = async () => {
    const missingField = !form.business_name.trim() || !form.location.trim() || !form.responsible_name.trim() || !form.phone.trim()
    if (missingField) {
      setFormError("Completa todos los campos para crear el codigo del bar.")
      return
    }
    if (form.phone.trim().length < 6) {
      setFormError("Introduce un telefono o Bizum valido.")
      return
    }
    if (!form.terms_accepted) {
      setFormError("Debes aceptar las condiciones para crear el codigo.")
      return
    }

    setIsCreating(true)
    setFormError(null)
    try {
      await createBarReferralPartner({
        business_name: form.business_name.trim(),
        location: form.location.trim(),
        responsible_name: form.responsible_name.trim(),
        phone: form.phone.trim(),
        terms_accepted: form.terms_accepted,
      })
      onRefresh()
    } catch (requestError) {
      setFormError(requestError instanceof Error ? requestError.message : "No pudimos crear el codigo del bar.")
    } finally {
      setIsCreating(false)
    }
  }

  const applyCode = async () => {
    const normalizedCode = codeDraft.trim().toUpperCase()
    if (!normalizedCode) {
      setApplyError("Introduce un codigo.")
      return
    }

    setIsApplying(true)
    setApplyError(null)
    setApplyStatus(null)
    try {
      const response = await applyReferralCode(normalizedCode)
      setApplyStatus(`Codigo aplicado: ${response.code}. Tendras ${formatEuro(response.discount_amount)} de descuento en el World Pass.`)
      setCodeDraft("")
      onRefresh()
    } catch (requestError) {
      setApplyError(requestError instanceof Error ? requestError.message : "No pudimos aplicar este codigo.")
    } finally {
      setIsApplying(false)
    }
  }

  const copyCode = async () => {
    if (!dashboard?.code) return
    try {
      await navigator.clipboard.writeText(dashboard.code)
    } catch {
      return
    }
  }

  return (
    <section className="mx-4 mb-3 shrink-0 overflow-hidden rounded-2xl border border-[#1A2845] bg-card sm:mx-5">
      <div className="border-b border-[#1A2845] px-4 py-3.5">
        <div className="mb-3 flex items-center justify-between gap-3">
          <div className="flex min-w-0 items-center gap-2">
            <Handshake className="h-4 w-4 shrink-0 text-[#00FF87]" />
            <h2 className="text-sm font-bold text-foreground">Referrals</h2>
          </div>
          <button
            className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg border border-[#1A2845] text-[#6A7A9B] transition-colors hover:border-[#00FF87]/50 hover:text-[#00FF87]"
            type="button"
            onClick={onRefresh}
            aria-label="Actualizar referrals"
          >
            <RefreshCw className={`h-4 w-4 ${isLoading ? "animate-spin" : ""}`} />
          </button>
        </div>
        <div className="grid grid-cols-2 rounded-xl border border-[#1A2845] bg-[#070D1A] p-1">
          <ReferralTabButton active={activeTab === "bars"} label="Bars" icon={Store} onClick={() => setActiveTab("bars")} />
          <ReferralTabButton active={activeTab === "users"} label="Users" icon={UsersRound} onClick={() => setActiveTab("users")} />
        </div>
      </div>

      {error && (
        <div className="border-b border-[#1A2845] bg-[#FF4D4D]/10 px-4 py-3 text-xs font-semibold text-[#FF9A9A]">
          {error}
        </div>
      )}

      {activeTab === "users" ? (
        <div className="px-4 py-4">
          <p className="text-sm font-semibold text-foreground">Invita amigos pronto</p>
          <p className="mt-1 text-xs leading-relaxed text-[#A8B4D0]">
            Soon you will be able to invite friends and get perks on Matchmind.
          </p>
        </div>
      ) : (
        <div className="divide-y divide-[#1A2845]">
          <div className="px-4 py-4">
            {isLoading && !dashboard ? (
              <div className="flex items-center gap-2 text-sm text-[#A8B4D0]">
                <RefreshCw className="h-4 w-4 animate-spin text-[#00FF87]" />
                Cargando referrals...
              </div>
            ) : hasPartner ? (
              <BarPartnerDashboard dashboard={dashboard} onCopyCode={copyCode} />
            ) : (
              <BarPartnerForm
                form={form}
                formError={formError}
                isCreating={isCreating}
                onUpdateField={updateField}
                onSubmit={createPartner}
              />
            )}
          </div>
          <div className="px-4 py-4">
            <ReferralCodeApply
              appliedReferral={appliedReferral}
              codeDraft={codeDraft}
              applyStatus={applyStatus}
              applyError={applyError}
              isApplying={isApplying}
              onCodeChange={(value) => {
                setCodeDraft(value.toUpperCase())
                setApplyError(null)
                setApplyStatus(null)
              }}
              onApply={applyCode}
            />
          </div>
        </div>
      )}
    </section>
  )
}

function BarPartnerForm({
  form,
  formError,
  isCreating,
  onUpdateField,
  onSubmit,
}: {
  form: {
    business_name: string
    location: string
    responsible_name: string
    phone: string
    terms_accepted: boolean
  }
  formError: string | null
  isCreating: boolean
  onUpdateField: (field: keyof typeof form, value: string | boolean) => void
  onSubmit: () => void
}) {
  return (
    <div>
      <p className="text-sm font-semibold text-foreground">Colabora con Matchmind durante el Mundial</p>
      <p className="mt-2 text-xs leading-relaxed text-[#A8B4D0]">
        Si tienes un bar y compartes tu codigo con tus clientes, ellos tendran descuento en el World Pass y tu acumularas una comision por cada cliente que venga de tu bar y compre. El pago se hara al final del torneo.
      </p>

      <ul className="mt-4 space-y-2 text-xs leading-relaxed text-[#A8B4D0]">
        {[
          "Tus clientes reciben descuento usando tu codigo.",
          "Ganas €2 por cada cliente referido que compre el World Pass.",
          "El pago se hara al final del Mundial.",
          "Matchmind no acepta ni coloca apuestas.",
          "Solo usamos tu telefono para contacto y pagos manuales.",
        ].map((item) => (
          <li key={item} className="flex gap-2">
            <Check className="mt-0.5 h-3.5 w-3.5 shrink-0 text-[#00FF87]" />
            <span>{item}</span>
          </li>
        ))}
      </ul>

      <div className="mt-4 grid gap-3">
        <ReferralInput label="Nombre del bar" value={form.business_name} onChange={(value) => onUpdateField("business_name", value)} />
        <ReferralInput label="Ubicacion" value={form.location} onChange={(value) => onUpdateField("location", value)} />
        <ReferralInput label="Persona responsable" value={form.responsible_name} onChange={(value) => onUpdateField("responsible_name", value)} />
        <ReferralInput label="Telefono / Bizum" value={form.phone} onChange={(value) => onUpdateField("phone", value)} inputMode="tel" />
      </div>

      <label className="mt-4 flex items-start gap-3 rounded-xl border border-[#1A2845] bg-[#070D1A] p-3 text-xs leading-relaxed text-[#A8B4D0]">
        <input
          className="mt-0.5 h-4 w-4 accent-[#00FF87]"
          type="checkbox"
          checked={form.terms_accepted}
          onChange={(event) => onUpdateField("terms_accepted", event.target.checked)}
        />
        <span>
          Acepto que Matchmind use estos datos para gestionar mi codigo de partner, contactarme y procesar el pago manual de comisiones al final del torneo.
        </span>
      </label>

      {formError && <p className="mt-3 text-xs font-semibold text-[#FF6B6B]">{formError}</p>}
      <button
        className="mt-4 flex w-full items-center justify-center gap-2 rounded-xl bg-[#00FF87] py-3 text-sm font-bold text-[#070D1A] transition-colors hover:bg-[#00e87a] disabled:cursor-not-allowed disabled:opacity-60"
        type="button"
        onClick={onSubmit}
        disabled={isCreating}
      >
        {isCreating ? <RefreshCw className="h-4 w-4 animate-spin" /> : <Store className="h-4 w-4" />}
        Create bar code
      </button>
    </div>
  )
}

function BarPartnerDashboard({
  dashboard,
  onCopyCode,
}: {
  dashboard: ReferralDashboardResponse | null
  onCopyCode: () => void
}) {
  if (!dashboard) return null

  return (
    <div>
      <p className="text-sm font-semibold text-foreground">Tu codigo de bar</p>
      <div className="mt-3 flex flex-col gap-3 rounded-xl border border-[#00FF87]/25 bg-[#00FF87]/10 p-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <p className="text-3xl font-black tracking-normal text-[#00FF87]">{dashboard.code}</p>
          <button
            className="inline-flex items-center gap-2 rounded-lg border border-[#00FF87]/30 bg-[#070D1A] px-3 py-2 text-xs font-bold text-[#00FF87] transition-colors hover:bg-[#0F1C35]"
            type="button"
            onClick={onCopyCode}
          >
            <Copy className="h-3.5 w-3.5" />
            Copiar
          </button>
        </div>
        <p className="text-xs leading-relaxed text-[#A8B4D0]">Comparte este codigo con tus clientes. Precio con codigo: €8.99 ({formatEuro(dashboard.discount_amount)} discount).</p>
      </div>
      <div className="mt-4 grid grid-cols-2 gap-2">
        <ReferralMetric label="Usuarios registrados" value={dashboard.registered_referrals.toString()} />
        <ReferralMetric label="Usuarios que compraron" value={dashboard.paid_referrals.toString()} />
        <ReferralMetric label="Comision estimada" value={formatEuro(dashboard.estimated_payout)} />
        <ReferralMetric label="Pago esperado" value="Fin del Mundial" />
      </div>
      <p className="mt-3 text-xs leading-relaxed text-[#6A7A9B]">
        Las comisiones se revisaran y pagaran manualmente al final del torneo.
      </p>
    </div>
  )
}

function ReferralCodeApply({
  appliedReferral,
  codeDraft,
  applyStatus,
  applyError,
  isApplying,
  onCodeChange,
  onApply,
}: {
  appliedReferral: ReferralDashboardResponse["applied_referral"]
  codeDraft: string
  applyStatus: string | null
  applyError: string | null
  isApplying: boolean
  onCodeChange: (value: string) => void
  onApply: () => void
}) {
  return (
    <div>
      <div className="mb-3 flex items-center gap-2">
        <Clipboard className="h-4 w-4 text-[#00FF87]" />
        <p className="text-sm font-semibold text-foreground">Tengo un codigo de referido</p>
      </div>
      {appliedReferral ? (
        <div className="rounded-xl border border-[#1A2845] bg-[#070D1A] p-3">
          <p className="text-sm font-bold text-[#00FF87]">Codigo aplicado: {appliedReferral.code}</p>
          <p className="mt-1 text-xs leading-relaxed text-[#A8B4D0]">
            Tendras {formatEuro(appliedReferral.discount_amount)} de descuento en el World Pass. Por ahora no se puede cambiar el codigo aplicado.
          </p>
        </div>
      ) : (
        <>
          <div className="flex gap-2">
            <input
              className="min-w-0 flex-1 rounded-xl border border-[#1A2845] bg-[#070D1A] px-3 py-2.5 text-sm font-semibold uppercase tracking-normal text-foreground outline-none focus:border-[#00FF87]/60"
              value={codeDraft}
              onChange={(event) => onCodeChange(event.target.value)}
              placeholder="BAR"
              maxLength={80}
            />
            <button
              className="shrink-0 rounded-xl bg-[#00FF87] px-4 py-2 text-sm font-bold text-[#070D1A] transition-colors hover:bg-[#00e87a] disabled:cursor-not-allowed disabled:opacity-60"
              type="button"
              onClick={onApply}
              disabled={isApplying}
            >
              {isApplying ? <RefreshCw className="h-4 w-4 animate-spin" /> : "Aplicar"}
            </button>
          </div>
          {applyStatus && <p className="mt-2 text-xs font-semibold text-[#00FF87]">{applyStatus}</p>}
          {applyError && <p className="mt-2 text-xs font-semibold text-[#FF6B6B]">{applyError}</p>}
        </>
      )}
    </div>
  )
}

function ReferralInput({
  label,
  value,
  onChange,
  inputMode,
}: {
  label: string
  value: string
  onChange: (value: string) => void
  inputMode?: "tel"
}) {
  return (
    <label className="grid gap-1.5">
      <span className="text-xs font-semibold text-[#A8B4D0]">{label}</span>
      <input
        className="rounded-xl border border-[#1A2845] bg-[#070D1A] px-3 py-2.5 text-sm text-foreground outline-none focus:border-[#00FF87]/60"
        value={value}
        onChange={(event) => onChange(event.target.value)}
        inputMode={inputMode}
      />
    </label>
  )
}

function ReferralMetric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl border border-[#1A2845] bg-[#070D1A] p-3">
      <p className="text-[11px] leading-tight text-[#6A7A9B]">{label}</p>
      <p className="mt-1 text-sm font-bold text-foreground">{value}</p>
    </div>
  )
}

function ReferralTabButton({
  active,
  label,
  icon: Icon,
  onClick,
}: {
  active: boolean
  label: string
  icon: typeof Store
  onClick: () => void
}) {
  return (
    <button
      className={`flex min-w-0 items-center justify-center gap-1.5 rounded-lg px-3 py-2 text-xs font-bold transition-colors ${
        active ? "bg-[#00FF87] text-[#070D1A]" : "text-[#6A7A9B] hover:text-[#A8B4D0]"
      }`}
      type="button"
      onClick={onClick}
    >
      <Icon className="h-3.5 w-3.5" />
      {label}
    </button>
  )
}

function formatEuro(value: number) {
  return new Intl.NumberFormat("es-ES", { style: "currency", currency: "EUR" }).format(value)
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

function isSingleAvatarCharacter(value: string) {
  if (!value || /\s/.test(value)) return false
  const Segmenter = (
    Intl as typeof Intl & {
      Segmenter?: new (
        locales?: string | string[],
        options?: { granularity: "grapheme" },
      ) => { segment(input: string): Iterable<unknown> }
    }
  ).Segmenter

  if (Segmenter) {
    return Array.from(new Segmenter(undefined, { granularity: "grapheme" }).segment(value)).length === 1
  }

  return Array.from(value).length === 1
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

function ExplanationButton({
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
      className={`min-w-0 rounded-lg px-2 py-2 text-xs font-bold transition-colors ${
        isActive
          ? "bg-[#00FF87] text-[#070D1A]"
          : "text-[#6A7A9B] hover:text-[#A8B4D0]"
      }`}
      type="button"
    >
      {label}
    </button>
  )
}
