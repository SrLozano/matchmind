import type { Metadata } from "next"
import LegalPage from "../../../legal/LegalPage"

export const metadata: Metadata = {
  title: "Uso responsable",
  description: "Guía de uso responsable y recursos de juego seguro para usuarios de Matchmind.",
  alternates: { canonical: "/es/legal/responsible-use" },
}

export default function SpanishResponsibleUsePage() {
  return (
    <LegalPage
      eyebrow="Uso responsable"
      title="Uso responsable"
      updatedAt="27 de mayo de 2026"
      backLabel="Volver"
      footerLinks={{
        terms: "Términos",
        privacy: "Privacidad",
        responsibleUse: "Uso responsable",
      }}
      footerBasePath="/es/legal"
      intro="Matchmind está diseñado para frenar decisiones, no para empujar a apostar más. A veces, la mejor respuesta de Matchmind será: no entrar."
      sections={[
        {
          title: "Usa Matchmind para reducir daño",
          body: [
            "Define un presupuesto antes de mirar cuotas. No aumentes importes porque un partido sea emocional, nacional, urgente o porque estés intentando recuperar pérdidas.",
            "Trata cada veredicto como una estimación. Una confianza alta no es una garantía, y una apuesta con valor también puede perder.",
          ],
        },
        {
          title: "Cuándo no usar Matchmind",
          body: [
            "No uses Matchmind si eres menor de 18 años, si estás autoexcluido del juego, si apostar ha dejado de ser recreativo para ti o si las herramientas de análisis hacen que te cueste más parar.",
            "Si apostar te genera estrés, deuda, secretos, conflicto, persecución de pérdidas o pérdida de control, haz una pausa y busca apoyo profesional o local.",
          ],
        },
        {
          title: "Recurso en España",
          body: [
            "La DGOJ ofrece información de juego seguro y el Registro General de Interdicciones de Acceso al Juego (RGIAJ), un registro de autoprohibición de acceso al juego.",
            "Recurso: https://www.ordenacionjuego.es/participantes-juego/juego-seguro/rgiaj",
          ],
        },
        {
          title: "Límites del producto",
          body: [
            "Matchmind no coloca apuestas, no custodia fondos, no garantiza resultados y actualmente no enlaza a usuarios con operadores de apuestas.",
            "La app debe evitar lenguaje como apuesta segura, fijo, garantizado, sin riesgo o beneficio seguro.",
          ],
        },
      ]}
    />
  )
}
