import { existsSync, readdirSync } from "node:fs"
import { mkdir, writeFile } from "node:fs/promises"
import { createRequire } from "node:module"
import { join, resolve } from "node:path"

const require = createRequire(import.meta.url)
const sharp = loadSharp()

const publicDir = join(process.cwd(), "public")
const green = "#00FF87"
const navy = "#070D1A"
const midnight = "#040810"
const surface = "#0D1629"
const text = "#F0F4FF"
const muted = "#A8B4D0"

await mkdir(publicDir, { recursive: true })

const iconSvg = iconSvgMarkup(512)
await writeFile(join(publicDir, "icon.svg"), iconSvg)
await writeFile(join(publicDir, "safari-pinned-tab.svg"), safariPinnedTabSvg())

const iconPng512 = await sharp(Buffer.from(iconSvg)).png().toBuffer()
await writePng("icon-16.png", iconSvg, 16)
await writePng("icon-32.png", iconSvg, 32)
await writePng("icon-192.png", iconSvg, 192)
await writePng("icon-512.png", iconSvg, 512)
await writePng("apple-touch-icon.png", iconSvg, 180)
await writePng("mstile-150.png", iconSvg, 150)
await writePng("icon-light-32x32.png", iconSvg, 32)
await writePng("icon-dark-32x32.png", iconSvg, 32)

await writePng("maskable-icon-192.png", maskableIconSvgMarkup(512), 192)
await writePng("maskable-icon-512.png", maskableIconSvgMarkup(512), 512)
await writeFile(join(publicDir, "favicon.ico"), icoFromPng(await sharp(iconPng512).resize(32, 32).png().toBuffer()))

await writeSocialPng("og-image.png", 1200, 630)
await writeSocialPng("twitter-image.png", 1200, 675)
await writePwaScreenshot("pwa-screenshot-mobile.png", 390, 844)
await writePwaScreenshot("pwa-screenshot-wide.png", 1440, 900)

async function writePng(filename, svg, size) {
  await sharp(Buffer.from(svg)).resize(size, size).png().toFile(join(publicDir, filename))
}

async function writeSocialPng(filename, width, height) {
  const svg = `
    <svg width="${width}" height="${height}" viewBox="0 0 ${width} ${height}" fill="none" xmlns="http://www.w3.org/2000/svg">
      <defs>
        <radialGradient id="glow" cx="0" cy="0" r="1" gradientUnits="userSpaceOnUse" gradientTransform="translate(${width * 0.74} ${height * 0.22}) rotate(118) scale(${width * 0.54} ${height * 0.72})">
          <stop stop-color="${green}" stop-opacity="0.32"/>
          <stop offset="1" stop-color="${green}" stop-opacity="0"/>
        </radialGradient>
        <linearGradient id="panel" x1="0" y1="0" x2="1" y2="1">
          <stop stop-color="#0F1C35"/>
          <stop offset="1" stop-color="#08101F"/>
        </linearGradient>
      </defs>
      <rect width="${width}" height="${height}" fill="${midnight}"/>
      <rect width="${width}" height="${height}" fill="url(#glow)"/>
      <path d="M0 ${height * 0.82} C ${width * 0.22} ${height * 0.70}, ${width * 0.46} ${height * 0.96}, ${width} ${height * 0.73}" stroke="${green}" stroke-opacity="0.17" stroke-width="3"/>
      <g transform="translate(76 72)">
        ${iconInnerSvg(94)}
        <text x="118" y="44" fill="${text}" font-family="Inter, Arial, sans-serif" font-size="46" font-weight="900">Matchmind</text>
        <text x="120" y="78" fill="${green}" font-family="Inter, Arial, sans-serif" font-size="18" font-weight="800" letter-spacing="3">WORLD CUP 2026</text>
      </g>
      <text x="78" y="${height * 0.49}" fill="${text}" font-family="Inter, Arial, sans-serif" font-size="66" font-weight="950">Your AI second opinion</text>
      <text x="80" y="${height * 0.60}" fill="${text}" font-family="Inter, Arial, sans-serif" font-size="66" font-weight="950">before you bet.</text>
      <text x="82" y="${height * 0.70}" fill="${muted}" font-family="Inter, Arial, sans-serif" font-size="26" font-weight="600">Odds context, market signals, honest World Cup analysis.</text>
      <g transform="translate(${width - 432} ${height - 184})">
        <rect width="344" height="138" rx="24" fill="url(#panel)" stroke="#1A2845" stroke-width="2"/>
        <text x="28" y="42" fill="${muted}" font-family="Inter, Arial, sans-serif" font-size="18" font-weight="800">CONFIDENCE</text>
        <text x="28" y="100" fill="${green}" font-family="Inter, Arial, sans-serif" font-size="58" font-weight="950">8.1/10</text>
        <path d="M204 92 L230 68 L254 82 L302 38" stroke="${green}" stroke-width="8" stroke-linecap="round" stroke-linejoin="round"/>
      </g>
    </svg>
  `

  await sharp(Buffer.from(svg)).png().toFile(join(publicDir, filename))
}

