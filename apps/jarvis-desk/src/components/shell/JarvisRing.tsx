import { useRef, type CSSProperties } from 'react'
import './JarvisPulse.css'
import { faseForsinkelse } from '../../lib/fasePin'

/** Maerkets omloeb — skal svare til `jarvis-puls` i JarvisPulse.css. */
const OMLOEB_MS = 1600

/** Shared Puls mark. Keep the existing API for header, chat and code callers. */
export function JarvisRing({ size = 15, spinning = false, tone = 'idle' }: {
  size?: number
  spinning?: boolean
  tone?: 'idle' | 'working' | 'error'
}) {
  // Pin til dokument-tid, saa to maerker monteret paa hver sit tidspunkt
  // pulser I FASE (spec punkt 8). Regnes ÉN gang pr. montering: en ny vaerdi
  // ved hver render ville genstarte animationen, og det er vaerre end at gaa
  // forskudt.
  const fase = useRef<string | null>(null)
  if (fase.current === null) fase.current = faseForsinkelse(OMLOEB_MS)

  return (
    <span className={`jarvis-ring jarvis-pulse${spinning ? ' is-working' : ''}${tone === 'error' ? ' is-error' : ''}`}
      style={{ '--fase': fase.current } as CSSProperties} aria-hidden="true">
      <svg viewBox="0 0 100 100" width={size} height={size} fill="currentColor">
        <rect x="15" y="32" width="19" height="36" rx="9.5" />
        <rect x="41" y="19.5" width="19" height="61" rx="9.5" />
        <rect x="67" y="30.5" width="19" height="39" rx="9.5" />
      </svg>
    </span>
  )
}
