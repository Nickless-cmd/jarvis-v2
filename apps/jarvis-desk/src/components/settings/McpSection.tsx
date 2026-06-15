import { useEffect, useState } from 'react'
import { Trash2 } from 'lucide-react'
import type { ApiConfig } from '../../lib/api'
import { getAccountMcp, addMcpServer, removeMcpServer, type McpServer } from '../../lib/coworkApi'

/** MCP-sektion (§4.6, owner-only). Konfigurations-lager for MCP-server-endpoints.
 *  Runtime-konsumption er et separat spor — her ejer vi konfigurationen. */
export function McpSection({ config }: { config: ApiConfig | undefined }) {
  const [servers, setServers] = useState<McpServer[] | null>(null)
  const [error, setError] = useState(false)
  const [name, setName] = useState('')
  const [url, setUrl] = useState('')

  const load = () => {
    if (!config) return
    getAccountMcp(config).then(setServers).catch(() => setError(true))
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

  if (error) return <div className="settings-section">Kunne ikke hente MCP-servere.</div>
  if (!servers) return <div className="settings-section">Indlæser MCP…</div>

  return (
    <div className="settings-section mcp-section">
      <h3>MCP-servere</h3>
      <div className="mcp-add">
        <input placeholder="Navn" value={name} onChange={(e) => setName(e.target.value)} />
        <input placeholder="URL (https://…)" value={url} onChange={(e) => setUrl(e.target.value)} />
        <button type="button" onClick={() => void add()}>Tilføj</button>
      </div>
      {servers.length === 0 && <div className="cowork-empty">Ingen MCP-servere konfigureret.</div>}
      <div className="mcp-list">
        {servers.map((s) => (
          <div key={s.id} className="mcp-row">
            <span className="mcp-name">{s.name}</span>
            <span className="mcp-url">{s.url}</span>
            <button type="button" aria-label="Fjern" className="todo-del-btn" onClick={() => void remove(s.id)}>
              <Trash2 size={13} />
            </button>
          </div>
        ))}
      </div>
    </div>
  )
}
