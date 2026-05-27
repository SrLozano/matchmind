import Link from "next/link"
import { Sparkles } from "lucide-react"

type LegalSection = {
  title: string
  body: string[]
}

export type LegalPageProps = {
  eyebrow: string
  title: string
  intro: string
  updatedAt: string
  sections: LegalSection[]
  backLabel?: string
  footerLinks?: {
    terms: string
    privacy: string
    responsibleUse: string
  }
}

export default function LegalPage({
  eyebrow,
  title,
  intro,
  updatedAt,
  sections,
  backLabel = "Back",
  footerLinks = {
    terms: "Terms",
    privacy: "Privacy",
    responsibleUse: "Responsible use",
  },
}: LegalPageProps) {
  return (
    <main id="main-content" className="min-h-screen bg-[#040810] px-4 py-6 text-foreground sm:px-6 lg:px-8">
      <div className="mx-auto w-full max-w-3xl">
        <nav className="mb-8 flex items-center justify-between gap-4">
          <Link href="/" className="flex items-center gap-3">
            <span className="flex h-10 w-10 items-center justify-center rounded-xl border border-[#00FF87]/30 bg-[#00FF87]/15">
              <Sparkles className="h-5 w-5 text-[#00FF87]" />
            </span>
            <span className="text-lg font-black text-white">Matchmind</span>
          </Link>
          <Link href="/" className="text-sm font-bold text-[#8DFFC2] hover:text-[#00FF87]">
            {backLabel}
          </Link>
        </nav>

        <header className="border-b border-white/10 pb-6">
          <p className="text-xs font-black uppercase tracking-[0.2em] text-[#00FF87]">{eyebrow}</p>
          <h1 className="mt-3 text-4xl font-black leading-tight text-white sm:text-5xl">{title}</h1>
          <p className="mt-4 text-base leading-7 text-[#C9D4EC]">{intro}</p>
          <p className="mt-4 text-xs font-semibold uppercase tracking-[0.16em] text-[#6A7A9B]">
            Last updated: {updatedAt}
          </p>
        </header>

        <div className="space-y-7 py-8">
          {sections.map((section) => (
            <section key={section.title} className="rounded-2xl border border-white/10 bg-[#071222]/86 p-5">
              <h2 className="text-lg font-black text-white">{section.title}</h2>
              <div className="mt-3 space-y-3 text-sm leading-7 text-[#BFD0EA]">
                {section.body.map((paragraph) => (
                  <p key={paragraph}>{paragraph}</p>
                ))}
              </div>
            </section>
          ))}
        </div>

        <footer className="border-t border-white/10 py-6 text-sm text-[#8E9BBC]">
          <div className="flex flex-wrap gap-x-4 gap-y-2">
            <Link href="/legal/terms" className="hover:text-[#00FF87]">{footerLinks.terms}</Link>
            <Link href="/legal/privacy" className="hover:text-[#00FF87]">{footerLinks.privacy}</Link>
            <Link href="/legal/responsible-use" className="hover:text-[#00FF87]">{footerLinks.responsibleUse}</Link>
          </div>
        </footer>
      </div>
    </main>
  )
}
