"use client"

import { Activity, BarChart3, GraduationCap, HelpCircle, Loader2, MessageCircle, Sparkles, UserRound, X } from "lucide-react"
import { useEffect, useState } from "react"

import { updateCurrentUserName, type CurrentUser } from "@/lib/api"
import { useLanguage } from "@/lib/i18n"
import { usePreferences, type ExplanationLevel } from "@/lib/preferences"
import { displayUserName } from "@/lib/user-display"

const stepIcons = [MessageCircle, UserRound, Sparkles, BarChart3, Activity, HelpCircle, GraduationCap]

export const ONBOARDING_STORAGE_KEY = "matchmind-onboarding-complete"

export default function OnboardingTutorial({
  currentUser,
  onProfileUpdated,
  onComplete,
}: {
  currentUser: CurrentUser | null
  onProfileUpdated: () => void
  onComplete: () => void
}) {
  const { t } = useLanguage()
  const { explanationLevel, setExplanationLevel } = usePreferences()
  const [stepIndex, setStepIndex] = useState(0)
  const [nameDraft, setNameDraft] = useState("")
  const [isSavingName, setIsSavingName] = useState(false)
  const [nameError, setNameError] = useState<string | null>(null)
  const totalSteps = t.onboarding.steps.length + 2
  const isNameStep = stepIndex === 1
  const isExplanationStep = stepIndex === totalSteps - 1
  const tutorialStepIndex = stepIndex > 1 ? stepIndex - 1 : stepIndex
  const step = isNameStep || isExplanationStep ? null : t.onboarding.steps[tutorialStepIndex]
  const Icon = stepIcons[stepIndex] ?? Sparkles
  const isLastStep = stepIndex === totalSteps - 1
  const fallbackName = displayUserName({
    name: currentUser?.name,
    email: currentUser?.email,
    fallback: t.profile.matchmindUser,
  })

  useEffect(() => {
    setNameDraft(currentUser?.name ?? "")
  }, [currentUser?.name])

  const finish = () => {
    window.localStorage.setItem(ONBOARDING_STORAGE_KEY, "true")
    onComplete()
  }

  const chooseLevel = (level: ExplanationLevel) => {
    setExplanationLevel(level)
  }

  const saveNameIfNeeded = async () => {
    const nextName = nameDraft.trim()
    if (!nextName || nextName === currentUser?.name?.trim()) return true

    setIsSavingName(true)
    setNameError(null)
    try {
      await updateCurrentUserName(nextName)
      onProfileUpdated()
      return true
    } catch {
      setNameError(t.onboarding.nameSaveError)
      return false
    } finally {
      setIsSavingName(false)
    }
  }

  const goNext = async () => {
    if (isLastStep) {
      finish()
      return
    }
    if (isNameStep) {
      const saved = await saveNameIfNeeded()
      if (!saved) return
    }
    setStepIndex((index) => index + 1)
  }

  return (
    <div className="absolute inset-0 z-50 flex items-end bg-[#040810]/80 px-4 pb-[calc(1rem+env(safe-area-inset-bottom))] backdrop-blur-sm sm:items-center">
      <div className="w-full rounded-2xl border border-[#1A2845] bg-[#0B162B] p-4 shadow-[0_24px_80px_rgba(0,0,0,0.6)]">
        <div className="flex items-start justify-between gap-3">
          <div className="flex min-w-0 items-center gap-3">
            <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl border border-[#00FF87]/30 bg-[#00FF87]/12">
              <Icon className="h-5 w-5 text-[#00FF87]" />
            </div>
            <div className="min-w-0">
              <p className="text-[10px] font-bold uppercase tracking-widest text-[#00FF87]">
                {t.onboarding.step} {stepIndex + 1}/{totalSteps}
              </p>
              <h2 className="mt-1 text-lg font-black leading-tight text-foreground">
                {isNameStep ? t.onboarding.nameTitle : isExplanationStep ? t.onboarding.explanationChoiceTitle : step?.title}
              </h2>
            </div>
          </div>
          <button
            type="button"
            onClick={finish}
            className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg border border-[#1A2845] text-[#6A7A9B] transition-colors hover:text-foreground"
            aria-label={t.onboarding.skip}
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        <p className="mt-4 text-sm leading-relaxed text-[#A8B4D0]">
          {isNameStep ? t.onboarding.nameBody : isExplanationStep ? t.onboarding.explanationChoiceBody : step?.body}
        </p>

        {isNameStep && (
          <div className="mt-4">
            <input
              className="w-full rounded-xl border border-[#1A2845] bg-[#071021] px-3 py-3 text-base text-foreground outline-none placeholder:text-[#6A7A9B] focus:border-[#00FF87]/60 sm:text-sm"
              type="text"
              autoComplete="given-name"
              maxLength={80}
              value={nameDraft}
              onChange={(event) => {
                setNameDraft(event.target.value)
                setNameError(null)
              }}
              placeholder={fallbackName || t.onboarding.namePlaceholder}
            />
            {nameError ? (
              <p className="mt-2 text-xs font-semibold text-[#FF8AA1]">{nameError}</p>
            ) : (
              <p className="mt-2 text-xs leading-relaxed text-[#6A7A9B]">
                {nameDraft.trim() ? nameDraft.trim() : fallbackName}
              </p>
            )}
          </div>
        )}

        {isExplanationStep && (
          <div className="mt-4 grid grid-cols-1 gap-2">
            <ExplanationChoice
              isActive={explanationLevel === "beginner"}
              label={t.profile.beginner}
              description={t.onboarding.explanationChoices.beginner}
              onClick={() => chooseLevel("beginner")}
            />
            <ExplanationChoice
              isActive={explanationLevel === "standard"}
              label={t.profile.standard}
              description={t.onboarding.explanationChoices.standard}
              onClick={() => chooseLevel("standard")}
            />
            <ExplanationChoice
              isActive={explanationLevel === "advanced"}
              label={t.profile.advanced}
              description={t.onboarding.explanationChoices.advanced}
              onClick={() => chooseLevel("advanced")}
            />
          </div>
        )}

        <div className="mt-5 flex items-center gap-2">
          {Array.from({ length: totalSteps }, (_, index) => (
            <span
              key={index}
              className={`h-1.5 flex-1 rounded-full ${index <= stepIndex ? "bg-[#00FF87]" : "bg-[#1A2845]"}`}
            />
          ))}
        </div>

        <div className="mt-5 flex items-center gap-2">
          <button
            type="button"
            onClick={finish}
            className="flex-1 rounded-xl border border-[#1A2845] px-4 py-3 text-sm font-semibold text-[#A8B4D0] transition-colors hover:text-foreground"
          >
            {t.onboarding.skip}
          </button>
          <button
            type="button"
            onClick={() => void goNext()}
            disabled={isSavingName}
            className="flex-[1.4] rounded-xl bg-[#00FF87] px-4 py-3 text-sm font-bold text-[#04110A] transition-colors hover:bg-[#00e87a]"
          >
            {isSavingName && <Loader2 className="mr-2 inline h-4 w-4 animate-spin" />}
            {isLastStep ? t.onboarding.done : isNameStep && nameDraft.trim() ? t.onboarding.saveName : t.onboarding.next}
          </button>
        </div>
      </div>
    </div>
  )
}

function ExplanationChoice({
  isActive,
  label,
  description,
  onClick,
}: {
  isActive: boolean
  label: string
  description: string
  onClick: () => void
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`rounded-xl border px-3 py-3 text-left transition-colors ${
        isActive
          ? "border-[#00FF87]/50 bg-[#00FF87]/10"
          : "border-[#1A2845] bg-[#071021] hover:border-[#00FF87]/30"
      }`}
    >
      <span className={`block text-sm font-bold ${isActive ? "text-[#00FF87]" : "text-foreground"}`}>
        {label}
      </span>
      <span className="mt-1 block text-xs leading-relaxed text-[#6A7A9B]">{description}</span>
    </button>
  )
}
