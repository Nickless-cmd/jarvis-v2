import { useCallback, useEffect, useState } from 'react'
import type { ApiConfig } from '../lib/api'
import { getQuota, type QuotaOverview } from '../lib/accountApi'

const LABELS: Record<string, string> = {
  chat: 'Chat', code: 'Kode', cowork: 'Cowork', agent: 'Agent',
}

/** Forbrug & kvote (§5.2): tier + brug pr. type. Read-only, self-scoped. */
export function QuotaPanel({ config }: { config?: ApiConfig }) {
  const [data, setData] = useState<QuotaOverview | null>(null)
  const [err, setErr] = useState(false)

  const load = useCallback(() => {
    if (!config) return
    getQuota(config)
      .then((d) => { setData(d); setErr(false) })
      .catch(() => setErr(true))
  }, [config])

  useEffect(() => { load() }, [load])

  if (!config) return null

  return (
    <section className="quota-panel">
      <h3>Forbrug &amp; kvote</h3>
      {err && <p className="quota-err">Kunne ikke hente forbrug.</p>}
      {data && (
        <>
          <div className="quota-tier">Plan: <strong>{data.tier}</strong></div>
          <table className="quota-table">
            <thead><tr><th>Type</th><th>Brugt</th><th>Grænse</th><th>Tilbage</th></tr></thead>
            <tbody>
              {data.items.map((it) => (
                <tr key={it.kind} className={it.warn ? 'quota-warn' : ''}>
                  <td>{LABELS[it.kind] ?? it.kind}</td>
                  <td>{it.used}</td>
                  <td>{it.limit ?? '∞'}</td>
                  <td>{it.remaining ?? '∞'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      )}
    </section>
  )
}
