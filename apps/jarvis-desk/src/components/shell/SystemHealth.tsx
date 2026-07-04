import { useMemo, useState } from 'react'
import type { CanonicalError } from '../../lib/canonicalError'

type Health = 'ok' | 'degraded' | 'attention'

/** Udled system-helbred fra nylige kanoniske fejl (seneste 60s). Self-safe mod undefined. */
function deriveHealth(errors: CanonicalError[]): Health {
  const cutoff = Date.now() - 60_000
  const recent = (errors ?? []).filter((e) => e.receivedAt >= cutoff)
  if (recent.some((e) => e.severity === 'critical' || e.severity === 'error')) return 'attention'
  if (recent.some((e) => e.severity === 'warning' || e.recoverable === 'degraded')) return 'degraded'
  return 'ok'
}

const HEALTH_DA: Record<Health, string> = {
  ok: 'Alt kører',
  degraded: 'Nedsat',
  attention: 'Kræver opsyn',
}

/**
 * Minimal system-helbreds-chip (sidebar-fod/header). Klik → transparens-log over
 * nylige kanoniske fejl med correlation_id. Kun observabilitet.
 */
export function SystemHealth({ errors }: { errors: CanonicalError[] }) {
  const list = errors ?? []
  const [open, setOpen] = useState(false)
  const health = useMemo(() => deriveHealth(list), [list])
  return (
    <div className="syshealth">
      <button
        type="button"
        className={`syshealth-chip syshealth-${health}`}
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
        title={HEALTH_DA[health]}
      >
        <span className="syshealth-dot" />
        <span className="syshealth-label">{HEALTH_DA[health]}</span>
      </button>
      {open && (
        <div className="syshealth-log" role="region" aria-label="Transparens-log">
          {list.length === 0 ? (
            <div className="syshealth-empty">Ingen fejl registreret.</div>
          ) : (
            <ul className="syshealth-list">
              {list.slice(0, 20).map((e, i) => (
                <li
                  key={`${e.correlationId || e.code}-${e.receivedAt}-${i}`}
                  className={`syshealth-item syshealth-sev-${e.severity}`}
                >
                  <span className="syshealth-item-code">{e.kind ?? e.code}</span>
                  <span className="syshealth-item-msg">{e.message}</span>
                  {e.correlationId && (
                    <span className="syshealth-item-cid" title="correlation_id (run)">
                      #{e.correlationId.slice(0, 8)}
                    </span>
                  )}
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  )
}
