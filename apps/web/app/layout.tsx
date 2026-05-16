import type { Metadata, Viewport } from 'next'
import { Geist, Geist_Mono } from 'next/font/google'
import { Analytics } from '@vercel/analytics/next'
import './globals.css'

const _geist = Geist({ subsets: ["latin"] });
const _geistMono = Geist_Mono({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: 'Matchmind — FIFA World Cup 2026 Match Intelligence',
  description: 'AI-powered World Cup 2026 analysis with match insights, odds context, market signals, and tournament tracking.',
  applicationName: 'Matchmind',
  appleWebApp: {
    title: 'Matchmind',
  },
  openGraph: {
    title: 'Matchmind — FIFA World Cup 2026 Match Intelligence',
    description: 'AI-powered World Cup 2026 analysis with match insights, odds context, market signals, and tournament tracking.',
    siteName: 'Matchmind',
    type: 'website',
  },
  twitter: {
    card: 'summary',
    title: 'Matchmind — FIFA World Cup 2026 Match Intelligence',
    description: 'AI-powered World Cup 2026 analysis with match insights, odds context, market signals, and tournament tracking.',
  },
  icons: {
    icon: [
      {
        url: '/icon-light-32x32.png',
        media: '(prefers-color-scheme: light)',
      },
      {
        url: '/icon-dark-32x32.png',
        media: '(prefers-color-scheme: dark)',
      },
      {
        url: '/icon.svg',
        type: 'image/svg+xml',
      },
    ],
    apple: '/apple-icon.png',
  },
}

export const viewport: Viewport = {
  width: 'device-width',
  initialScale: 1,
  viewportFit: 'cover',
  interactiveWidget: 'resizes-content',
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    <html lang="en" className="bg-background">
      <body className="font-sans antialiased bg-background text-foreground">
        {children}
        {process.env.NODE_ENV === 'production' && <Analytics />}
      </body>
    </html>
  )
}
