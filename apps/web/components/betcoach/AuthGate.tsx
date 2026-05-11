"use client"

import { useState, type ReactNode } from "react"
import { Loader2, LockKeyhole, Mail } from "lucide-react"
import { useAuth } from "@/lib/auth"
import { useLanguage } from "@/lib/i18n"

export default function AuthGate({ children }: { children: ReactNode }) {
  const { isConfigured, isLoading, session, authError, signIn, signUp, requestPasswordReset } = useAuth()
  const { language } = useLanguage()
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [mode, setMode] = useState<"signin" | "signup" | "forgot">("signin")
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [localError, setLocalError] = useState<string | null>(null)
  const [successMessage, setSuccessMessage] = useState<string | null>(null)
  const copy = language === "es" ? copyEs : copyEn

  if (!isConfigured) return <>{children}</>

  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[#040810] text-[#A8B4D0]">
        <Loader2 className="mr-2 h-4 w-4 animate-spin text-[#00FF87]" />
        {copy.loading}
      </div>
    )
  }

  if (session) return <>{children}</>

  const submit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setIsSubmitting(true)
    setLocalError(null)
    setSuccessMessage(null)
    try {
      if (mode === "forgot") {
        await requestPasswordReset(email)
        setSuccessMessage(copy.resetSent)
      } else if (mode === "signin") {
        await signIn(email, password)
      } else {
        await signUp(email, password)
      }
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

        <form onSubmit={submit} className="space-y-3">
          <label className="block">
            <span className="mb-1.5 block text-xs font-semibold text-[#A8B4D0]">{copy.email}</span>
            <span className="flex items-center gap-2 rounded-xl border border-[#1A2845] bg-[#0F1C35] px-3 py-3">
              <Mail className="h-4 w-4 text-[#6A7A9B]" />
              <input
                className="min-w-0 flex-1 bg-transparent text-sm text-foreground outline-none placeholder:text-[#6A7A9B]"
                type="email"
                autoComplete="email"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                placeholder="you@example.com"
                required
              />
            </span>
          </label>

          {mode !== "forgot" && (
            <label className="block">
              <span className="mb-1.5 block text-xs font-semibold text-[#A8B4D0]">{copy.password}</span>
              <input
                className="w-full rounded-xl border border-[#1A2845] bg-[#0F1C35] px-3 py-3 text-sm text-foreground outline-none placeholder:text-[#6A7A9B]"
                type="password"
                autoComplete={mode === "signin" ? "current-password" : "new-password"}
                minLength={6}
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                placeholder="••••••••"
                required
              />
            </label>
          )}

          {(localError || authError) && (
            <div className="rounded-xl border border-[#FF5A7A]/30 bg-[#FF5A7A]/10 px-3 py-2 text-xs text-[#FF9AAF]">
              {localError ?? authError}
            </div>
          )}
          {successMessage && (
            <div className="rounded-xl border border-[#00FF87]/30 bg-[#00FF87]/10 px-3 py-2 text-xs text-[#8DFFC2]">
              {successMessage}
            </div>
          )}

          <button
            className="flex w-full items-center justify-center rounded-xl bg-[#00FF87] py-3 text-sm font-bold text-[#070D1A] transition-colors hover:bg-[#00e87a] disabled:cursor-not-allowed disabled:opacity-70"
            type="submit"
            disabled={isSubmitting}
          >
            {isSubmitting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            {mode === "forgot" ? copy.sendReset : mode === "signin" ? copy.signIn : copy.signUp}
          </button>
        </form>

        {mode === "signin" && (
          <button
            className="mt-3 w-full text-center text-xs font-semibold text-[#A8B4D0] transition-colors hover:text-[#00FF87]"
            type="button"
            onClick={() => {
              setMode("forgot")
              setLocalError(null)
              setSuccessMessage(null)
            }}
          >
            {copy.forgotPassword}
          </button>
        )}

        <button
          className="mt-4 w-full text-center text-xs font-semibold text-[#00FF87]"
          type="button"
          onClick={() => {
            setMode(mode === "signin" ? "signup" : "signin")
            setLocalError(null)
            setSuccessMessage(null)
          }}
        >
          {mode === "signin" ? copy.switchToSignUp : copy.switchToSignIn}
        </button>
      </div>
    </div>
  )
}

const copyEn = {
  loading: "Checking session...",
  title: "Welcome to Matchmind",
  subtitle: "Sign in to keep your chats, bets, and plan tied to you.",
  email: "Email",
  password: "Password",
  signIn: "Sign in",
  signUp: "Create account",
  sendReset: "Send reset email",
  forgotPassword: "Forgot your password?",
  resetSent: "If that email exists, Supabase will send a password reset link.",
  switchToSignUp: "New here? Create an account",
  switchToSignIn: "Already have an account? Sign in",
  genericError: "Authentication failed.",
}

const copyEs = {
  loading: "Comprobando sesión...",
  title: "Bienvenido a Matchmind",
  subtitle: "Inicia sesión para guardar tus chats, apuestas y plan.",
  email: "Email",
  password: "Contraseña",
  signIn: "Entrar",
  signUp: "Crear cuenta",
  sendReset: "Enviar email de recuperación",
  forgotPassword: "¿Has olvidado la contraseña?",
  resetSent: "Si ese email existe, Supabase enviará un enlace para cambiar la contraseña.",
  switchToSignUp: "¿Nuevo aquí? Crea una cuenta",
  switchToSignIn: "¿Ya tienes cuenta? Entra",
  genericError: "No se pudo autenticar.",
}
