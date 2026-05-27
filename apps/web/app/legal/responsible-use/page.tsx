import type { Metadata } from "next"
import LegalPage from "../LegalPage"

export const metadata: Metadata = {
  title: "Responsible Use",
  description: "Responsible betting-analysis guidance and safer gambling resources for Matchmind users.",
  alternates: { canonical: "/legal/responsible-use" },
}

export default function ResponsibleUsePage() {
  return (
    <LegalPage
      eyebrow="Responsible use"
      title="Responsible Use"
      updatedAt="May 27, 2026"
      intro="Matchmind is designed to slow decisions down, not to push users toward more betting. The healthiest Matchmind answer is often: skip it."
      sections={[
        {
          title: "Use Matchmind to reduce harm",
          body: [
            "Set a budget before looking at odds. Do not increase stakes because a match feels emotional, national, urgent, or because you are trying to recover losses.",
            "Treat every coach verdict as an estimate. A high confidence score is not a guarantee, and a value bet can still lose.",
          ],
        },
        {
          title: "When not to use Matchmind",
          body: [
            "Do not use Matchmind if you are under 18, if you are self-excluded from gambling, if betting is no longer recreational for you, or if analysis tools make it harder to stop.",
            "If betting creates stress, debt, secrecy, conflict, chasing losses, or loss of control, take a break and seek professional or local support.",
          ],
        },
        {
          title: "Spain resource",
          body: [
            "Spain's DGOJ provides safer gambling information and the Registro General de Interdicciones de Acceso al Juego (RGIAJ), a self-exclusion register for gambling access.",
            "Resource: https://www.ordenacionjuego.es/participantes-juego/juego-seguro/rgiaj",
          ],
        },
        {
          title: "Product boundaries",
          body: [
            "Matchmind does not place bets, does not hold user funds, does not guarantee results, and does not currently link users to betting operators.",
            "The app should avoid language such as lock, safe bet, guaranteed, sure thing, or risk-free.",
          ],
        },
      ]}
    />
  )
}
