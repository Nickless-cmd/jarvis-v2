import { useEffect, useState } from 'react'
import type { ApiConfig } from '../../lib/api'
import { getAccountApps, type ConnectedApp } from '../../lib/coworkApi'

/** Apps-sektion (§4.5). Connectede apps = plugin-registry (kind=connector).
 *  Connector-implementationerne registrerer sig selv; her er management-fladen. */
export function AppsSection({ config }: { config: ApiConfig | undefined }) {
  const [apps, setApps] = useState<ConnectedApp[] | null>(null)
  const [error, setError] = useState(false)

  useEffect(() => {
    if (!config) return
    let alive = true
    getAccountApps(config)
      .then((a) => { if (alive) setApps(a) })
      .catch(() => { if (alive) setError(true) })
    return () => { alive = false }
  }, [config?.apiBaseUrl, config?.authToken])

  if (error) return <div className="settings-section">Kunne ikke hente apps.</div>
  if (!apps) return <div className="settings-section">Indlæser apps…</div>

  return (
    <div className="settings-section apps-section">
      <h3>Apps</h3>
      {apps.length === 0 && <div className="cowork-empty">Ingen connectede apps endnu.</div>}
      <div className="apps-list">
        {apps.map((a) => (
          <div key={a.plugin_id} className="apps-row">
            <span className="apps-name">{a.name}</span>
            <span className={`badge ${a.status === 'connected' ? 'badge-ok' : 'badge-warn'}`}>{a.status}</span>
          </div>
        ))}
      </div>
    </div>
  )
}
