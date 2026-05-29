import type { ReferralDashboardResponse, UserReferralTierKey } from "@/lib/api"

export const STANDARD_WORLD_CUP_PASS_PRICE = 9.99
export const FOUNDER_WORLD_CUP_PASS_PRICE = 6.99
export const FOUNDER_PASS_SALE_ENDS_AT = "2026-06-10T21:59:59+02:00"

export type PassPriceOffer = {
  price: number
  standardPrice: number
  isDiscounted: boolean
  isFree: boolean
  source: "standard" | "founder" | "applied_referral" | "user_referral"
  appliedCode: string | null
  tierKey: UserReferralTierKey | null
}

export function getBestPassPriceOffer(dashboard: ReferralDashboardResponse | null): PassPriceOffer {
  const appliedReferral = dashboard?.applied_referral ?? null
  const appliedReferralPrice = appliedReferral
    ? Math.max(STANDARD_WORLD_CUP_PASS_PRICE - appliedReferral.discount_amount, 0)
    : null
  const userPerkPrice = dashboard?.user_referral?.has_code
    ? dashboard.user_referral.perks.unlocked_pass_price
    : null
  const candidates: Array<{ price: number; source: PassPriceOffer["source"] }> = [
    { price: STANDARD_WORLD_CUP_PASS_PRICE, source: "standard" },
  ]
  if (isFounderPassSaleActive()) {
    candidates.push({ price: FOUNDER_WORLD_CUP_PASS_PRICE, source: "founder" })
  }
  if (appliedReferralPrice !== null) {
    candidates.push({ price: appliedReferralPrice, source: "applied_referral" })
  }
  if (userPerkPrice !== null) {
    candidates.push({ price: userPerkPrice, source: "user_referral" })
  }
  const bestOffer = candidates.reduce((best, candidate) => (candidate.price < best.price ? candidate : best))

  return {
    price: bestOffer.price,
    standardPrice: STANDARD_WORLD_CUP_PASS_PRICE,
    isDiscounted: bestOffer.price < STANDARD_WORLD_CUP_PASS_PRICE,
    isFree: bestOffer.price <= 0,
    source: bestOffer.source,
    appliedCode: appliedReferral?.code ?? null,
    tierKey: dashboard?.user_referral?.perks.current_tier?.key ?? null,
  }
}

export function isFounderPassSaleActive(now: Date = new Date()) {
  return now.getTime() <= Date.parse(FOUNDER_PASS_SALE_ENDS_AT)
}
