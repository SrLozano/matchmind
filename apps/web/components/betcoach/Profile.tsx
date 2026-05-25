"use client"

import { useEffect, useState } from "react"
import { AlertCircle, Check, ChevronDown, ChevronRight, Clipboard, Copy, Crown, FileText, Globe2, GraduationCap, Handshake, LockKeyhole, MessageCircleMore, Pencil, PlayCircle, RefreshCw, Save, ShieldCheck, Store, UserRound, UsersRound, X } from "lucide-react"
import { applyReferralCode, createBarReferralPartner, createUserReferralCode, getMyReferralDashboard, type CurrentUser, type ReferralDashboardResponse, type UserReferralTierKey, updateCurrentUserName, updateCurrentUserProfile } from "@/lib/api"
import { useAuth } from "@/lib/auth"
import { useLanguage } from "@/lib/i18n"
import { usePreferences } from "@/lib/preferences"
import { getBestPassPriceOffer } from "@/lib/referral-pricing"
import { displayUserName } from "@/lib/user-display"
import SectionHeader from "./SectionHeader"

const USER_REFERRAL_TIER_ORDER: UserReferralTierKey[] = ["scout", "insider", "captain", "legend", "founder_circle"]

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
  const passOffer = getBestPassPriceOffer(referralDashboard)
  const referralLoadError = t.profile.referrals.loadError
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
        if (isMounted) setReferralError(error instanceof Error ? error.message : referralLoadError)
      })
      .finally(() => {
        if (isMounted) setIsLoadingReferrals(false)
      })

    return () => {
      isMounted = false
    }
  }, [currentUser, referralRefreshKey, referralLoadError])

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
          <div className={`mx-4 mb-3 shrink-0 rounded-2xl bg-card p-4 sm:mx-5 ${passOffer.isDiscounted ? "referral-banner-glow border border-[#00FF87]/50" : "border border-[#00FF87]/30"}`}>
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
                {passOffer.isDiscounted ? (
                  <div className="referral-price-pop">
                    <p className="text-[11px] font-bold uppercase text-[#00FF87]">
                      {passOffer.appliedCode
                        ? `${t.profile.referrals.codeLabel} ${passOffer.appliedCode}`
                        : passOffer.tierKey
                          ? t.profile.referrals.tierLabels[passOffer.tierKey]
                          : t.profile.referrals.unlockedPrice}
                    </p>
                    <div className="mt-1 flex items-end justify-end gap-2">
                      <span className="text-sm font-bold leading-none text-[#6A7A9B] line-through">{formatEuro(passOffer.standardPrice)}</span>
                      <span className="text-2xl font-black leading-none text-[#00FF87]">{formatPassPrice(passOffer.price, t.profile.referrals.freePrice)}</span>
                    </div>
                  </div>
                ) : (
                  <>
                    <p className="text-xl font-black leading-none text-foreground">{formatEuro(passOffer.standardPrice)}</p>
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
        isPremium={isPremium}
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
  isPremium,
  onRefresh,
}: {
  dashboard: ReferralDashboardResponse | null
  isLoading: boolean
  error: string | null
  isPremium: boolean
  onRefresh: () => void
}) {
  const { t } = useLanguage()
  const copy = t.profile.referrals
  const [activeTab, setActiveTab] = useState<"bars" | "users">("users")
  const [form, setForm] = useState({
    business_name: "",
    location: "",
    responsible_name: "",
    phone: "",
    terms_accepted: false,
  })
  const [formError, setFormError] = useState<string | null>(null)
  const [isCreating, setIsCreating] = useState(false)
  const [isCreatingUserCode, setIsCreatingUserCode] = useState(false)
  const [userCodeError, setUserCodeError] = useState<string | null>(null)
  const [codeDraft, setCodeDraft] = useState("")
  const [applyStatus, setApplyStatus] = useState<string | null>(null)
  const [applyError, setApplyError] = useState<string | null>(null)
  const [isApplying, setIsApplying] = useState(false)
  const [isPartnerSignupOpen, setIsPartnerSignupOpen] = useState(false)
  const hasPartner = Boolean(dashboard?.has_bar_partner)
  const appliedReferral = dashboard?.applied_referral ?? null
  const userReferral = dashboard?.user_referral ?? null

  const updateField = (field: keyof typeof form, value: string | boolean) => {
    setForm((current) => ({ ...current, [field]: value }))
    setFormError(null)
  }

  const createPartner = async () => {
    const missingField = !form.business_name.trim() || !form.location.trim() || !form.responsible_name.trim() || !form.phone.trim()
    if (missingField) {
      setFormError(copy.missingFields)
      return
    }
    if (form.phone.trim().length < 6) {
      setFormError(copy.invalidPhone)
      return
    }
    if (!form.terms_accepted) {
      setFormError(copy.termsRequired)
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
      setFormError(translateReferralApiError(requestError, copy, copy.createError))
    } finally {
      setIsCreating(false)
    }
  }

  const createPersonalCode = async () => {
    setIsCreatingUserCode(true)
    setUserCodeError(null)
    try {
      await createUserReferralCode()
      onRefresh()
    } catch (requestError) {
      setUserCodeError(translateReferralApiError(requestError, copy, copy.userCreateError))
    } finally {
      setIsCreatingUserCode(false)
    }
  }

  const applyCode = async () => {
    const normalizedCode = codeDraft.trim().toUpperCase()
    if (!normalizedCode) {
      setApplyError(copy.applyMissingCode)
      return
    }

    setIsApplying(true)
    setApplyError(null)
    setApplyStatus(null)
    try {
      const response = await applyReferralCode(normalizedCode)
      setApplyStatus(copy.applySuccess.replace("{code}", response.code))
      setCodeDraft("")
      onRefresh()
    } catch (requestError) {
      setApplyError(translateReferralApiError(requestError, copy, copy.applyError))
    } finally {
      setIsApplying(false)
    }
  }

  const copyCode = async (code: string | null | undefined) => {
    if (!code) return
    try {
      await navigator.clipboard.writeText(code)
    } catch {
      return
    }
  }

  return (
    <section className="mx-4 mb-3 shrink-0 overflow-hidden rounded-2xl border border-[#1A2845] bg-card sm:mx-5">
      <div className="border-b border-[#1A2845] px-4 py-3.5">
        <div className="flex items-center justify-between gap-3">
          <div className="flex min-w-0 items-center gap-2">
            <Handshake className="h-4 w-4 shrink-0 text-[#00FF87]" />
            <h2 className="text-sm font-bold text-foreground">{copy.title}</h2>
          </div>
          <button
            className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg border border-[#1A2845] text-[#6A7A9B] transition-colors hover:border-[#00FF87]/50 hover:text-[#00FF87]"
            type="button"
            onClick={onRefresh}
            aria-label={copy.refresh}
          >
            <RefreshCw className={`h-4 w-4 ${isLoading ? "animate-spin" : ""}`} />
          </button>
        </div>
      </div>

      {error && (
        <div className="border-b border-[#1A2845] bg-[#FF4D4D]/10 px-4 py-3 text-xs font-semibold text-[#FF9A9A]">
          {error}
        </div>
      )}

      <div className="divide-y divide-[#1A2845]">
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

        <div>
          <button
            className="flex w-full items-center justify-between gap-3 px-4 py-4 text-left transition-colors hover:bg-[#0F1C35] active:bg-[#0F1C35]"
            type="button"
            onClick={() => setIsPartnerSignupOpen((isOpen) => !isOpen)}
            aria-expanded={isPartnerSignupOpen}
          >
            <span className="min-w-0">
              <span className="flex items-center gap-2 text-sm font-bold text-foreground">
                <UsersRound className="h-4 w-4 shrink-0 text-[#00FF87]" />
                {copy.ownCodeTitle}
              </span>
              <span className="mt-1 block text-xs leading-relaxed text-[#6A7A9B]">
                {copy.ownCodeSubtitle}
              </span>
            </span>
            {isPartnerSignupOpen ? (
              <ChevronDown className="h-4 w-4 shrink-0 text-[#6A7A9B]" />
            ) : (
              <ChevronRight className="h-4 w-4 shrink-0 text-[#6A7A9B]" />
            )}
          </button>

          {isPartnerSignupOpen && (
            <div className="border-t border-[#1A2845] px-4 py-4">
              <div className="mb-4 grid grid-cols-2 rounded-xl border border-[#1A2845] bg-[#070D1A] p-1">
                <ReferralTabButton active={activeTab === "users"} label={copy.usersTab} icon={UsersRound} onClick={() => setActiveTab("users")} />
                <ReferralTabButton active={activeTab === "bars"} label={copy.barsTab} icon={Store} onClick={() => setActiveTab("bars")} />
              </div>

              {activeTab === "users" ? (
                <UserReferralPanel
                  userReferral={userReferral}
                  isLoading={isLoading}
                  isCreating={isCreatingUserCode}
                  error={userCodeError}
                  isPremium={isPremium}
                  onCreate={createPersonalCode}
                  onCopyCode={() => copyCode(userReferral?.code)}
                />
              ) : isLoading && !dashboard ? (
                <div className="flex items-center gap-2 text-sm text-[#A8B4D0]">
                  <RefreshCw className="h-4 w-4 animate-spin text-[#00FF87]" />
                  {copy.loading}
                </div>
              ) : hasPartner ? (
                <BarPartnerDashboard dashboard={dashboard} onCopyCode={() => copyCode(dashboard?.code)} />
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
          )}
        </div>
      </div>
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
  const { t } = useLanguage()
  const copy = t.profile.referrals

  return (
    <div>
      <p className="text-sm font-semibold text-foreground">{copy.barIntroTitle}</p>
      <p className="mt-2 text-xs leading-relaxed text-[#A8B4D0]">
        {copy.barIntroCopy}
      </p>

      <ul className="mt-4 space-y-2 text-xs leading-relaxed text-[#A8B4D0]">
        {copy.barConditions.map((item) => (
          <li key={item} className="flex gap-2">
            <Check className="mt-0.5 h-3.5 w-3.5 shrink-0 text-[#00FF87]" />
            <span>{item}</span>
          </li>
        ))}
      </ul>

      <div className="mt-4 grid gap-3">
        <ReferralInput label={copy.businessName} value={form.business_name} onChange={(value) => onUpdateField("business_name", value)} />
        <ReferralInput label={copy.location} value={form.location} onChange={(value) => onUpdateField("location", value)} />
        <ReferralInput label={copy.responsibleName} value={form.responsible_name} onChange={(value) => onUpdateField("responsible_name", value)} />
        <ReferralInput label={copy.phone} value={form.phone} onChange={(value) => onUpdateField("phone", value)} inputMode="tel" />
      </div>

      <label className="mt-4 flex items-start gap-3 rounded-xl border border-[#1A2845] bg-[#070D1A] p-3 text-xs leading-relaxed text-[#A8B4D0]">
        <input
          className="mt-0.5 h-4 w-4 accent-[#00FF87]"
          type="checkbox"
          checked={form.terms_accepted}
          onChange={(event) => onUpdateField("terms_accepted", event.target.checked)}
        />
        <span>
          {copy.terms}
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
        {copy.createButton}
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
  const { t } = useLanguage()
  const copy = t.profile.referrals

  if (!dashboard) return null

  return (
    <div>
      <p className="text-sm font-semibold text-foreground">{copy.barCodeTitle}</p>
      <div className="mt-3 flex flex-col gap-3 rounded-xl border border-[#00FF87]/25 bg-[#00FF87]/10 p-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <p className="text-3xl font-black tracking-normal text-[#00FF87]">{dashboard.code}</p>
          <button
            className="inline-flex items-center gap-2 rounded-lg border border-[#00FF87]/30 bg-[#070D1A] px-3 py-2 text-xs font-bold text-[#00FF87] transition-colors hover:bg-[#0F1C35]"
            type="button"
            onClick={onCopyCode}
          >
            <Copy className="h-3.5 w-3.5" />
            {copy.copy}
          </button>
        </div>
        <p className="text-xs leading-relaxed text-[#A8B4D0]">{copy.shareCode}</p>
      </div>
      <div className="mt-4 grid grid-cols-2 gap-2">
        <ReferralMetric label={copy.registeredUsers} value={dashboard.registered_referrals.toString()} />
        <ReferralMetric label={copy.paidUsers} value={dashboard.paid_referrals.toString()} />
        <ReferralMetric label={copy.estimatedCommission} value={formatEuro(dashboard.estimated_payout)} />
        <ReferralMetric label={copy.expectedPayment} value={copy.endOfWorldCup} />
      </div>
      <p className="mt-3 text-xs leading-relaxed text-[#6A7A9B]">
        {copy.manualReview}
      </p>
    </div>
  )
}

function UserReferralPanel({
  userReferral,
  isLoading,
  isCreating,
  error,
  isPremium,
  onCreate,
  onCopyCode,
}: {
  userReferral: ReferralDashboardResponse["user_referral"] | null
  isLoading: boolean
  isCreating: boolean
  error: string | null
  isPremium: boolean
  onCreate: () => void
  onCopyCode: () => void
}) {
  const { t } = useLanguage()
  const copy = t.profile.referrals
  const hasCode = Boolean(userReferral?.has_code && userReferral.code)
  const perks = userReferral?.perks
  const currentTier = perks?.current_tier ?? null
  const nextTier = perks?.next_tier ?? null
  const currentPerkValue = currentTier ? copy.tierRewards[currentTier.key] : copy.noPerkYet
  const currentStatus = currentTier ? copy.tierLabels[currentTier.key] : copy.progressStart
  const nextPerkValue = nextTier
    ? `${copy.tierRewards[nextTier.key]} · ${formatReferralRequirement(perks, copy)}`
    : copy.allPerksUnlocked
  const nextAction = formatReferralAction(perks, copy)
  const unlockedPrice = formatEuro(perks?.unlocked_pass_price ?? 9.99)

  if (isLoading && !userReferral) {
    return (
      <div className="flex items-center gap-2 text-sm text-[#A8B4D0]">
        <RefreshCw className="h-4 w-4 animate-spin text-[#00FF87]" />
        {copy.loading}
      </div>
    )
  }

  if (!hasCode) {
    return (
      <div>
        <p className="text-sm font-semibold text-foreground">{copy.userInviteTitle}</p>
        <p className="mt-2 text-xs leading-relaxed text-[#A8B4D0]">
          {copy.userInviteCopy}
        </p>

        <ul className="mt-4 space-y-2 text-xs leading-relaxed text-[#A8B4D0]">
          {copy.userInviteBullets.map((item) => (
            <li key={item} className="flex gap-2">
              <Check className="mt-0.5 h-3.5 w-3.5 shrink-0 text-[#00FF87]" />
              <span>{item}</span>
            </li>
          ))}
        </ul>

        {error && <p className="mt-3 text-xs font-semibold text-[#FF6B6B]">{error}</p>}
        <button
          className="mt-4 flex w-full items-center justify-center gap-2 rounded-xl bg-[#00FF87] py-3 text-sm font-bold text-[#070D1A] transition-colors hover:bg-[#00e87a] disabled:cursor-not-allowed disabled:opacity-60"
          type="button"
          onClick={onCreate}
          disabled={isCreating}
        >
          {isCreating ? <RefreshCw className="h-4 w-4 animate-spin" /> : <UsersRound className="h-4 w-4" />}
          {copy.userCreateButton}
        </button>
      </div>
    )
  }

  return (
    <div>
      <p className="text-sm font-semibold text-foreground">{copy.userCodeTitle}</p>
      <div className="mt-3 flex flex-col gap-3 rounded-xl border border-[#00FF87]/25 bg-[#00FF87]/10 p-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <p className="text-3xl font-black tracking-normal text-[#00FF87]">{userReferral?.code}</p>
          <button
            className="inline-flex items-center gap-2 rounded-lg border border-[#00FF87]/30 bg-[#070D1A] px-3 py-2 text-xs font-bold text-[#00FF87] transition-colors hover:bg-[#0F1C35]"
            type="button"
            onClick={onCopyCode}
          >
            <Copy className="h-3.5 w-3.5" />
            {copy.copy}
          </button>
        </div>
        <p className="text-xs leading-relaxed text-[#A8B4D0]">{copy.userShareCode}</p>
      </div>
      <UserReferralProgress userReferral={userReferral} />
      <div className="mt-4 rounded-xl border border-[#D8B866]/30 bg-[#D8B866]/8 p-3">
        <p className="text-[11px] font-semibold uppercase tracking-normal text-[#E8D39A]">{copy.nextAction}</p>
        <p className="mt-1 text-sm font-bold leading-relaxed text-foreground">{nextAction}</p>
      </div>
      <div className="mt-4 grid grid-cols-1 gap-2 sm:grid-cols-3">
        <ReferralMetric label={copy.friendsRegistered} value={(userReferral?.registered_referrals ?? 0).toString()} />
        <ReferralMetric label={copy.friendsPurchased} value={(userReferral?.paid_referrals ?? 0).toString()} />
        <ReferralMetric label={copy.currentTier} value={currentStatus} />
      </div>
      <div className="mt-4 rounded-xl border border-[#1A2845] bg-[#070D1A] p-3">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-normal text-[#6A7A9B]">{copy.currentPerk}</p>
            <p className="mt-1 text-sm font-bold text-foreground">{currentPerkValue}</p>
          </div>
          <div className="rounded-lg border border-[#00FF87]/25 bg-[#00FF87]/10 px-3 py-2 text-right">
            <p className="text-[10px] font-semibold text-[#6A7A9B]">{copy.unlockedPrice}</p>
            <p className="text-sm font-black text-[#00FF87]">{unlockedPrice}</p>
          </div>
        </div>
        <div className="mt-3 border-t border-[#1A2845] pt-3">
          <p className="text-[11px] font-semibold uppercase tracking-normal text-[#6A7A9B]">{copy.nextPerk}</p>
          <p className="mt-1 text-xs font-semibold leading-relaxed text-[#A8B4D0]">{nextPerkValue}</p>
          {isPremium && (
            <p className="mt-2 text-xs leading-relaxed text-[#00FF87]">
              {(perks?.unlocked_pass_price ?? 9.99) <= 0 ? copy.futureCreditFree : copy.futureCredit}
            </p>
          )}
          {perks?.beta_priority && (
            <p className="mt-2 text-xs leading-relaxed text-[#E8D39A]">{copy.betaPriority}</p>
          )}
        </div>
      </div>
    </div>
  )
}

function UserReferralProgress({
  userReferral,
}: {
  userReferral: ReferralDashboardResponse["user_referral"] | null
}) {
  const { t } = useLanguage()
  const copy = t.profile.referrals
  if (!userReferral) return null

  const currentTierKey = userReferral.perks.current_tier?.key ?? null
  const currentIndex = currentTierKey ? USER_REFERRAL_TIER_ORDER.indexOf(currentTierKey) : -1
  const progressPercent = currentIndex < 0 ? 0 : (currentIndex / (USER_REFERRAL_TIER_ORDER.length - 1)) * 100

  return (
    <div className="mt-4 rounded-xl border border-[#1A2845] bg-[#070D1A] p-3">
      <div className="flex items-center justify-between gap-3">
        <p className="text-xs font-bold text-foreground">{copy.progressTitle}</p>
        <p className="text-[11px] font-semibold text-[#6A7A9B]">
          {currentTierKey ? copy.tierLabels[currentTierKey] : copy.progressStart}
        </p>
      </div>
      <div className="mt-3 h-2 overflow-hidden rounded-full bg-[#101B32]" aria-label={copy.progressTitle}>
        <div className="h-full rounded-full bg-[#00FF87] transition-all" style={{ width: `${progressPercent}%` }} />
      </div>
      <div className="mt-3 grid gap-2">
        {USER_REFERRAL_TIER_ORDER.map((tierKey, index) => {
          const isUnlocked = index <= currentIndex
          const isNext = userReferral.perks.next_tier?.key === tierKey
          return (
            <div
              key={tierKey}
              className={`flex items-start gap-3 rounded-lg border p-2.5 ${
                isUnlocked
                  ? "border-[#00FF87]/30 bg-[#00FF87]/10"
                  : isNext
                    ? "border-[#D8B866]/30 bg-[#D8B866]/8"
                    : "border-[#1A2845] bg-[#0B1426]"
              }`}
            >
              <span
                className={`mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full border text-[10px] font-black ${
                  isUnlocked
                    ? "border-[#00FF87] bg-[#00FF87] text-[#070D1A]"
                    : isNext
                      ? "border-[#D8B866] text-[#E8D39A]"
                      : "border-[#263653] text-[#6A7A9B]"
                }`}
              >
                {isUnlocked ? <Check className="h-3 w-3" /> : index + 1}
              </span>
              <span className="min-w-0 flex-1">
                <span className="flex flex-wrap items-center gap-2">
                  <span className="text-xs font-bold text-foreground">{copy.tierLabels[tierKey]}</span>
                  {isNext && <span className="rounded-full bg-[#D8B866]/15 px-2 py-0.5 text-[10px] font-bold text-[#E8D39A]">{copy.nextBadge}</span>}
                </span>
                <span className="mt-0.5 block text-[11px] leading-relaxed text-[#A8B4D0]">{copy.tierRewards[tierKey]}</span>
                <span className="mt-0.5 block text-[10px] leading-relaxed text-[#6A7A9B]">{copy.tierRequirements[tierKey]}</span>
              </span>
            </div>
          )
        })}
      </div>
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
  const { t } = useLanguage()
  const copy = t.profile.referrals

  return (
    <div>
      <div className="mb-3 flex items-center gap-2">
        <Clipboard className="h-4 w-4 text-[#00FF87]" />
        <p className="text-sm font-semibold text-foreground">{copy.applyTitle}</p>
      </div>
      {appliedReferral ? (
        <div className="rounded-xl border border-[#1A2845] bg-[#070D1A] p-3">
          <p className="text-sm font-bold text-[#00FF87]">{copy.appliedCode.replace("{code}", appliedReferral.code)}</p>
        </div>
      ) : (
        <>
          <div className="flex gap-2">
            <input
              className="min-w-0 flex-1 rounded-xl border border-[#1A2845] bg-[#070D1A] px-3 py-2.5 text-sm font-semibold uppercase tracking-normal text-foreground outline-none focus:border-[#00FF87]/60"
              value={codeDraft}
              onChange={(event) => onCodeChange(event.target.value)}
              placeholder={copy.applyPlaceholder}
              maxLength={80}
            />
            <button
              className="shrink-0 rounded-xl bg-[#00FF87] px-4 py-2 text-sm font-bold text-[#070D1A] transition-colors hover:bg-[#00e87a] disabled:cursor-not-allowed disabled:opacity-60"
              type="button"
              onClick={onApply}
              disabled={isApplying}
            >
              {isApplying ? <RefreshCw className="h-4 w-4 animate-spin" /> : copy.applyButton}
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

function formatPassPrice(value: number, freeLabel: string) {
  return value <= 0 ? freeLabel : formatEuro(value)
}

function formatReferralRequirement(
  perks: ReferralDashboardResponse["user_referral"]["perks"] | undefined,
  copy: ReturnType<typeof useLanguage>["t"]["profile"]["referrals"],
) {
  if (!perks?.next_tier) return copy.allPerksUnlocked

  const remainingRegistered = perks.remaining_registered_referrals
  const remainingPaid = perks.remaining_paid_referrals
  if (remainingRegistered > 0) {
    const template = remainingRegistered === 1 ? copy.registeredNeeded : copy.registeredNeededPlural
    return template.replace("{count}", remainingRegistered.toString())
  }
  if (remainingPaid > 0) {
    const template = remainingPaid === 1 ? copy.paidNeeded : copy.paidNeededPlural
    return template.replace("{count}", remainingPaid.toString())
  }
  return copy.allPerksUnlocked
}

function formatReferralAction(
  perks: ReferralDashboardResponse["user_referral"]["perks"] | undefined,
  copy: ReturnType<typeof useLanguage>["t"]["profile"]["referrals"],
) {
  if (!perks?.next_tier) return copy.topTierAction

  const remainingRegistered = perks.remaining_registered_referrals
  const remainingPaid = perks.remaining_paid_referrals
  if (remainingRegistered > 0) {
    const template = remainingRegistered === 1 ? copy.nextActionRegistered : copy.nextActionRegisteredPlural
    return template.replace("{count}", remainingRegistered.toString())
  }
  if (remainingPaid > 0) {
    const template = remainingPaid === 1 ? copy.nextActionPaid : copy.nextActionPaidPlural
    return template.replace("{count}", remainingPaid.toString())
  }
  return copy.topTierAction
}

function translateReferralApiError(
  error: unknown,
  copy: ReturnType<typeof useLanguage>["t"]["profile"]["referrals"],
  fallback: string,
) {
  if (!(error instanceof Error)) return fallback

  const message = error.message
  if (message === "This code does not exist.") return copy.codeNotFound
  if (message === "You have already applied a code.") return copy.alreadyApplied
  if (message === "You cannot apply your own referral code.") return copy.selfReferral
  if (message === "This user already has a bar partner code.") return copy.alreadyHasPartner
  return message || fallback
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
