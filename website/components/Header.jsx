import Link from 'next/link'

export default function Header() {
  return (
    <header className="border-b border-[#1E293B] bg-[#0F172A]">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 sm:py-8">
        <div className="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-4">

          {/* Wordmark */}
          <Link href="/" className="group flex items-center gap-4">
            {/* Animated dot cluster */}
            <div className="flex flex-col gap-1">
              <div className="flex gap-1">
                <div className="w-2 h-2 rounded-full bg-[#1D4ED8]" />
                <div className="w-2 h-2 rounded-full bg-[#3B82F6]" />
              </div>
              <div className="flex gap-1">
                <div className="w-2 h-2 rounded-full bg-[#3B82F6]" />
                <div className="w-2 h-2 rounded-full bg-[#60A5FA]" />
              </div>
            </div>

            <div>
              <div className="text-3xl sm:text-4xl font-bold text-white tracking-tight leading-none group-hover:text-[#60A5FA] transition-colors duration-200">
                Downstream
              </div>
              <div className="font-sans text-xs text-[#3B82F6] tracking-widest uppercase mt-1">
                Follow the chain.
              </div>
            </div>
          </Link>

          {/* Right side: date + description */}
          <div className="sm:text-right">
            <div className="font-sans text-[11px] text-[#64748B] uppercase tracking-widest">
              Daily macro implication chains
            </div>
            <div className="font-sans text-[11px] text-[#475569] mt-0.5">
              Rates · FX · Equities · Commodities
            </div>
          </div>

        </div>
      </div>
    </header>
  )
}
