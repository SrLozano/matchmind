"use client"

import { createContext, useContext, useEffect, useMemo, useState } from "react"
import type { ReactNode } from "react"
import { createClient, type Session, type SupabaseClient, type User } from "@supabase/supabase-js"
import { setAuthTokenProvider } from "@/lib/api"

type AuthContextValue = {
  isConfigured: boolean
  isLoading: boolean
  session: Session | null
  user: User | null
  authError: string | null
  signIn: (email: string, password: string) => Promise<void>
  signUp: (email: string, password: string) => Promise<{ needsConfirmation: boolean }>
  signInWithGoogle: () => Promise<void>
  requestPasswordReset: (email: string) => Promise<void>
  updatePassword: (password: string) => Promise<void>
  signOut: () => Promise<void>
}

const AuthContext = createContext<AuthContextValue | null>(null)
let supabaseClient: SupabaseClient | null | undefined

function getAppOrigin() {
  if (typeof window === "undefined") return ""

  const configuredUrl = process.env.NEXT_PUBLIC_APP_URL?.trim()
  if (!configuredUrl) return window.location.origin

  try {
    return new URL(configuredUrl).origin
  } catch {
    return window.location.origin
  }
}

function isStaleRefreshTokenError(error: unknown) {
  if (!(error instanceof Error)) return false
  const message = error.message.toLowerCase()
  return message.includes("invalid refresh token") || message.includes("refresh token not found")
}

async function clearStaleLocalSession(supabase: SupabaseClient) {
  const { error } = await supabase.auth.signOut({ scope: "local" })
  if (error && !isStaleRefreshTokenError(error)) {
    throw error
  }
}

async function readSession(supabase: SupabaseClient) {
  const { data, error } = await supabase.auth.getSession()
  if (error) throw error
  return data.session
}

function createSupabaseClient(): SupabaseClient | null {
  if (supabaseClient !== undefined) return supabaseClient

  const url = process.env.NEXT_PUBLIC_SUPABASE_URL
  const key = process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY

  supabaseClient = url && key ? createClient(url, key) : null
  return supabaseClient
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [supabase] = useState(() => createSupabaseClient())
  const [session, setSession] = useState<Session | null>(null)
  const [isLoading, setIsLoading] = useState(Boolean(supabase))
  const [authError, setAuthError] = useState<string | null>(null)

  useEffect(() => {
    if (!supabase) {
      setAuthTokenProvider(null)
      setIsLoading(false)
      return
    }

    setAuthTokenProvider(async () => {
      try {
        const nextSession = await readSession(supabase)
        return nextSession?.access_token ?? null
      } catch (error) {
        if (isStaleRefreshTokenError(error)) {
          await clearStaleLocalSession(supabase)
          return null
        }
        throw error
      }
    })

    let mounted = true
    readSession(supabase).then(async (nextSession) => {
      if (!mounted) return
      setSession(nextSession)
      setIsLoading(false)
    }).catch(async (error: unknown) => {
      if (!mounted) return
      if (isStaleRefreshTokenError(error)) {
        await clearStaleLocalSession(supabase)
        setAuthError(null)
      } else {
        setAuthError(error instanceof Error ? error.message : "Unable to check your session.")
      }
      setSession(null)
      setIsLoading(false)
    })

    const { data: listener } = supabase.auth.onAuthStateChange((_event, nextSession) => {
      setSession(nextSession)
    })

    return () => {
      mounted = false
      listener.subscription.unsubscribe()
    }
  }, [supabase])

  const value = useMemo<AuthContextValue>(
    () => ({
      isConfigured: Boolean(supabase),
      isLoading,
      session,
      user: session?.user ?? null,
      authError,
      async signIn(email, password) {
        if (!supabase) return
        setAuthError(null)
        const { error } = await supabase.auth.signInWithPassword({ email, password })
        if (error) {
          setAuthError(error.message)
          throw error
        }
      },
      async signUp(email, password) {
        if (!supabase) return { needsConfirmation: false }
        setAuthError(null)
        const { data, error } = await supabase.auth.signUp({
          email,
          password,
        })
        if (error) {
          setAuthError(error.message)
          throw error
        }
        return { needsConfirmation: !data.session }
      },
      async signInWithGoogle() {
        if (!supabase) return
        setAuthError(null)
        const redirectTo = `${getAppOrigin()}/auth/callback`
        const { error } = await supabase.auth.signInWithOAuth({
          provider: "google",
          options: {
            redirectTo,
          },
        })
        if (error) {
          setAuthError(error.message)
          throw error
        }
      },
      async requestPasswordReset(email) {
        if (!supabase) return
        setAuthError(null)
        const redirectTo = `${window.location.origin}/reset-password`
        const { error } = await supabase.auth.resetPasswordForEmail(email, { redirectTo })
        if (error) {
          setAuthError(error.message)
          throw error
        }
      },
      async updatePassword(password) {
        if (!supabase) return
        setAuthError(null)
        const { error } = await supabase.auth.updateUser({ password })
        if (error) {
          setAuthError(error.message)
          throw error
        }
      },
      async signOut() {
        if (!supabase) return
        setAuthError(null)
        await supabase.auth.signOut()
      },
    }),
    [authError, isLoading, session, supabase]
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error("useAuth must be used inside AuthProvider")
  }
  return context
}
