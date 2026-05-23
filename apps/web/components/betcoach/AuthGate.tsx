"use client"

import { useState, type FormEvent, type ReactNode } from "react"
import {
  ArrowRight,
  AlertTriangle,
  CheckCircle2,
  LineChart,
  Loader2,
  Mail,
  MessageSquareText,
  Sparkles,
  Trophy,
} from "lucide-react"
import { useAuth } from "@/lib/auth"
import { useLanguage, type Language } from "@/lib/i18n"

type SignalRow = {
  label: string
  value: string
  width: string
}

type StatTile = {
  label: string
  value: string
}

type LandingCopy = {
  loading: string
  navCta: string
  kicker: string
  heroTitle: string
  heroSubtitle: string
  primaryCta: string
  priceHook: string
  proofPoints: string[]
  previewTitle: string
  previewLive: string
  previewQuestion: string
  previewVerdict: string
  previewAnswer: string
  signalsTitle: string
  signalsSubtitle: string
  signalRows: SignalRow[]
  statTiles: StatTile[]
  authEyebrow: string
  signInTitle: string
  signInSubtitle: string
  signUpTitle: string
  signUpSubtitle: string
  forgotTitle: string
  forgotSubtitle: string
  email: string
  password: string
  signIn: string
  signUp: string
  continueWithGoogle: string
  continueWithGoogleSignUp: string
  or: string
  modeSignUp: string
  modeSignIn: string
  sendReset: string
  forgotPassword: string
  resetSent: string
  confirmEmail: string
  accountExistsSwitch: string
  switchToSignUp: string
  switchToSignIn: string
  genericError: string
  languageLabel: string
  authUnavailableTitle: string
  authUnavailableCopy: string
}

