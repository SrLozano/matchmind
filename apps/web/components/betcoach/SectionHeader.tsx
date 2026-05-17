"use client"

import type { ReactNode } from "react"
import type { LucideIcon } from "lucide-react"

export default function SectionHeader({
  icon: Icon,
  title,
  subtitle,
  action,
}: {
  icon: LucideIcon
  title: string
  subtitle?: string
  action?: ReactNode
}) {
  return (
    <div className="flex-shrink-0 px-4 pb-4 pt-[calc(1rem+env(safe-area-inset-top))] sm:px-5">
      <div className="flex items-start justify-between gap-3">
        <div className="flex min-w-0 items-start gap-3">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl border border-[#00FF87]/25 bg-[#00FF87]/10 text-[#00FF87]">
            <Icon className="h-5 w-5" />
          </div>
          <div className="min-w-0">
            <h1 className="text-2xl font-bold tracking-normal text-foreground">{title}</h1>
            {subtitle && <p className="mt-0.5 text-xs leading-relaxed text-[#6A7A9B]">{subtitle}</p>}
          </div>
        </div>
        {action && <div className="shrink-0">{action}</div>}
      </div>
    </div>
  )
}
