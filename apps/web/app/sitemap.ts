import type { MetadataRoute } from "next"
import { publicRoutes } from "@/lib/seo/metadata"

export const dynamic = "force-static"

export default function sitemap(): MetadataRoute.Sitemap {
  return publicRoutes
}
