"use client"

import { createContext, useContext, useEffect, useMemo, useState } from "react"
import type { ReactNode } from "react"

export type ExplanationLevel = "beginner" | "standard" | "advanced"

const EXPLANATION_LEVEL_STORAGE_KEY = "matchmind-explanation-level"
const DEFAULT_EXPLANATION_LEVEL: ExplanationLevel = "standard"

type PreferencesContextValue = {
  explanationLevel: ExplanationLevel
  setExplanationLevel: (level: ExplanationLevel) => void
  isBeginner: boolean
  isAdvanced: boolean
}

const PreferencesContext = createContext<PreferencesContextValue | null>(null)

function isExplanationLevel(value: string | null): value is ExplanationLevel {
  return value === "beginner" || value === "standard" || value === "advanced"
}

export function PreferencesProvider({ children }: { children: ReactNode }) {
  const [explanationLevel, setExplanationLevelState] = useState<ExplanationLevel>(DEFAULT_EXPLANATION_LEVEL)

  useEffect(() => {
    const storedLevel = window.localStorage.getItem(EXPLANATION_LEVEL_STORAGE_KEY)
    if (isExplanationLevel(storedLevel)) {
      setExplanationLevelState(storedLevel)
    }
  }, [])

  const setExplanationLevel = (nextLevel: ExplanationLevel) => {
    setExplanationLevelState(nextLevel)
    window.localStorage.setItem(EXPLANATION_LEVEL_STORAGE_KEY, nextLevel)
  }

  const value = useMemo(
    () => ({
      explanationLevel,
      setExplanationLevel,
      isBeginner: explanationLevel === "beginner",
      isAdvanced: explanationLevel === "advanced",
    }),
    [explanationLevel],
  )

  return <PreferencesContext.Provider value={value}>{children}</PreferencesContext.Provider>
}

export function usePreferences() {
  const context = useContext(PreferencesContext)
  if (!context) {
    throw new Error("usePreferences must be used within PreferencesProvider")
  }
  return context
}
