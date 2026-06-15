import { useEffect, useState } from 'react'
import type { ApiConfig } from '../../lib/api'
import { getAccountQuota, type QuotaOverview, type QuotaItem } from '../../lib/coworkApi'

const LABELS: Record<QuotaItem['kind'], string> = {
  chat: 'Chat-beskeder',
  code: 'Code-minutter',
  cowork: 'Cowork-godkendelser',
  agent: 'Agent-dispatches',
}

export function KvoteSection({ config }: { config: ApiConfig | undefined }) {
  const [data, setData] = useState<QuotaOverview | null>(null)
  const [error, setError] = useState(false)

  useEffect(() => {
    if (!config) return
    let alive = true
    getAccountQuota(config)
      .then((d) => { if (alive) setData(d) })
      .catch(() => { if (alive) setError(true) })
    return () => { alive = false }
  }, [config?.apiBaseUrl, config?.authToken])

  if (error) return <div className="settings-section">Kunne ikke hente kvoten.</div>
  if (!data) return <div className="settings-section">Indlæser kvote…</div>

  return (
    <div className="settings-section kvote-section">
      <h3>Kvote <span className="badge badge-ok">{data.tier}</span></h3>
      <div className="quota-list">
        {data.items.map((it) => {
          const unlimited = it.limit == null
          const pct = unlimited || !it.limit ? 0 : Math.min(100, Math.round((it.used / it.limit) * 100))
          return (
            <div key={it.kind} className={`quota-row${it.warn ? ' warn' : ''}`}>
              <div className="quota-head">
                <span>{LABELS[it.kind]}</span>
                <span className="quota-num">{unlimited ? 'ubegrænset' : `${it.used} / ${it.limit}`}</span>
              </div>
              {!unlimited && (
                <div className="quota-bar"><div className="quota-fill" style={{ width: `${pct}%` }} /></div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
