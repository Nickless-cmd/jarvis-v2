import { useEffect, useState } from 'react'
import { ShieldCheck, ShieldOff, Trash2 } from 'lucide-react'
import type { ApiConfig } from '../../lib/api'
import {
  addMcpServer,
  allowMcpServer,
  getAccountMcp,
  getMcpTrust,
  removeMcpServer,
  revokeMcpServer,
  type McpServer,
  type McpTrustRow,
} from '../../lib/coworkApi'

/** MCP-sektion (owner-only).
 *
 *  Var indtil 6/9-2026 et rent konfigurations-lager — man kunne tilføje en
 *  server og aldrig godkende den herfra, altså tilføje noget der aldrig kunne
 *  bruges. Nu er begge halvdele her: registeret ER adressebogen, godkendelsen
 *  ER beslutningen, og de to er bevidst adskilt i UI'et. En server der bare
 *  står på listen kan ingenting.
 */
export function McpSection({ config }: { config: ApiConfig | undefined }) {
  const [servers, setServers] = useState<McpServer[] | null>(null)
  const [trust, setTrust] = useState<Record<string, McpTrustRow>>({})
  const [error, setError] = useState(false)
  const [name, setName] = useState('')
  const [url, setUrl] = useState('')
  const [travl, setTravl] = useState('')

  const load = () => {
    if (!config) return
    getAccountMcp(config).then(setServers).catch(() => setError(true))
    getMcpTrust(config)
      .then((d) => {
        const kort: Record<string, McpTrustRow> = {}
        for (const r of d.servere ?? []) kort[r.navn] = r
        setTrust(kort)
      })
      .catch(() => setTrust({}))
  }
  useEffect(load, [config?.apiBaseUrl, config?.authToken])

  const add = async () => {
    if (!config || !name.trim() || !url.trim()) return
    await addMcpServer(config, name.trim(), url.trim())
    setName(''); setUrl(''); load()
  }
  const remove = async (id: string) => {
    if (!config) return
    await removeMcpServer(config, id); load()
  }
  const skiftTillid = async (navn: string, godkend: boolean) => {
    if (!config) return
    setTravl(navn)
    try {
      await (godkend ? allowMcpServer(config, navn) : revokeMcpServer(config, navn))
      load()
    } finally {
      setTravl('')
    }
  }

  if (error) return <div className="settings-section">Kunne ikke hente MCP-servere.</div>
  if (!servers) return <div className="settings-section">Indlæser MCP…</div>

  return (
    <div className="settings-section mcp-section">
      <h3>MCP-servere</h3>
      <p className="settings-hint">
        At tilføje en server er ikke det samme som at godkende den. Først når du
        godkender, må Jarvis forbinde og bruge dens værktøjer. Første forbindelse
        låses til serverens identitet — skifter den bagefter, blokeres den indtil
        du godkender på ny.
      </p>
      <div className="mcp-add">
        <input placeholder="Navn" value={name} onChange={(e) => setName(e.target.value)} />
        <input placeholder="URL (https://…)" value={url} onChange={(e) => setUrl(e.target.value)} />
        <button type="button" onClick={() => void add()}>Tilføj</button>
      </div>
      {servers.length === 0 && <div className="cowork-empty">Ingen MCP-servere konfigureret.</div>}
      <div className="mcp-list">
        {servers.map((s) => {
          const t = trust[s.name]
          const godkendt = Boolean(t?.godkendt)
          return (
            <div key={s.id} className="mcp-row">
              <span className="mcp-name">{s.name}</span>
              <span className="mcp-url">{s.url}</span>
              <span className={godkendt ? 'mcp-trust ok' : 'mcp-trust nej'}>
                {godkendt
                  ? t?.forbundet
                    ? `godkendt · ${t.vaerktoejer} værktøjer`
                    : 'godkendt'
                  : 'ikke godkendt'}
              </span>
              <button
                type="button"
                className="mcp-trust-btn"
                disabled={travl === s.name}
                aria-label={godkendt ? 'Tilbagekald' : 'Godkend'}
                title={godkendt
                  ? 'Tilbagekald godkendelsen og glem serverens identitet'
                  : 'Godkend, så Jarvis må forbinde og bruge serverens værktøjer'}
                onClick={() => void skiftTillid(s.name, !godkendt)}
              >
                {godkendt ? <ShieldOff size={13} /> : <ShieldCheck size={13} />}
              </button>
              <button type="button" aria-label="Fjern" className="todo-del-btn" onClick={() => void remove(s.id)}>
                <Trash2 size={13} />
              </button>
            </div>
          )
        })}
      </div>
    </div>
  )
}
