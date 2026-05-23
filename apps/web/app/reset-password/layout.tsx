import type { Metadata } from "next"

export const metadata: Metadata = {
  title: "Reset Password",
  description: "Update your Matchmind account password.",
  alternates: {
    canonical: "/reset-password",
  },
  robots: {
    index: false,
    follow: false,
    nocache: true,
  },
}

export default function ResetPasswordLayout({ children }: { children: React.ReactNode }) {
  return children
}
