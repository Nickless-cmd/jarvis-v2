import { useEffect, useState } from 'react'
import { Wifi, WifiOff, Globe, Home, ShieldAlert, Loader2 } from 'lucide-react'

interface Props {
  apiBaseUrl: string
}

type Status =
  | { kind: 'checking' }
  | { kind: 'local'; latencyMs: number }
  | { kind: 'remote'; latencyMs: number }
  | { kind: 'offline'; error: string }
  | { kind: 'auth-required' }

const POLL_MS = 15000  // 15s — connection state isn't bursty

/**
 * Small pill in the chat top-toolbar that shows what backend JarvisX
 * is talking to: localhost, remote URL, offline, or auth-walled.
 *
 * Why: when something stops working, the first question is "is the
 * backend up". A pill that's always visible turns that into a glance
 * instead of a Settings round-trip. When connection is healthy the
 * pill is muted; when something's wrong it turns warn/danger so the
 * user notices without needing to look for it.
 *
 * Detection:
 *   - Local: apiBaseUrl matches localhost / 127.0.0.1 / 0.0.0.0
 *   - Remote: anything else
 *   - Auth-required: ping returns 401 (means backend is up but
 *     enforcing auth — the token is missing or stale)
 *   - Offline: ping fails (network, dns, server down)
 *
 * Polls /openapi.json every 15s — same target as electron's main
 * process ping loop, no new endpoint needed.
 */
export function ConnectionPill({ apiBaseUrl }: Props) {
  const [status, setStatus] = useState<Status>({ kind: 'checking' })
  const isLocalUrl = /^https?:\/\/(localhost|127\.0\.0\.1|0\.0\.0\.0)(?::|\/|$)/.test(
    apiBaseUrl,
  )

  useEffect(() => {
    let cancelled = false
    const check = async () => {
      const start = Date.now()
      try {
        const ctrl = new AbortController()
        const timer = setTimeout(() => ctrl.abort(), 4000)
        const res = await fetch(
          `${apiBaseUrl.replace(/\/$/, '')}/openapi.json`,
          { signal: ctrl.signal },
        )
        clearTimeout(timer)
        if (cancelled) return
        if (res.status === 401) {
          setStatus({ kind: 'auth-required' })
          return
        }
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        const latencyMs = Date.now() - start
        setStatus(
          isLocalUrl
            ? { kind: 'local', latencyMs }
            : { kind: 'remote', latencyMs },
        )
      } catch (e) {
        if (cancelled) return
        setStatus({
          kind: 'offline',
          error: e instanceof Error ? e.message : String(e),
        })
      }
    }
    void check()
    const id = window.setInterval(check, POLL_MS)
    return () => {
      cancelled = true
      window.clearInterval(id)
    }
  }, [apiBaseUrl, isLocalUrl])

  // Also re-check when window regains focus — common case is "I came
  // back from VPN switching, is everything still happy?"
  useEffect(() => {
    const onFocus = () => {
      // Trigger a re-fetch by bumping state. The effect above re-runs
      // on apiBaseUrl change; we don't want to re-mount, so we just
      // trust the next 15s tick. For instant feedback users can also
      // just look at the pill — that's the whole point.
      // (Left as a no-op; explicit click-to-recheck is in Settings.)
      void onFocus
    }
    window.addEventListener('focus', onFocus)
    return () => window.removeEventListener('focus', onFocus)
  }, [])

  const display = renderStatus(status)
  const host = apiBaseUrl.replace(/^https?:\/\//, '').replace(/\/$/, '') || '?'

  return (
    <span
      title={`${display.tooltip}\n${apiBaseUrl}`}
      className={[
        'flex flex-shrink-0 items-center gap-1 rounded-md px-1.5 py-0.5 text-[10px] font-mono ring-1 transition-colors',
        display.cls,
      ].join(' ')}
    >
      <display.Icon size={10} className={status.kind === 'checking' ? 'animate-spin' : ''} />
      <span>{display.label}</span>
      {(status.kind === 'local' || status.kind === 'remote') && (
        <span className="opacity-60">{host}</span>
      )}
    </span>
  )
}

function renderStatus(s: Status): {
  label: string
  Icon: typeof Wifi
  cls: string
  tooltip: string
} {
  switch (s.kind) {
    case 'checking':
      return {
        label: 'tjekker',
        Icon: Loader2,
        cls: 'bg-bg2 text-fg3 ring-line2',
        tooltip: 'Tjekker forbindelse til backend…',
      }
    case 'local':
      return {
        label: 'local',
        Icon: Home,
        cls: 'bg-bg2 text-fg3 ring-line2',
        tooltip: `Localhost backend, ${s.latencyMs}ms`,
      }
    case 'remote':
      return {
        label: 'remote',
        Icon: Globe,
        cls: 'bg-accent2/10 text-accent2 ring-accent2/30',
        tooltip: `Remote backend, ${s.latencyMs}ms — verificér du stoler på serveren`,
      }
    case 'auth-required':
      return {
        label: 'auth',
        Icon: ShieldAlert,
        cls: 'bg-warn/15 text-warn ring-warn/30',
        tooltip:
          'Backend er oppe, men kræver token. Claim eller udskift den i Indstillinger → Authentication.',
      }
    case 'offline':
      return {
        label: 'offline',
        Icon: WifiOff,
        cls: 'bg-danger/15 text-danger ring-danger/30',
        tooltip: `Kan ikke nå backend: ${s.error}`,
      }
  }
}
