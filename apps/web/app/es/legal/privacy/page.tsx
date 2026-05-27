import type { Metadata } from "next"
import LegalPage from "../../../legal/LegalPage"

export const metadata: Metadata = {
  title: "Política de privacidad",
  description: "Cómo Matchmind trata datos de cuenta, chats, apuestas registradas y referidos.",
  alternates: { canonical: "/es/legal/privacy" },
}

export default function SpanishPrivacyPage() {
  return (
    <LegalPage
      eyebrow="Privacidad"
      title="Política de privacidad"
      updatedAt="27 de mayo de 2026"
      backLabel="Volver"
      footerLinks={{
        terms: "Términos",
        privacy: "Privacidad",
        responsibleUse: "Uso responsable",
      }}
      footerBasePath="/es/legal"
      intro="Matchmind utiliza datos personales y de producto para ofrecer la experiencia de la app: autenticación, chats con el coach, lecturas de mercado, registro manual de apuestas, pagos y referidos."
      sections={[
        {
          title: "Datos que usamos",
          body: [
            "Matchmind puede tratar tu email, nombre visible, avatar, identificadores de autenticación, mensajes del chat, apuestas registradas manualmente, preferencias, estado de pago e información de referidos.",
            "Si te registras como bar partner, Matchmind puede tratar el nombre del bar, ubicación, persona responsable, teléfono o Bizum de contacto, código de referido, comisión estimada y estado de revisión del pago.",
          ],
        },
        {
          title: "Base legal",
          body: [
            "Tratamos datos de cuenta, chat, tracker, acceso y estado de pago porque son necesarios para prestar Matchmind. También podemos tratar logs limitados y datos antifraude por seguridad y prevención de abuso.",
            "Los mensajes comerciales o el seguimiento no esencial solo se usarán cuando exista el consentimiento requerido.",
          ],
        },
        {
          title: "Para qué los usamos",
          body: [
            "Usamos estos datos para autenticarte, generar respuestas del coach, guardar historial de conversaciones, mantener tu tracker, aplicar límites de uso, desbloquear acceso de pago, prevenir abuso de referidos y resolver incidencias de cuenta o facturación.",
            "Los mensajes del chat y las apuestas registradas pueden contener notas sensibles relacionadas con apuestas. Evita introducir información que no quieras que Matchmind procese.",
          ],
        },
        {
          title: "Proveedores",
          body: [
            "Matchmind usa servicios de terceros para hosting, autenticación, base de datos, pagos, analítica, respuestas de IA, cuotas, datos futbolísticos y mercados de predicción, incluidos Supabase, OpenAI, Stripe y el proveedor de hosting.",
            "El contenido del chat enviado al proveedor de IA no debería incluir identificadores innecesarios como datos completos de pago. Matchmind no envía intencionadamente datos de tarjeta al proveedor de IA.",
            "Los datos completos de tarjeta se gestionan mediante Stripe Checkout. Matchmind no almacena números completos de tarjeta.",
          ],
        },
        {
          title: "Cookies y analítica",
          body: [
            "Matchmind utiliza actualmente Vercel Web Analytics en producción. Vercel describe este producto de analítica como sin cookies y basado en datos de tráfico anónimos y agregados.",
            "Si Matchmind añade más adelante cookies o seguimiento que no sean estrictamente necesarios, pediremos consentimiento cuando sea obligatorio.",
          ],
        },
        {
          title: "Conservación y eliminación",
          body: [
            "Matchmind conserva datos de cuenta, chats, tracker, estado de pago y referidos mientras sean necesarios para prestar el producto durante el Mundial, resolver soporte, auditar pagos o referidos y cumplir obligaciones legales u operativas.",
            "Después del torneo, Matchmind tiene previsto eliminar o archivar las bases de datos de producto que ya no sean necesarias, salvo registros limitados que deban conservarse por motivos legales, fiscales, de pagos, seguridad o disputas.",
            "Puedes solicitar acceso, corrección, eliminación o cierre de cuenta escribiendo a support@trymatchmind.com.",
          ],
        },
        {
          title: "No colocamos apuestas",
          body: [
            "Matchmind no envía tus apuestas a casas, no coloca apuestas, no custodia saldos de juego y no procesa ganancias de apuestas.",
            "Si decides apostar en otro lugar, esa relación será entre tú y el operador externo.",
          ],
        },
      ]}
    />
  )
}
