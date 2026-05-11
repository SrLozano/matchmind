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
  signUp: (email: string, password: string) => Promise<void>
  signOut: () => Promise<void>
}

const AuthContext = createContext<AuthContextValue | null>(null)

function createSupabaseClient(): SupabaseClient | null {
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL
  const key = process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY

  if (!url || !key) return null
  return createClient(url, key)
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
      const { data } = await supabase.auth.getSession()
      return data.session?.access_token ?? null
    })

    let mounted = true
    supabase.auth.getSession().then(({ data, error }) => {
      if (!mounted) return
      if (error) setAuthError(error.message)
      setSession(data.session)
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
        if (!supabase) return
        setAuthError(null)
        const { error } = await supabase.auth.signUp({ email, password })
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
