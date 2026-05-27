import type { Metadata } from "next"
import LegalPage from "../LegalPage"

export const metadata: Metadata = {
  title: "Privacy Policy",
  description: "How Matchmind handles account data, chat messages, bet tracker entries, and referral information.",
  alternates: { canonical: "/legal/privacy" },
}

export default function PrivacyPage() {
  return (
    <LegalPage
      eyebrow="Privacy"
      title="Privacy Policy"
      updatedAt="May 27, 2026"
      intro="Matchmind uses personal and product data to provide the app experience: authentication, coach chats, market reads, bet tracking, payments, and referrals."
      sections={[
        {
          title: "Data we use",
          body: [
            "Matchmind may process your email address, display name, avatar, authentication identifiers, chat messages, manually logged bets, preferences, payment status, and referral information.",
            "If you register as a pub partner, Matchmind may process the pub name, location, responsible contact name, phone or Bizum contact, referral code, estimated commission, and payout review status.",
          ],
        },
        {
          title: "Why we use it",
          body: [
            "We use this data to authenticate you, provide coach responses, store conversation history, maintain your bet tracker, enforce usage limits, unlock paid access, prevent referral abuse, and support account or billing issues.",
            "Chat messages and bet tracker entries can contain sensitive betting-related notes. Avoid entering information you do not want processed by Matchmind.",
          ],
        },
        {
          title: "Service providers",
          body: [
            "Matchmind relies on third-party services for hosting, authentication, database storage, payments, analytics, AI responses, odds, football data, and prediction-market data.",
            "Payment card details are handled by Stripe-hosted Checkout. Matchmind does not store full card numbers.",
          ],
        },
        {
          title: "Retention and deletion",
          body: [
            "Matchmind keeps account, chat, tracker, payment-status, and referral records for as long as needed to provide the product, resolve support issues, audit payments/referrals, and satisfy legal or operational obligations.",
          ],
        },
        {
          title: "No bet placement",
          body: [
            "Matchmind does not send your bets to bookmakers, place wagers, hold gambling balances, or process gambling payouts.",
            "If you choose to bet elsewhere, that relationship is between you and the third-party operator.",
          ],
        },
      ]}
    />
  )
}
