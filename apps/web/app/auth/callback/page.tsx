"use client"

import { useEffect } from "react"
import { Loader2 } from "lucide-react"
import { AuthProvider, useAuth } from "@/lib/auth"
import { useLanguage, LanguageProvider } from "@/lib/i18n"

export default function AuthCallbackPage() {
  return (
    <LanguageProvider>
      <AuthProvider>
        <AuthCallbackContent />
      </AuthProvider>
    </LanguageProvider>
  )
}

function AuthCallbackContent() {
  const { language } = useLanguage()
  const { isLoading, session } = useAuth()
  const copy = language === "es" ? copyEs : copyEn

  useEffect(() => {
    if (session || !isLoading) {
      window.location.replace("/")
      return
    }

    const timeout = window.setTimeout(() => {
      window.location.replace("/")
    }, 3000)

    return () => window.clearTimeout(timeout)
  }, [isLoading, session])

  return (
    <main id="main-content" className="flex min-h-[100dvh] items-center justify-center bg-[#040810] px-4 text-[#A8B4D0]">
      <div className="flex items-center gap-2 text-sm font-semibold">
        <Loader2 className="h-4 w-4 animate-spin text-[#00FF87]" />
        {copy.finishing}
      </div>
    </main>
  )
}

const copyEn = {
  finishing: "Finishing sign in...",
}

const copyEs = {
  finishing: "Terminando inicio de sesión...",
}
