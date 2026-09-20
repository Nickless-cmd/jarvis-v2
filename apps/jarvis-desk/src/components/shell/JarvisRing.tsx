import './JarvisPulse.css'

/** Shared Puls mark. Keep the existing API for header, chat and code callers. */
export function JarvisRing({ size = 15, spinning = false, tone = 'idle' }: {
  size?: number
  spinning?: boolean
  tone?: 'idle' | 'working' | 'error'
}) {
  return (
    <span className={`jarvis-ring jarvis-pulse${spinning ? ' is-working' : ''}${tone === 'error' ? ' is-error' : ''}`} aria-hidden="true">
      <svg viewBox="0 0 100 100" width={size} height={size} fill="currentColor">
        <rect x="15" y="32" width="19" height="36" rx="9.5" />
        <rect x="41" y="19.5" width="19" height="61" rx="9.5" />
        <rect x="67" y="30.5" width="19" height="39" rx="9.5" />
      </svg>
    </span>
  )
}
