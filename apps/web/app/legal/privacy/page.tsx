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
          title: "Legal basis",
          body: [
            "We process account, chat, tracker, access, and payment-status data because it is needed to provide Matchmind. We may process limited logs and anti-abuse data for security and fraud prevention.",
            "Marketing messages or non-essential tracking will only be used where we have the required consent.",
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
            "Matchmind relies on third-party services for hosting, authentication, database storage, payments, analytics, AI responses, odds, football data, and prediction-market data, including Supabase, OpenAI, Stripe, and the hosting provider.",
            "Chat content sent to the AI provider should not include unnecessary identifiers such as your full payment details. Matchmind does not intentionally send card details to the AI provider.",
            "Payment card details are handled by Stripe-hosted Checkout. Matchmind does not store full card numbers.",
          ],
        },
        {
          title: "Cookies and analytics",
          body: [
            "Matchmind currently uses Vercel Web Analytics in production. Vercel describes this analytics product as cookie-free and based on anonymized, aggregated traffic data.",
            "If Matchmind later adds cookies or tracking that are not strictly necessary, we will ask for consent where required.",
          ],
        },
        {
          title: "Retention and deletion",
          body: [
            "Matchmind keeps account, chat, tracker, payment-status, and referral records for as long as needed to provide the product during the World Cup, resolve support issues, audit payments/referrals, and satisfy legal or operational obligations.",
            "After the tournament, Matchmind intends to delete or archive product databases that are no longer needed, except where limited records must be kept for legal, payment, tax, security, or dispute reasons.",
            "You can request access, correction, deletion, or account closure by emailing support@trymatchmind.com.",
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
