import type { Metadata } from "next"
import LegalPage from "../LegalPage"

export const metadata: Metadata = {
  title: "Terms and Disclaimer",
  description: "Matchmind terms, product limits, and analysis-only disclaimer.",
  alternates: { canonical: "/legal/terms" },
}

export default function TermsPage() {
  return (
    <LegalPage
      eyebrow="Terms"
      title="Terms and Disclaimer"
      updatedAt="May 27, 2026"
      intro="Matchmind is a World Cup analysis and coaching tool. It helps users think more clearly about betting decisions, but it is not a bookmaker, sportsbook, gambling operator, broker, or financial adviser."
      sections={[
        {
          title: "Analysis only",
          body: [
            "Matchmind does not accept, place, arrange, settle, or pay out bets. Users who choose to bet do so outside Matchmind with third-party operators.",
            "Coach responses, market signals, odds comparisons, confidence scores, and tracker metrics are informational decision-support outputs. They are not guarantees, instructions to bet, financial advice, or promises of profit.",
          ],
        },
        {
          title: "Eligibility",
          body: [
            "You must be at least 18 years old to create an account. Do not use Matchmind if betting is illegal for you, if you are self-excluded from gambling, or if using betting-analysis tools would undermine a personal limit or recovery plan.",
            "You are responsible for complying with the laws and rules that apply where you live and where you place any bet outside Matchmind.",
          ],
        },
        {
          title: "Data and odds",
          body: [
            "Bookmaker odds, football context, and prediction-market signals can be delayed, incomplete, unavailable, or wrong. Matchmind may continue answering with partial context when a data source fails.",
            "No single source is treated as truth. Bookmaker consensus, prediction-market probabilities, and AI analysis are estimates that can change quickly.",
          ],
        },
        {
          title: "Payments and access",
          body: [
            "The World Cup Pass unlocks analysis features inside Matchmind. It does not buy betting services, betting funds, tips with guaranteed returns, or access to a bookmaker.",
            "Referral rewards and pub partner commissions are promotional, estimated until reviewed, and may be rejected, paused, cancelled, or removed for abuse, fake referrals, duplicate accounts, self-referrals, payment disputes, refunds, or suspicious activity.",
          ],
        },
        {
          title: "No affiliate betting links",
          body: [
            "Matchmind does not currently provide bookmaker affiliate links, betslip deep links, bonuses, or incentives to place bets with a specific operator.",
            "If this ever changes, Matchmind should complete a separate legal and product review before launch.",
          ],
        },
      ]}
    />
  )
}
