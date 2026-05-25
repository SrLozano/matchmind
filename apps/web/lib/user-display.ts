export function nameFromEmail(email: string | null | undefined) {
  const localPart = email?.split("@")[0]?.trim()
  if (!localPart) return null

  const firstToken = localPart
    .replace(/[._-]+/g, " ")
    .split(" ")
    .find(Boolean)

  if (!firstToken) return null
  return firstToken.charAt(0).toUpperCase() + firstToken.slice(1).toLowerCase()
}

export function displayUserName({
  name,
  email,
  fallback,
}: {
  name: string | null | undefined
  email: string | null | undefined
  fallback: string
}) {
  return name?.trim() || nameFromEmail(email) || fallback
}
