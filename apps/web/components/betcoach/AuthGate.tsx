"use client"

import { useState, type ReactNode } from "react"
import { Loader2, LockKeyhole, Mail } from "lucide-react"
import { useAuth } from "@/lib/auth"
import { useLanguage } from "@/lib/i18n"

export default function AuthGate({ children }: { children: ReactNode }) {
  const { isConfigured, isLoading, session, authError, signIn, signUp, signInWithGoogle, requestPasswordReset } = useAuth()
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
        const result = await signUp(email, password)
        if (result.needsConfirmation) {
          setSuccessMessage(copy.confirmEmail)
          setPassword("")
          setMode("signin")
        }
      }
    } catch (error) {
      setLocalError(error instanceof Error ? error.message : copy.genericError)
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleGoogleSignIn = async () => {
    setIsSubmitting(true)
    setLocalError(null)
    setSuccessMessage(null)
    try {
      await signInWithGoogle()
    } catch (error) {
      setLocalError(error instanceof Error ? error.message : copy.genericError)
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

        {mode !== "forgot" && (
          <>
            <button
              className="mb-4 flex w-full items-center justify-center gap-2 rounded-xl border border-[#1A2845] bg-[#F8FAFC] px-3 py-3 text-sm font-bold text-[#111827] transition-colors hover:bg-white disabled:cursor-not-allowed disabled:opacity-70"
              type="button"
              onClick={() => void handleGoogleSignIn()}
              disabled={isSubmitting}
            >
              <GoogleMark />
              {copy.continueWithGoogle}
            </button>

            <div className="mb-4 grid grid-cols-[1fr_auto_1fr] items-center gap-3 text-[10px] font-semibold uppercase tracking-wider text-[#6A7A9B]">
              <div className="h-px bg-[#1A2845]" />
              <span>{copy.or}</span>
              <div className="h-px bg-[#1A2845]" />
            </div>
          </>
        )}

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

function GoogleMark() {
  return (
    <svg className="h-4 w-4" viewBox="0 0 24 24" aria-hidden="true">
      <path
        fill="#4285F4"
        d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
      />
      <path
        fill="#34A853"
        d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
      />
      <path
        fill="#FBBC05"
        d="M5.84 14.1c-.22-.66-.35-1.36-.35-2.1s.13-1.44.35-2.1V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l3.66-2.84z"
      />
      <path
        fill="#EA4335"
        d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06L5.84 9.9C6.71 7.31 9.14 5.38 12 5.38z"
      />
    </svg>
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
  continueWithGoogle: "Continue with Google",
  or: "or",
  sendReset: "Send reset email",
  forgotPassword: "Forgot your password?",
  resetSent: "If that email exists, Supabase will send a password reset link.",
  confirmEmail: "Account created. Check your email to confirm it, then sign in.",
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
  continueWithGoogle: "Continuar con Google",
  or: "o",
  sendReset: "Enviar email de recuperación",
  forgotPassword: "¿Has olvidado la contraseña?",
  resetSent: "Si ese email existe, Supabase enviará un enlace para cambiar la contraseña.",
  confirmEmail: "Cuenta creada. Confirma tu email y luego inicia sesión.",
  switchToSignUp: "¿Nuevo aquí? Crea una cuenta",
  switchToSignIn: "¿Ya tienes cuenta? Entra",
  genericError: "No se pudo autenticar.",
}
