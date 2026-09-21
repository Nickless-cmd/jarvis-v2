import { useSettingsResource } from '../../hooks/useSettingsResource'
import { SettingsState } from './SettingsState'
import type { ApiConfig } from '../../lib/api'
import { getAccountApps } from '../../lib/coworkApi'

/** Apps-sektion (§4.5). Connectede apps = plugin-registry (kind=connector).
 *  Connector-implementationerne registrerer sig selv; her er management-fladen. */
export function AppsSection({ config }: { config: ApiConfig | undefined }) {
  const resource = useSettingsResource(config, getAccountApps)
  const apps = resource.data

  if (!apps) return <SettingsState status={resource.status} label="apps" onRetry={resource.retry} />

  return (
    <div className="settings-section apps-section">
      <h3>Apps</h3>
      {apps.length === 0 && <div className="cowork-empty">Ingen tilsluttede apps endnu. Find en app under Find værktøjer ovenfor.</div>}
      <div className="apps-list">
        {apps.map((a) => (
          <div key={a.plugin_id} className="apps-row">
            <span className="apps-name">{a.name}</span>
            <span className={`badge ${a.status === 'connected' ? 'badge-ok' : 'badge-warn'}`}>{{ connected: 'Tilsluttet', disconnected: 'Afbrudt', error: 'Fejl', pending: 'Afventer', disabled: 'Slået fra' }[a.status] ?? a.status}</span>
          </div>
        ))}
      </div>
    </div>
  )
}
