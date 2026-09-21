import { useSettingsResource } from '../../hooks/useSettingsResource'
import { SettingsState, SettingsActionError } from './SettingsState'
import { useState } from 'react'
import type { ApiConfig } from '../../lib/api'
import { getJarvisOverview, setVisibleModel } from '../../lib/coworkApi'

/** Jarvis-sektion (§4.2, owner-only). Model pr. lane (read) + valg af synlig-lane-
 *  model. Diagnostik: credentials-ready pr. lane. */
export function JarvisSection({ config }: { config: ApiConfig | undefined }) {
  const resource = useSettingsResource(config, getJarvisOverview)
  const data = resource.data
  const [saved, setSaved] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const visible = data?.lanes.find(l => l.lane === 'visible')
  const pick = async (value: string) => {
    if (!config || busy) return
    const [provider = '', model = ''] = value.split('|')
    setBusy(true); setError(''); setSaved(false)
    try { await setVisibleModel(config, provider, model); setSaved(true); resource.retry() }
    catch { setError('Modellen kunne ikke ændres. Prøv igen.') }
    finally { setBusy(false) }
  }
  if (!data) return <SettingsState status={resource.status} label="Jarvis-indstillinger" onRetry={resource.retry} />

  return (
    <div className="settings-section jarvis-section">
      <h3>Jarvis’ modeller</h3>
      <SettingsActionError message={error} />

      <label className="jarvis-model-field">
        <span>Model til dine samtaler</span>
        <select disabled={busy}
          value={visible ? `${visible.provider}|${visible.model}` : ''}
          onChange={(e) => void pick(e.target.value)}
        >
          {data.visible_options.map((o) => (
            <option key={`${o.provider}|${o.model}`} value={`${o.provider}|${o.model}`}>
              {o.provider} · {o.model}
            </option>
          ))}
        </select>
        {saved && <span className="settings-saved">Gemt ✓</span>}
      </label>

      <h4>Modeller til de forskellige opgaver</h4>
      <div className="jarvis-lanes">
        {data.lanes.map((l) => (
          <div key={l.lane} className="jarvis-lane">
            <span className="jarvis-lane-name">{{ visible: 'Samtaler', internal: 'Internt arbejde', cheap: 'Små baggrundsopgaver' }[l.lane] ?? l.lane}</span>
            <span className="jarvis-lane-model">{l.active ? `${l.provider} · ${l.model}` : '—'}</span>
            {l.active && (l.credentials_ready
              ? <span className="badge badge-ok">klar</span>
              : <span className="badge badge-warn">mangler nøgle</span>)}
          </div>
        ))}
      </div>
    </div>
  )
}
