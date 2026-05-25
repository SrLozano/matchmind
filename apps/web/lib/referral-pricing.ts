import type { ReferralDashboardResponse, UserReferralTierKey } from "@/lib/api"

export const STANDARD_WORLD_CUP_PASS_PRICE = 9.99

export type PassPriceOffer = {
  price: number
  standardPrice: number
  isDiscounted: boolean
  isFree: boolean
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
  const candidatePrices = [appliedReferralPrice, userPerkPrice].filter((price): price is number => typeof price === "number")
  const price = candidatePrices.length ? Math.min(...candidatePrices) : STANDARD_WORLD_CUP_PASS_PRICE

  return {
    price,
    standardPrice: STANDARD_WORLD_CUP_PASS_PRICE,
    isDiscounted: price < STANDARD_WORLD_CUP_PASS_PRICE,
    isFree: price <= 0,
    appliedCode: appliedReferral?.code ?? null,
    tierKey: dashboard?.user_referral?.perks.current_tier?.key ?? null,
  }
}
