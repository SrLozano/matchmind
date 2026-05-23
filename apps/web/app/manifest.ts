import type { MetadataRoute } from "next"
import { siteConfig } from "@/lib/seo/metadata"

export const dynamic = "force-static"

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: `${siteConfig.name} - World Cup 2026 Betting Coach`,
    short_name: siteConfig.shortName,
    description: siteConfig.description,
    start_url: "/",
    scope: "/",
    display: "standalone",
    orientation: "portrait",
    background_color: siteConfig.backgroundColor,
    theme_color: siteConfig.backgroundColor,
    categories: ["sports", "finance", "productivity"],
    lang: "en",
    dir: "ltr",
    icons: [
      {
        src: "/icon-192.png",
        sizes: "192x192",
        type: "image/png",
        purpose: "any",
      },
      {
        src: "/maskable-icon-192.png",
        sizes: "192x192",
        type: "image/png",
        purpose: "maskable",
      },
      {
        src: "/icon-512.png",
        sizes: "512x512",
        type: "image/png",
        purpose: "any",
      },
      {
        src: "/maskable-icon-512.png",
        sizes: "512x512",
        type: "image/png",
        purpose: "maskable",
      },
    ],
    screenshots: [
      {
        src: "/pwa-screenshot-mobile.png",
        sizes: "390x844",
        type: "image/png",
        form_factor: "narrow",
        label: "Matchmind mobile betting coach chat",
      },
      {
        src: "/pwa-screenshot-wide.png",
        sizes: "1440x900",
        type: "image/png",
        form_factor: "wide",
        label: "Matchmind World Cup 2026 market signals",
      },
    ],
  }
}
