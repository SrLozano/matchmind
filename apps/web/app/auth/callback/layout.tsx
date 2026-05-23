import type { Metadata } from "next"

export const metadata: Metadata = {
  title: "Sign In Callback",
  description: "Completing your Matchmind sign in.",
  alternates: {
    canonical: "/auth/callback",
  },
  robots: {
    index: false,
    follow: false,
    nocache: true,
  },
}

export default function AuthCallbackLayout({ children }: { children: React.ReactNode }) {
  return children
}
