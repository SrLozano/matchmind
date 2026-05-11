"use client"

import { useState } from "react"
import { Check, Loader2, LockKeyhole } from "lucide-react"
import { AuthProvider, useAuth } from "@/lib/auth"
import { LanguageProvider, useLanguage } from "@/lib/i18n"

export default function ResetPasswordPage() {
  return (
    <LanguageProvider>
      <AuthProvider>
        <ResetPasswordForm />
      </AuthProvider>
    </LanguageProvider>
  )
}

function ResetPasswordForm() {
  const { language } = useLanguage()
  const { isConfigured, isLoading, session, authError, updatePassword } = useAuth()
  const [password, setPassword] = useState("")
  const [confirmPassword, setConfirmPassword] = useState("")
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [message, setMessage] = useState<string | null>(null)
  const [localError, setLocalError] = useState<string | null>(null)
  const copy = language === "es" ? copyEs : copyEn

  const submit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setLocalError(null)
    setMessage(null)
    if (password !== confirmPassword) {
      setLocalError(copy.passwordMismatch)
      return
    }

    setIsSubmitting(true)
    try {
      await updatePassword(password)
      setMessage(copy.success)
      setPassword("")
      setConfirmPassword("")
    } catch (error) {
      setLocalError(error instanceof Error ? error.message : copy.genericError)
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-[#040810] px-5">
      <div className="w-full max-w-[430px] rounded-2xl border border-[#1A2845] bg-[#070D1A] p-5 shadow-[0_0_60px_rgba(0,255,135,0.08)]">
        <div className="mb-5 flex items-center gap-3">
          <div className="flex h-11 w-11 items-center justify-center rounded-xl border border-[#00FF87]/25 bg-[#00FF87]/10">
            <LockKeyhole className="h-5 w-5 text-[#00FF87]" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-foreground">{copy.title}</h1>
            <p className="text-xs text-[#6A7A9B]">{copy.subtitle}</p>
          </div>
        </div>

        {!isConfigured ? (
          <Notice>{copy.notConfigured}</Notice>
        ) : isLoading ? (
          <Notice>
            <Loader2 className="mr-2 inline h-4 w-4 animate-spin text-[#00FF87]" />
            {copy.loading}
          </Notice>
        ) : !session ? (
          <Notice>{copy.noSession}</Notice>
        ) : (
          <form onSubmit={submit} className="space-y-3">
            <label className="block">
              <span className="mb-1.5 block text-xs font-semibold text-[#A8B4D0]">{copy.newPassword}</span>
              <input
                className="w-full rounded-xl border border-[#1A2845] bg-[#0F1C35] px-3 py-3 text-sm text-foreground outline-none placeholder:text-[#6A7A9B]"
                type="password"
                autoComplete="new-password"
                minLength={6}
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                placeholder="••••••••"
                required
              />
            </label>
            <label className="block">
              <span className="mb-1.5 block text-xs font-semibold text-[#A8B4D0]">{copy.confirmPassword}</span>
              <input
                className="w-full rounded-xl border border-[#1A2845] bg-[#0F1C35] px-3 py-3 text-sm text-foreground outline-none placeholder:text-[#6A7A9B]"
                type="password"
                autoComplete="new-password"
                minLength={6}
                value={confirmPassword}
                onChange={(event) => setConfirmPassword(event.target.value)}
                placeholder="••••••••"
                required
              />
            </label>

            {(localError || authError) && (
              <div className="rounded-xl border border-[#FF5A7A]/30 bg-[#FF5A7A]/10 px-3 py-2 text-xs text-[#FF9AAF]">
                {localError ?? authError}
              </div>
            )}
            {message && (
              <div className="flex items-center gap-2 rounded-xl border border-[#00FF87]/30 bg-[#00FF87]/10 px-3 py-2 text-xs text-[#8DFFC2]">
                <Check className="h-4 w-4" />
                {message}
              </div>
            )}

            <button
              className="flex w-full items-center justify-center rounded-xl bg-[#00FF87] py-3 text-sm font-bold text-[#070D1A] transition-colors hover:bg-[#00e87a] disabled:cursor-not-allowed disabled:opacity-70"
              type="submit"
              disabled={isSubmitting}
            >
              {isSubmitting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              {copy.submit}
            </button>
          </form>
        )}
      </div>
    </div>
  )
}

function Notice({ children }: { children: React.ReactNode }) {
  return <div className="rounded-xl border border-[#1A2845] bg-[#0F1C35] px-3 py-3 text-sm text-[#A8B4D0]">{children}</div>
}

const copyEn = {
  title: "Reset password",
  subtitle: "Choose a new password for your Matchmind account.",
  loading: "Checking reset session...",
  notConfigured: "Supabase auth is not configured for this environment.",
  noSession: "This reset link is missing or expired. Request a new password reset from the login screen.",
  newPassword: "New password",
  confirmPassword: "Confirm password",
  passwordMismatch: "Passwords do not match.",
  submit: "Update password",
  success: "Password updated. You can return to Matchmind.",
  genericError: "Unable to update password.",
}

const copyEs = {
  title: "Cambiar contraseña",
  subtitle: "Elige una nueva contraseña para tu cuenta de Matchmind.",
  loading: "Comprobando sesión de recuperación...",
  notConfigured: "Supabase auth no está configurado en este entorno.",
  noSession: "Este enlace no existe o ha caducado. Pide otro cambio de contraseña desde la pantalla de acceso.",
  newPassword: "Nueva contraseña",
  confirmPassword: "Confirmar contraseña",
  passwordMismatch: "Las contraseñas no coinciden.",
  submit: "Actualizar contraseña",
  success: "Contraseña actualizada. Ya puedes volver a Matchmind.",
  genericError: "No se pudo actualizar la contraseña.",
}
