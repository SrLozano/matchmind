import type { Metadata } from "next"
import LegalPage from "../../../legal/LegalPage"

export const metadata: Metadata = {
  title: "Términos y aviso legal",
  description: "Términos de Matchmind, límites del producto y aviso de solo análisis.",
  alternates: { canonical: "/es/legal/terms" },
}

export default function SpanishTermsPage() {
  return (
    <LegalPage
      eyebrow="Términos"
      title="Términos y aviso legal"
      updatedAt="27 de mayo de 2026"
      backLabel="Volver"
      footerLinks={{
        terms: "Términos",
        privacy: "Privacidad",
        responsibleUse: "Uso responsable",
      }}
      intro="Matchmind es una herramienta de análisis y acompañamiento para el Mundial. Ayuda a pensar mejor antes de apostar, pero no es una casa de apuestas, operador de juego, intermediario, asesor financiero ni gestor de fondos."
      sections={[
        {
          title: "Solo análisis",
          body: [
            "Matchmind no acepta, coloca, organiza, liquida ni paga apuestas. Si un usuario decide apostar, lo hace fuera de Matchmind con operadores de terceros.",
            "Las respuestas del coach, señales de mercado, comparaciones de cuotas, puntuaciones de confianza y métricas del tracker son información de apoyo a la decisión. No son garantías, instrucciones para apostar, asesoramiento financiero ni promesas de beneficio.",
          ],
        },
        {
          title: "Requisitos de uso",
          body: [
            "Debes tener al menos 18 años para crear una cuenta. No uses Matchmind si apostar es ilegal para ti, si estás autoexcluido del juego o si usar herramientas de análisis de apuestas perjudica tus límites personales o tu proceso de recuperación.",
            "Eres responsable de cumplir las leyes y normas aplicables en el lugar donde resides y en el lugar donde, en su caso, realices cualquier apuesta fuera de Matchmind.",
          ],
        },
        {
          title: "Datos y cuotas",
          body: [
            "Las cuotas de casas de apuestas, el contexto futbolístico y las señales de mercados de predicción pueden estar retrasados, incompletos, no disponibles o ser incorrectos. Matchmind puede seguir respondiendo con contexto parcial cuando falle una fuente de datos.",
            "Ninguna fuente se trata como verdad absoluta. El consenso de casas, las probabilidades de mercados de predicción y el análisis de IA son estimaciones que pueden cambiar rápidamente.",
          ],
        },
        {
          title: "Pagos y acceso",
          body: [
            "El Pase Mundial desbloquea funciones de análisis dentro de Matchmind. No compra servicios de apuestas, fondos para apostar, tips con retorno garantizado ni acceso a una casa de apuestas.",
            "Las recompensas por referidos y comisiones de bares partner son promocionales, estimadas hasta su revisión, y pueden rechazarse, pausarse, cancelarse o eliminarse por abuso, referidos falsos, cuentas duplicadas, autoreferidos, disputas de pago, reembolsos o actividad sospechosa.",
          ],
        },
        {
          title: "Sin enlaces de afiliación a apuestas",
          body: [
            "Matchmind no ofrece actualmente enlaces de afiliación a casas de apuestas, enlaces a boletos, bonos ni incentivos para apostar con un operador concreto.",
            "Si esto cambiara en el futuro, Matchmind debería completar una revisión legal y de producto separada antes de lanzarlo.",
          ],
        },
      ]}
    />
  )
}
