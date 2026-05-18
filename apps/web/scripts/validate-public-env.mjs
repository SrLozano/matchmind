import { existsSync, readFileSync } from "node:fs"
import { dirname, join } from "node:path"
import { fileURLToPath } from "node:url"

const appDir = dirname(dirname(fileURLToPath(import.meta.url)))

loadEnvFile(join(appDir, ".env.local"))

const requiredPublicEnv = [
  "NEXT_PUBLIC_API_URL",
  "NEXT_PUBLIC_APP_URL",
  "NEXT_PUBLIC_SUPABASE_URL",
  "NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY",
]

const missing = requiredPublicEnv.filter((key) => !isUsableValue(process.env[key]))

if (missing.length > 0) {
  console.error("")
  console.error("Missing required public frontend environment variables:")
  for (const key of missing) {
    console.error(`- ${key}`)
  }
  console.error("")
  console.error("Set these in Cloudflare Pages before deploying Matchmind Web.")
  console.error("They are compiled into the static Next.js bundle at build time.")
  console.error("")
  process.exit(1)
}

function loadEnvFile(filePath) {
  if (!existsSync(filePath)) return

  const file = readFileSync(filePath, "utf8")
  for (const line of file.split(/\r?\n/)) {
    const trimmedLine = line.trim()
    if (!trimmedLine || trimmedLine.startsWith("#")) continue

    const separatorIndex = trimmedLine.indexOf("=")
    if (separatorIndex === -1) continue

    const key = trimmedLine.slice(0, separatorIndex).trim()
    const value = trimmedLine.slice(separatorIndex + 1).trim()
    if (!key || process.env[key]) continue

    process.env[key] = stripQuotes(value)
  }
}

function stripQuotes(value) {
  if (
    (value.startsWith('"') && value.endsWith('"')) ||
    (value.startsWith("'") && value.endsWith("'"))
  ) {
    return value.slice(1, -1)
  }

  return value
}

function isUsableValue(value) {
  const normalizedValue = value?.trim()
  if (!normalizedValue) return false

  return !["your-project", "project-web", "your-render-api-url"].some((placeholder) =>
    normalizedValue.includes(placeholder)
  )
}
