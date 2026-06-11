import Link from 'next/link'

export default function Header() {
  return (
    <header className="border-b border-[#1E293B] bg-[#0F172A] sticky top-0 z-20">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-14 flex items-center justify-between">
        <Link href="/" className="flex items-center gap-3">
          <div className="w-2 h-2 rounded-full bg-blue-500" />
          <span className="font-mono text-sm font-semibold tracking-widest uppercase text-white">
            Downstream
          </span>
        </Link>
        <span className="font-mono text-xs text-[#64748B] hidden sm:block">
          Follow the chain.
        </span>
      </div>
    </header>
  )
}