async function writePwaScreenshot(filename, width, height) {
  const isWide = width > height
  const appWidth = isWide ? 430 : width
  const x = isWide ? Math.round((width - appWidth) / 2) : 0
  const svg = `
    <svg width="${width}" height="${height}" viewBox="0 0 ${width} ${height}" fill="none" xmlns="http://www.w3.org/2000/svg">
      <rect width="${width}" height="${height}" fill="${midnight}"/>
      <rect x="${x}" y="0" width="${appWidth}" height="${height}" rx="${isWide ? 36 : 0}" fill="${navy}" stroke="#1A2845"/>
      <g transform="translate(${x + 24} 42)">
        ${iconInnerSvg(44)}
        <text x="60" y="29" fill="${text}" font-family="Inter, Arial, sans-serif" font-size="25" font-weight="900">Matchmind AI</text>
      </g>
      <rect x="${x + 20}" y="118" width="${appWidth - 40}" height="138" rx="18" fill="${surface}" stroke="#1A2845"/>
      <text x="${x + 42}" y="158" fill="${muted}" font-family="Inter, Arial, sans-serif" font-size="14" font-weight="800">BET CHECK</text>
      <text x="${x + 42}" y="198" fill="${text}" font-family="Inter, Arial, sans-serif" font-size="24" font-weight="900">Argentina to win Group J?</text>
      <text x="${x + 42}" y="228" fill="${green}" font-family="Inter, Arial, sans-serif" font-size="18" font-weight="800">Good price only above 1.80</text>
      <rect x="${x + 20}" y="280" width="${appWidth - 40}" height="240" rx="18" fill="#0F1C35" stroke="#1A2845"/>
      <text x="${x + 42}" y="322" fill="${text}" font-family="Inter, Arial, sans-serif" font-size="22" font-weight="900">Market Signals</text>
      <rect x="${x + 42}" y="356" width="${appWidth - 84}" height="18" rx="9" fill="#13233F"/>
      <rect x="${x + 42}" y="356" width="${Math.round((appWidth - 84) * 0.74)}" height="18" rx="9" fill="${green}"/>
      <rect x="${x + 42}" y="400" width="${appWidth - 84}" height="18" rx="9" fill="#13233F"/>
      <rect x="${x + 42}" y="400" width="${Math.round((appWidth - 84) * 0.58)}" height="18" rx="9" fill="#FFD600"/>
      <rect x="${x + 42}" y="444" width="${appWidth - 84}" height="18" rx="9" fill="#13233F"/>
      <rect x="${x + 42}" y="444" width="${Math.round((appWidth - 84) * 0.39)}" height="18" rx="9" fill="#FF4D4D"/>
      <rect x="${x + 20}" y="${height - 86}" width="${appWidth - 40}" height="62" rx="20" fill="#080E1E" stroke="#1A2845"/>
      <circle cx="${x + appWidth / 2}" cy="${height - 55}" r="24" fill="#0A1325" stroke="${green}"/>
      <circle cx="${x + appWidth / 2}" cy="${height - 55}" r="7" fill="${green}"/>
    </svg>
  `

  await sharp(Buffer.from(svg)).png().toFile(join(publicDir, filename))
}

function iconSvgMarkup(size) {
  return `
    <svg width="${size}" height="${size}" viewBox="0 0 512 512" fill="none" xmlns="http://www.w3.org/2000/svg">
      <rect width="512" height="512" rx="112" fill="${navy}"/>
      <rect x="32" y="32" width="448" height="448" rx="92" fill="#0B162B" stroke="#1A2845" stroke-width="10"/>
      ${iconInnerSvg(330, 91, 91)}
    </svg>
  `
}

function maskableIconSvgMarkup(size) {
  return `
    <svg width="${size}" height="${size}" viewBox="0 0 512 512" fill="none" xmlns="http://www.w3.org/2000/svg">
      <rect width="512" height="512" fill="${navy}"/>
      <circle cx="256" cy="256" r="210" fill="#0B162B" stroke="#1A2845" stroke-width="12"/>
      ${iconInnerSvg(250, 131, 131)}
    </svg>
  `
}

function iconInnerSvg(size, x = 0, y = 0) {
  const s = size / 330
  return `
    <g transform="translate(${x} ${y}) scale(${s})">
      <circle cx="165" cy="165" r="144" fill="${green}" fill-opacity="0.12"/>
      <path d="M67 228V92H118L165 164L212 92H263V228H217V158L178 216H152L113 158V228H67Z" fill="${text}"/>
      <path d="M82 263H248" stroke="${green}" stroke-width="26" stroke-linecap="round"/>
      <circle cx="278" cy="263" r="18" fill="${green}"/>
    </g>
  `
}

function safariPinnedTabSvg() {
  return `
    <svg width="512" height="512" viewBox="0 0 512 512" xmlns="http://www.w3.org/2000/svg">
      <path fill="#000" d="M80 352V144h78l98 145 98-145h78v208h-70V245l-79 107h-54l-79-107v107H80Zm25 72h258v48H105v-48Zm316 0a35 35 0 1 0 0 70 35 35 0 0 0 0-70Z"/>
    </svg>
  `
}

function icoFromPng(pngBuffer) {
  const header = Buffer.alloc(22)
  header.writeUInt16LE(0, 0)
  header.writeUInt16LE(1, 2)
  header.writeUInt16LE(1, 4)
  header.writeUInt8(32, 6)
  header.writeUInt8(32, 7)
  header.writeUInt8(0, 8)
  header.writeUInt8(0, 9)
  header.writeUInt16LE(1, 10)
  header.writeUInt16LE(32, 12)
  header.writeUInt32LE(pngBuffer.length, 14)
  header.writeUInt32LE(22, 18)
  return Buffer.concat([header, pngBuffer])
}

function loadSharp() {
  try {
    return require("sharp")
  } catch {
    const pnpmDir = resolve(process.cwd(), "../../node_modules/.pnpm")
    if (existsSync(pnpmDir)) {
      const sharpPackage = readdirSync(pnpmDir).find((entry) => entry.startsWith("sharp@"))
      if (sharpPackage) {
        return require(join(pnpmDir, sharpPackage, "node_modules/sharp"))
      }
    }
  }

  throw new Error("Unable to load sharp. Run the workspace install before generating assets.")
}
