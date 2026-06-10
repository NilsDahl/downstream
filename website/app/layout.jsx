import { Playfair_Display, JetBrains_Mono } from 'next/font/google'
import './globals.css'

const playfair = Playfair_Display({
  subsets: ['latin'],
  variable: '--font-playfair',
  display: 'swap',
})

const jetbrains = JetBrains_Mono({
  subsets: ['latin'],
  variable: '--font-jetbrains',
  display: 'swap',
})

export const metadata = {
  title: 'Downstream — Follow the chain.',
  description: 'Daily macro implication chain analysis. Trace cause-and-effect through financial markets.',
}

export default function RootLayout({ children }) {
  return (
    <html lang="en" className={`${playfair.variable} ${jetbrains.variable}`}>
      <body className="bg-parchment text-ink antialiased min-h-screen">
        {children}
      </body>
    </html>
  )
}
