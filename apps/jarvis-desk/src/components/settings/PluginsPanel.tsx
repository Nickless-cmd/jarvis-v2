import { useEffect, useState } from 'react'
import type { ApiConfig } from '../../lib/api'
import {
  getPluginsOverview, putPluginRuleset,
  type PluginRuleset,
} from '../../lib/pluginsApi'

interface ChannelServer { id: string; name: string; botToken: string; serverId: string }
interface DeskConfig {
  get: () => Promise<{ channelPlugins?: ChannelServer[] }>
  set: (cfg: { channelPlugins?: ChannelServer[] }) => Promise<boolean>
}
function deskConfig(): DeskConfig | undefined {
  return (window as unknown as { jarvisDesk?: { config: DeskConfig } }).jarvisDesk?.config
}

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
  // Kanal-servere (lokalt i app-config) + server-rapporteret status
  const [servers, setServers] = useState<ChannelServer[]>([])
  const [status, setStatus] = useState<Record<string, string>>({})
  const [srvName, setSrvName] = useState('')
  const [srvToken, setSrvToken] = useState('')
  const [srvId, setSrvId] = useState('')

  const load = async () => {
    if (!config) return
    try {
      const o = await getPluginsOverview(config)
      setRulesets(o.rulesets ?? {})
      const st: Record<string, string> = {}
      for (const c of (o.connected ?? []) as Array<{ plugin_id: string; status?: string }>) {
        st[c.plugin_id] = c.status ?? 'offline'
      }
      setStatus(st)
    } catch { /* 403 for ikke-owner — panel skjules alligevel af kalderen */ }
  }

  const loadServers = async () => {
    try {
      const cfg = await deskConfig()?.get()
      setServers(cfg?.channelPlugins ?? [])
    } catch { /* ikke i Electron */ }
  }

  const addServer = async () => {
    if (!srvToken.trim() || !srvId.trim()) return
    const next = [
      ...servers.filter((s) => s.serverId !== srvId.trim()),
      { id: `discord-local:${srvId.trim()}`, name: srvName.trim() || srvId.trim(), botToken: srvToken.trim(), serverId: srvId.trim() },
    ]
    await deskConfig()?.set({ channelPlugins: next })  // token gemmes LOKALT, aldrig på serveren
    setServers(next)
    setSrvName(''); setSrvToken(''); setSrvId('')
  }

  const removeServer = async (serverId: string) => {
    const next = servers.filter((s) => s.serverId !== serverId)
    await deskConfig()?.set({ channelPlugins: next })
    setServers(next)
  }

  useEffect(() => { void load(); void loadServers() }, [config?.apiBaseUrl, config?.authToken])

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
        Forbind Jarvis til dine egne Discord-servere via en lokal gateway —
        bot-token bliver <strong>lokalt på din maskine</strong>, aldrig på Jarvis' server.
        Definer derunder <strong>regelsæt</strong> der gælder for alle, også dig.
      </p>

      <div className="plugins-servers">
        <div className="plugins-existing-head">Dine Discord-servere</div>
        {servers.length === 0 && <div className="cowork-empty">Ingen servere forbundet endnu.</div>}
        <ul>
          {servers.map((s) => (
            <li key={s.serverId} className="plugins-server-item">
              <span><strong>{s.name}</strong> ({s.serverId})</span>
              <span className={`plugins-status plugins-status-${status[s.id] || 'offline'}`}>
                {status[s.id] || 'offline'}
              </span>
              <button type="button" className="totp-revoke" onClick={() => void removeServer(s.serverId)}>Fjern</button>
            </li>
          ))}
        </ul>
        <div className="plugins-add-server">
          <input type="text" value={srvName} onChange={(e) => setSrvName(e.target.value)} placeholder="Navn (fx Mikkels server)" />
          <input type="text" value={srvId} onChange={(e) => setSrvId(e.target.value)} placeholder="Server-ID" />
          <input type="password" value={srvToken} onChange={(e) => setSrvToken(e.target.value)} placeholder="Bot-token (bliver lokalt)" />
          <button type="button" onClick={() => void addServer()}>Tilføj server</button>
        </div>
      </div>

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
