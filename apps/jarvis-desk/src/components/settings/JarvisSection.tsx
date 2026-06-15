import { useEffect, useState } from 'react'
import type { ApiConfig } from '../../lib/api'
import { getJarvisOverview, setVisibleModel, type JarvisOverview } from '../../lib/coworkApi'

/** Jarvis-sektion (§4.2, owner-only). Model pr. lane (read) + valg af synlig-lane-
 *  model. Diagnostik: credentials-ready pr. lane. */
export function JarvisSection({ config }: { config: ApiConfig | undefined }) {
  const [data, setData] = useState<JarvisOverview | null>(null)
  const [error, setError] = useState(false)
  const [saved, setSaved] = useState(false)

  const load = () => {
    if (!config) return
    getJarvisOverview(config).then(setData).catch(() => setError(true))
  }
  useEffect(load, [config?.apiBaseUrl, config?.authToken])

  const visible = data?.lanes.find((l) => l.lane === 'visible')

  const pick = async (value: string) => {
    if (!config) return
    const [provider = '', model = ''] = value.split('|')
    await setVisibleModel(config, provider, model)
    setSaved(true)
    setTimeout(() => setSaved(false), 1600)
    load()
  }

  if (error) return <div className="settings-section">Kunne ikke hente Jarvis-indstillinger.</div>
  if (!data) return <div className="settings-section">Indlæser Jarvis…</div>

  return (
    <div className="settings-section jarvis-section">
      <h3>Jarvis</h3>

      <label className="jarvis-model-field">
        <span>Synlig model</span>
        <select
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

      <h4>Modeller pr. lane</h4>
      <div className="jarvis-lanes">
        {data.lanes.map((l) => (
          <div key={l.lane} className="jarvis-lane">
            <span className="jarvis-lane-name">{l.lane}</span>
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