export default function AuthGate({ children }: { children: ReactNode }) {
  const { isConfigured, isLoading, session, authError, signIn, signUp, signInWithGoogle, requestPasswordReset } = useAuth()
  const { language, setLanguage } = useLanguage()
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [mode, setMode] = useState<"signin" | "signup" | "forgot">("signup")
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [localError, setLocalError] = useState<string | null>(null)
  const [successMessage, setSuccessMessage] = useState<string | null>(null)
  const copy = language === "es" ? copyEs : copyEn

  if (!isConfigured) return <AuthUnavailable copy={copy} language={language} onLanguageChange={setLanguage} />

  if (session) return <>{children}</>

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (isLoading) return
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
      const message = error instanceof Error ? error.message.toLowerCase() : ""
      const accountAlreadyExists = mode === "signup" && (message.includes("already registered") || message.includes("already exists"))
      if (accountAlreadyExists) {
        setMode("signin")
        setSuccessMessage(copy.accountExistsSwitch)
      } else {
        setLocalError(error instanceof Error ? error.message : copy.genericError)
      }
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
  const authTitle = mode === "signup" ? copy.signUpTitle : mode === "forgot" ? copy.forgotTitle : copy.signInTitle
  const authSubtitle = mode === "signup" ? copy.signUpSubtitle : mode === "forgot" ? copy.forgotSubtitle : copy.signInSubtitle

  return (
    <div className="min-h-[100dvh] overflow-hidden bg-[#040810] text-foreground">
      <div className="relative min-h-[100dvh]">
        <div
          className="absolute inset-0 bg-[url('https://images.unsplash.com/photo-1577223625816-7546f13df25d?auto=format&fit=crop&w=2200&q=80')] bg-cover bg-center opacity-30"
          aria-hidden="true"
        />
        <div className="absolute inset-0 bg-[linear-gradient(90deg,rgba(4,8,16,0.98)_0%,rgba(4,8,16,0.88)_42%,rgba(4,8,16,0.52)_100%)]" />
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_72%_18%,rgba(0,255,135,0.2),transparent_32%),linear-gradient(180deg,transparent_0%,#040810_100%)]" />

        <main id="main-content" className="relative mx-auto grid min-h-[100dvh] w-full max-w-7xl grid-cols-1 gap-8 px-4 py-[calc(1.25rem+env(safe-area-inset-top))] sm:px-6 lg:grid-cols-[minmax(0,1fr)_420px] lg:items-center lg:gap-12 lg:px-8">
          <section className="flex min-h-0 flex-col justify-center pb-2 pt-2 lg:pb-10">
            <nav className="mb-8 flex items-center justify-between gap-4 lg:mb-14">
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-xl border border-[#00FF87]/30 bg-[#00FF87]/15 shadow-[0_0_26px_rgba(0,255,135,0.18)]">
                  <Sparkles className="h-5 w-5 text-[#00FF87]" />
                </div>
                <span className="text-lg font-black tracking-tight">Matchmind</span>
              </div>
              <LanguageSwitcher
                language={language}
                languageLabel={copy.languageLabel}
                onLanguageChange={setLanguage}
              />
            </nav>

            <div className="max-w-3xl">
              <div className="mb-4 inline-flex items-center gap-2 rounded-full border border-[#00FF87]/30 bg-[#00FF87]/12 px-3 py-1.5 text-xs font-black uppercase tracking-[0.18em] text-[#8DFFC2]">
                <Trophy className="h-3.5 w-3.5" />
                {copy.kicker}
              </div>
              <h1 className="text-balance text-5xl font-black leading-[0.95] tracking-normal text-white sm:text-6xl lg:text-7xl">
                {copy.heroTitle}
              </h1>
              <p className="mt-5 max-w-2xl text-pretty text-lg leading-8 text-[#C9D4EC] sm:text-xl">
                {copy.heroSubtitle}
              </p>
            </div>

            <div className="mt-7 flex flex-col gap-3 sm:flex-row">
              <a
                href="#matchmind-auth"
                className="inline-flex min-h-12 items-center justify-center gap-2 rounded-xl bg-[#00FF87] px-5 py-3 text-sm font-black text-[#06101D] shadow-[0_0_28px_rgba(0,255,135,0.24)] transition-transform hover:scale-[1.01] active:scale-[0.99]"
              >
                {copy.primaryCta}
                <ArrowRight className="h-4 w-4" />
              </a>
              <div className="inline-flex min-h-12 items-center justify-center rounded-xl border border-white/15 bg-white/8 px-5 py-3 text-sm font-bold text-[#DCE6FA] backdrop-blur">
                {copy.priceHook}
              </div>
            </div>

            <div className="mt-8 grid max-w-3xl grid-cols-1 gap-3 sm:grid-cols-3">
              {copy.proofPoints.map((point) => (
                <div key={point} className="flex items-start gap-2 rounded-xl border border-white/10 bg-[#071222]/72 px-3 py-3 backdrop-blur">
                  <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-[#00FF87]" />
                  <span className="text-sm font-semibold leading-5 text-[#D7E1F5]">{point}</span>
                </div>
              ))}
            </div>

            <div className="mt-8 grid max-w-4xl grid-cols-1 gap-4 lg:grid-cols-[1.05fr_0.95fr]">
              <ProductPreview copy={copy} />
              <SignalPreview copy={copy} />
            </div>
          </section>

          <aside id="matchmind-auth" className="scroll-mt-6 pb-[env(safe-area-inset-bottom)]">
            <div className="rounded-2xl border border-white/12 bg-[#070D1A]/92 p-5 shadow-[0_24px_100px_rgba(0,0,0,0.58)] backdrop-blur-xl">
              <div className="mb-5">
                <p className="text-xs font-black uppercase tracking-[0.2em] text-[#00FF87]">{copy.authEyebrow}</p>
                <h2 className="mt-2 text-2xl font-black text-white">{authTitle}</h2>
                <p className="mt-1 text-sm leading-6 text-[#A8B4D0]">{authSubtitle}</p>
                {isLoading && (
                  <p className="mt-3 inline-flex items-center gap-2 rounded-full border border-[#00FF87]/20 bg-[#00FF87]/10 px-3 py-1.5 text-xs font-semibold text-[#8DFFC2]">
                    <Loader2 className="h-3.5 w-3.5 animate-spin" />
                    {copy.loading}
                  </p>
                )}
              </div>

              {mode !== "forgot" && (
                <div className="mb-4 grid grid-cols-2 rounded-xl border border-[#1A2845] bg-[#0A1426] p-1">
                  <button
                    type="button"
                    onClick={() => {
                      setMode("signup")
                      setLocalError(null)
                      setSuccessMessage(null)
                    }}
                    className={`min-h-10 rounded-lg px-3 text-sm font-black transition-colors ${
                      mode === "signup"
                        ? "bg-[#00FF87] text-[#06101D]"
                        : "text-[#A8B4D0] hover:bg-white/8 hover:text-white"
                    }`}
                    aria-pressed={mode === "signup"}
                  >
                    {copy.modeSignUp}
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      setMode("signin")
                      setLocalError(null)
                      setSuccessMessage(null)
                    }}
                    className={`min-h-10 rounded-lg px-3 text-sm font-black transition-colors ${
                      mode === "signin"
                        ? "bg-[#00FF87] text-[#06101D]"
                        : "text-[#A8B4D0] hover:bg-white/8 hover:text-white"
                    }`}
                    aria-pressed={mode === "signin"}
                  >
                    {copy.modeSignIn}
                  </button>
                </div>
              )}

              {mode !== "forgot" && (
                <>
                  <button
                    className="mb-4 flex w-full items-center justify-center gap-2 rounded-xl border border-[#1A2845] bg-[#F8FAFC] px-3 py-3 text-sm font-bold text-[#111827] transition-colors hover:bg-white disabled:cursor-not-allowed disabled:opacity-70"
                    type="button"
                    onClick={() => void handleGoogleSignIn()}
                    disabled={isSubmitting || isLoading}
                  >
                    <GoogleMark />
                    {mode === "signup" ? copy.continueWithGoogleSignUp : copy.continueWithGoogle}
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
                      className="min-w-0 flex-1 bg-transparent text-base text-foreground outline-none placeholder:text-[#6A7A9B] sm:text-sm"
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
                      className="w-full rounded-xl border border-[#1A2845] bg-[#0F1C35] px-3 py-3 text-base text-foreground outline-none placeholder:text-[#6A7A9B] sm:text-sm"
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
                  disabled={isSubmitting || isLoading}
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
            </div>
          </aside>
        </main>
      </div>
    </div>
  )
}

function AuthUnavailable({
  copy,
  language,
  onLanguageChange,
}: {
  copy: LandingCopy
  language: Language
  onLanguageChange: (language: Language) => void
}) {
  return (
    <div className="flex min-h-[100dvh] items-center justify-center bg-[#040810] px-4 py-8 text-foreground">
      <div className="w-full max-w-[430px] rounded-2xl border border-[#FFB020]/30 bg-[#070D1A] p-5 shadow-[0_24px_100px_rgba(0,0,0,0.58)]">
        <div className="mb-6 flex items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl border border-[#00FF87]/30 bg-[#00FF87]/15">
              <Sparkles className="h-5 w-5 text-[#00FF87]" />
            </div>
            <span className="text-lg font-black tracking-tight text-white">Matchmind</span>
          </div>
          <LanguageSwitcher
            language={language}
            languageLabel={copy.languageLabel}
            onLanguageChange={onLanguageChange}
          />
        </div>

        <div className="flex items-start gap-3 rounded-xl border border-[#FFB020]/30 bg-[#FFB020]/10 p-4">
          <AlertTriangle className="mt-0.5 h-5 w-5 shrink-0 text-[#FFB020]" />
          <div>
            <h1 className="text-lg font-black text-white">{copy.authUnavailableTitle}</h1>
            <p className="mt-2 text-sm leading-6 text-[#D7E1F5]">{copy.authUnavailableCopy}</p>
          </div>
        </div>
      </div>
    </div>
  )
}

function ProductPreview({ copy }: { copy: LandingCopy }) {
  return (
    <div className="overflow-hidden rounded-2xl border border-white/12 bg-[#071222]/84 shadow-[0_22px_80px_rgba(0,0,0,0.38)] backdrop-blur">
      <div className="flex items-center justify-between border-b border-white/10 px-4 py-3">
        <div className="flex items-center gap-2">
          <MessageSquareText className="h-4 w-4 text-[#00FF87]" />
          <span className="text-sm font-black text-white">{copy.previewTitle}</span>
        </div>
        <span className="rounded-full bg-[#00FF87]/14 px-2.5 py-1 text-[10px] font-black uppercase tracking-wider text-[#8DFFC2]">
          {copy.previewLive}
        </span>
      </div>
      <div className="space-y-4 p-4">
        <div className="max-w-[85%] rounded-2xl rounded-tl-md bg-[#13223E] px-3 py-3 text-sm leading-6 text-[#DCE6FA]">
          {copy.previewQuestion}
        </div>
        <div className="ml-auto rounded-2xl rounded-tr-md border border-[#00FF87]/25 bg-[#00FF87]/10 p-3">
          <div className="flex items-center justify-between gap-4">
            <p className="text-sm font-black text-white">{copy.previewVerdict}</p>
            <span className="rounded-lg bg-[#00FF87] px-2 py-1 text-xs font-black text-[#06101D]">7/10</span>
          </div>
          <p className="mt-2 text-sm leading-6 text-[#BFD0EA]">{copy.previewAnswer}</p>
        </div>
      </div>
    </div>
  )
}

function SignalPreview({ copy }: { copy: LandingCopy }) {
  return (
    <div className="rounded-2xl border border-white/12 bg-[#071222]/84 p-4 shadow-[0_22px_80px_rgba(0,0,0,0.34)] backdrop-blur">
      <div className="mb-4 flex items-center justify-between">
        <div>
          <p className="text-sm font-black text-white">{copy.signalsTitle}</p>
          <p className="text-xs text-[#7F8FAF]">{copy.signalsSubtitle}</p>
        </div>
        <LineChart className="h-5 w-5 text-[#00FF87]" />
      </div>
      <div className="space-y-3">
        {copy.signalRows.map((row, index) => (
          <div key={row.label} className="rounded-xl border border-white/10 bg-[#0A1629] p-3">
            <div className="flex items-center justify-between gap-3 text-sm">
              <span className="font-bold text-[#DCE6FA]">{row.label}</span>
              <span className={index === 0 ? "font-black text-[#00FF87]" : "font-black text-[#FFD600]"}>{row.value}</span>
            </div>
            <div className="mt-2 h-2 overflow-hidden rounded-full bg-[#172640]">
              <div className="h-full rounded-full bg-[#00FF87]" style={{ width: row.width }} />
            </div>
          </div>
        ))}
      </div>
      <div className="mt-4 grid grid-cols-3 gap-2">
        {copy.statTiles.map((tile) => (
          <div key={tile.label} className="rounded-xl bg-white/8 px-3 py-2">
            <p className="text-base font-black text-white">{tile.value}</p>
            <p className="text-[10px] font-semibold uppercase tracking-wider text-[#7F8FAF]">{tile.label}</p>
          </div>
        ))}
      </div>
    </div>
  )
}

function LanguageSwitcher({
  language,
  languageLabel,
  onLanguageChange,
}: {
  language: Language
  languageLabel: string
  onLanguageChange: (language: Language) => void
}) {
  return (
    <div
      className="flex items-center gap-1 rounded-full border border-white/15 bg-white/8 p-1 text-xs font-black text-[#A8B4D0] backdrop-blur"
      aria-label={languageLabel}
    >
      {(["en", "es"] as const).map((option) => (
        <button
          key={option}
          type="button"
          onClick={() => onLanguageChange(option)}
          className={`h-8 rounded-full px-3 transition-colors ${
            language === option
              ? "bg-[#00FF87] text-[#06101D]"
              : "text-[#DCE6FA] hover:bg-white/10 hover:text-white"
          }`}
          aria-pressed={language === option}
        >
          {option.toUpperCase()}
        </button>
      ))}
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

const copyEn: LandingCopy = {
  loading: "Checking session...",
  navCta: "Get started",
  kicker: "World Cup 2026 betting coach",
  heroTitle: "Know when a World Cup bet is actually worth it.",
  heroSubtitle:
    "Matchmind combines match context, bookmaker odds, and prediction-market signals into one direct coach verdict before you stake a cent.",
  primaryCta: "Start free",
  priceHook: "Full tournament pass: €9.99 once",
  proofPoints: ["Pause impulsive bets", "Spot overpriced odds", "Track every decision"],
  previewTitle: "Coach verdict",
  previewLive: "AI read",
  previewQuestion: "Argentina to win the World Cup at 7.50. Good value or trap?",
  previewVerdict: "Lean yes, but keep stake controlled",
  previewAnswer:
    "The price is interesting if crowd probability stays above the implied 13.3%, but this is a long tournament. Small position, no chasing.",
  signalsTitle: "Market Signals",
  signalsSubtitle: "Tournament-level probability shifts",
  signalRows: [
    { label: "Brazil winner market", value: "18%", width: "78%" },
    { label: "Spain group winner", value: "64%", width: "64%" },
  ],
  statTiles: [
    { value: "Ask", label: "Before betting" },
    { value: "Value", label: "Odds check" },
    { value: "Track", label: "Your record" },
  ],
  authEyebrow: "Create your account",
  signInTitle: "Welcome back",
  signInSubtitle: "Open your coach chats, market reads, and betting record.",
  signUpTitle: "Create your free account",
  signUpSubtitle: "Get your second opinion before kickoff. No sportsbook, no bet placement.",
  forgotTitle: "Reset your password",
  forgotSubtitle: "Enter your email and we will send you a reset link.",
  email: "Email",
  password: "Password",
  signIn: "Sign in",
  signUp: "Create account",
  continueWithGoogle: "Continue with Google",
  continueWithGoogleSignUp: "Create account with Google",
  or: "or",
  modeSignUp: "Create account",
  modeSignIn: "Sign in",
  sendReset: "Send reset email",
  forgotPassword: "Forgot your password?",
  resetSent: "If that email exists, Supabase will send a password reset link.",
  confirmEmail: "Account created. Check your email to confirm it, then sign in.",
  accountExistsSwitch: "That email already has an account. I switched you to sign in.",
  switchToSignUp: "New here? Create an account",
  switchToSignIn: "Already have an account? Sign in",
  genericError: "Authentication failed.",
  languageLabel: "Select language",
  authUnavailableTitle: "Sign-in is temporarily unavailable",
  authUnavailableCopy:
    "Matchmind could not load its authentication settings, so the protected app is locked instead of opening a broken session. Please try again in a moment.",
}

const copyEs: LandingCopy = {
  loading: "Comprobando sesión...",
  navCta: "Empezar",
  kicker: "Mundial 2026 · análisis antes de apostar",
  heroTitle: "Antes de apostar, pregunta a Matchmind.",
  heroSubtitle:
    "Tu segunda opinión para cortar el ruido, el hype y las cuotas malas antes de poner dinero en juego.",
  primaryCta: "Crear cuenta gratis",
  priceHook: "Pase Mundial: 9,99 € para todo el torneo",
  proofPoints: ["Frena apuestas por impulso", "Detecta cuotas caras", "Guarda cada decisión"],
  previewTitle: "Veredicto Matchmind",
  previewLive: "Análisis IA",
  previewQuestion: "España gana el grupo a 1.65. Todo el mundo lo ve claro. ¿Entramos?",
  previewVerdict: "Yo no la cogería a esa cuota",
  previewAnswer:
    "Parece segura, pero el precio ya descuenta demasiado optimismo. Si quieres ir con España, esperaría una cuota mejor o bajaría mucho el importe.",
  signalsTitle: "Señales del mercado",
  signalsSubtitle: "Lo que el dinero está viendo antes que el ruido",
  signalRows: [
    { label: "Favorito sobrecomprado", value: "Alerta", width: "78%" },
    { label: "Valor en clasificación", value: "Fuerte", width: "64%" },
  ],
  statTiles: [
    { value: "Pregunta", label: "Antes de apostar" },
    { value: "Valor", label: "Lectura de cuota" },
    { value: "Control", label: "Historial propio" },
  ],
  authEyebrow: "Crea tu cuenta",
  signInTitle: "Vuelve a Matchmind",
  signInSubtitle: "Abre tus chats, lecturas de mercado e historial de apuestas.",
  signUpTitle: "Crea tu cuenta gratis",
  signUpSubtitle: "Ten una segunda opinión antes del saque inicial. Sin casa de apuestas, sin colocar apuestas.",
  forgotTitle: "Recupera tu contraseña",
  forgotSubtitle: "Escribe tu email y te enviaremos un enlace de recuperación.",
  email: "Email",
  password: "Contraseña",
  signIn: "Entrar",
  signUp: "Crear cuenta gratis",
  continueWithGoogle: "Continuar con Google",
  continueWithGoogleSignUp: "Crear cuenta con Google",
  or: "o",
  modeSignUp: "Crear cuenta",
  modeSignIn: "Iniciar sesión",
  sendReset: "Enviar email de recuperación",
  forgotPassword: "¿Has olvidado la contraseña?",
  resetSent: "Si ese email existe, Supabase enviará un enlace para cambiar la contraseña.",
  confirmEmail: "Cuenta creada. Confirma tu email y luego inicia sesión.",
  accountExistsSwitch: "Ese email ya tiene cuenta. Te he pasado a iniciar sesión.",
  switchToSignUp: "¿Nuevo aquí? Crea una cuenta",
  switchToSignIn: "¿Ya tienes cuenta? Inicia sesión",
  genericError: "No se pudo autenticar.",
  languageLabel: "Seleccionar idioma",
  authUnavailableTitle: "El acceso no está disponible ahora",
  authUnavailableCopy:
    "Matchmind no pudo cargar la configuración de autenticación, así que la app protegida queda bloqueada en vez de abrir una sesión rota. Inténtalo de nuevo en un momento.",
}
