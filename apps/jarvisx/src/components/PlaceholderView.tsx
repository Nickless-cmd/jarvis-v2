import type { ReactNode } from 'react'

interface Props {
  title: string
  hint: string
  apiBaseUrl: string
  children?: ReactNode
}

/**
 * Reusable shell for views that aren't fully implemented yet. Lets us
 * ship the full sidebar structure today while we incrementally fill in
 * each view's data wiring.
 */
export function PlaceholderView({ title, hint, apiBaseUrl, children }: Props) {
  return (
    <div className="flex h-full flex-col">
      <header className="flex items-center justify-between border-b border-line bg-bg1 px-4 py-2">
        <h2 className="text-sm font-semibold">{title}</h2>
        <span className="font-mono text-[10px] text-fg3">{apiBaseUrl}</span>
      </header>
      <div className="flex flex-1 flex-col items-center justify-center gap-3 px-6 py-10 text-center">
        <div className="rounded-full border border-line2 bg-bg2 px-3 py-1 font-mono text-[10px] uppercase tracking-wider text-accent">
          phase 1+
        </div>
        <h3 className="text-base font-semibold text-fg">{title}</h3>
        <p className="max-w-md text-xs text-fg3">{hint}</p>
        {children}
      </div>
    </div>
  )
}
