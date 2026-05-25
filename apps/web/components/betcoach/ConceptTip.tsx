"use client"

import { HelpCircle } from "lucide-react"
import type { ReactNode } from "react"

import {
  Drawer,
  DrawerContent,
  DrawerDescription,
  DrawerHeader,
  DrawerTitle,
  DrawerTrigger,
} from "@/components/ui/drawer"
import { useLanguage, translations } from "@/lib/i18n"

export type ConceptKey = keyof typeof translations.en.concepts

export function ConceptTip({
  concept,
  label,
  children,
  subtle = false,
}: {
  concept: ConceptKey
  label?: string
  children?: ReactNode
  subtle?: boolean
}) {
  const { t } = useLanguage()
  const copy = t.concepts[concept]
  const visibleLabel = label ?? copy.title

  return (
    <Drawer>
      <DrawerTrigger asChild>
        <button
          type="button"
          className={`inline-flex min-w-0 items-center gap-1 align-baseline ${
            subtle ? "text-inherit" : "text-[#A8B4D0] hover:text-foreground"
          }`}
          aria-label={copy.title}
          title={copy.title}
        >
          {children ?? <span className="truncate">{visibleLabel}</span>}
          <HelpCircle className="h-3 w-3 shrink-0 opacity-80" />
        </button>
      </DrawerTrigger>
      <DrawerContent className="mx-auto max-w-[430px] border-[#1A2845] bg-[#071021] text-foreground">
        <DrawerHeader className="text-left">
          <DrawerTitle className="text-base font-bold">{copy.title}</DrawerTitle>
          <DrawerDescription className="text-sm leading-relaxed text-[#A8B4D0]">
            {copy.body}
          </DrawerDescription>
        </DrawerHeader>
        <div className="px-4 pb-[calc(1rem+env(safe-area-inset-bottom))]">
          <p className="rounded-xl border border-[#1A2845] bg-[#0F1C35] px-3 py-3 text-xs leading-relaxed text-[#D7DEEF]">
            {copy.example}
          </p>
        </div>
      </DrawerContent>
    </Drawer>
  )
}
