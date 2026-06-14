import { useEffect, useState } from 'react'
import type { ApiConfig } from '../../lib/api'
import {
  getPluginsOverview, putPluginRuleset,
  type PluginRuleset,
} from '../../lib/pluginsApi'

/**
 * Plugins & Kanaler (spec §5.4, Fase 6 #2). Plugin-rammen er §14-deferred, så
 * "tilgængelige/forbundne" er tomme; den funktionelle del er regelsæt-editoren
 * (plugin_ruleset). Owner redigerer pr. kanal-plugin: tilladte kanaler, blokerede
 * roller, stilletid. Regelsæt er hardblock for ALLE inkl. owner (§5.3).
 */
const _csv = (s: string): string[] =>
  s.split(',').map((x) => x.trim()).filter(Boolean)

export function PluginsPanel({ config }: { config: ApiConfig | undefined }) {
  const [pluginId, setPluginId] = useState('discord')
  const [channels, setChannels] = useState('')
  const [roles, setRoles] = useState('')
  const [quietStart, setQuietStart] = useState('')
  const [quietEnd, setQuietEnd] = useState('')
  const [rulesets, setRulesets] = useState<Record<string, PluginRuleset>>({})
  const [saved, setSaved] = useState(false)

  const load = async () => {
    if (!config) return
    try {
      const o = await getPluginsOverview(config)
      setRulesets(o.rulesets ?? {})
    } catch { /* 403 for ikke-owner — panel skjules alligevel af kalderen */ }
  }

  useEffect(() => { void load() }, [config?.apiBaseUrl, config?.authToken])

  // Synk felter når man vælger et plugin der allerede har et regelsæt.
  useEffect(() => {
    const rs = rulesets[pluginId]
    setChannels((rs?.allowed_channels ?? []).join(', '))
    setRoles((rs?.blocked_roles ?? []).join(', '))
    setQuietStart(rs?.quiet_hours ? String(rs.quiet_hours[0]) : '')
    setQuietEnd(rs?.quiet_hours ? String(rs.quiet_hours[1]) : '')
  }, [pluginId, rulesets])

  const save = async () => {
    if (!config) return
    const rs: PluginRuleset = {}
    if (channels.trim()) rs.allowed_channels = _csv(channels)
    if (roles.trim()) rs.blocked_roles = _csv(roles)
    if (quietStart.trim() && quietEnd.trim()) {
      rs.quiet_hours = [Number(quietStart), Number(quietEnd)]
    }
    await putPluginRuleset(config, pluginId.trim(), rs)
    setSaved(true)
    setTimeout(() => setSaved(false), 1800)
    void load()
  }

  return (
    <div className="plugins-panel">
      <h3>Plugins &amp; Kanaler</h3>
      <p className="plugins-note">
        Plugin-rammen (connectors + lokale gateways) kommer senere. Her kan du
        definere <strong>regelsæt</strong> for kanal-plugins — de gælder for alle, også dig.
      </p>

      <div className="plugins-ruleset-editor">
        <label>
          <span>Kanal-plugin</span>
          <input type="text" value={pluginId} onChange={(e) => setPluginId(e.target.value)}
            placeholder="discord / telegram / slack" />
        </label>
        <label>
          <span>Tilladte kanaler (komma)</span>
          <input type="text" value={channels} onChange={(e) => setChannels(e.target.value)}
            placeholder="general, support" />
        </label>
        <label>
          <span>Blokerede roller (komma)</span>
          <input type="text" value={roles} onChange={(e) => setRoles(e.target.value)}
            placeholder="støj" />
        </label>
        <div className="plugins-quiet">
          <label>
            <span>Stilletid fra</span>
            <input type="number" min={0} max={23} value={quietStart}
              onChange={(e) => setQuietStart(e.target.value)} placeholder="22" />
          </label>
          <label>
            <span>til</span>
            <input type="number" min={0} max={23} value={quietEnd}
              onChange={(e) => setQuietEnd(e.target.value)} placeholder="8" />
          </label>
        </div>
        <div className="plugins-actions">
          <button type="button" onClick={() => void save()}>Gem regelsæt</button>
          {saved && <span className="settings-saved">Gemt ✓</span>}
        </div>
      </div>

      {Object.keys(rulesets).length > 0 && (
        <div className="plugins-existing">
          <div className="plugins-existing-head">Gemte regelsæt</div>
          <ul>
            {Object.entries(rulesets).map(([pid, rs]) => (
              <li key={pid}>
                <strong>{pid}</strong>: {(rs.allowed_channels ?? []).length} kanaler,{' '}
                {(rs.blocked_roles ?? []).length} blokerede roller
                {rs.quiet_hours ? `, stille ${rs.quiet_hours[0]}–${rs.quiet_hours[1]}` : ''}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}
