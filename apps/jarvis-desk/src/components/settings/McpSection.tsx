import { useSettingsResource } from '../../hooks/useSettingsResource'
import { SettingsState, SettingsActionError } from './SettingsState'
import { useState } from 'react'
import { ShieldCheck, ShieldOff, Trash2 } from 'lucide-react'
import type { ApiConfig } from '../../lib/api'
import {
  addMcpServer,
  allowMcpServer,
  getAccountMcp,
  getMcpCatalog,
  getMcpTrust,
  installMcpCatalogEntry,
  removeMcpServer,
  revokeMcpServer,
  type McpCatalogEntry,
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
  const resource = useSettingsResource(config, async cfg => {
    const [servers, trust, katalog] = await Promise.all([
      getAccountMcp(cfg),
      getMcpTrust(cfg),
      // Kataloget er en KATALOG-fejl hvis den ikke kan hentes; den må ikke
      // vælte listen over installerede servere. Et tomt katalog er ærligt.
      getMcpCatalog(cfg).catch((): McpCatalogEntry[] => []),
    ])
    return {
      servers,
      trust: Object.fromEntries((trust.servere ?? []).map(row => [row.navn, row])),
      katalog,
    }
  })
  const [name, setName] = useState('')
  const [url, setUrl] = useState('')
  const [travl, setTravl] = useState('')
  const [actionError, setActionError] = useState('')
  const change = async (id: string, action: () => Promise<unknown>, added = false) => {
    if (travl) return
    setTravl(id); setActionError('')
    try {
      await action()
      if (added) { setName(''); setUrl('') }
      resource.retry()
    } catch { setActionError('Ændringen kunne ikke gemmes. Prøv handlingen igen.') }
    finally { setTravl('') }
  }
  if (!resource.data) return <SettingsState status={resource.status} label="MCP-servere og godkendelser" onRetry={resource.retry} />
  const { servers, trust, katalog } = resource.data

  return (
    <div className="settings-section mcp-section">
      <h3>MCP-servere</h3>
      <p className="settings-hint">
        At tilføje en server er ikke det samme som at godkende den. Først når du
        godkender, må Jarvis forbinde og bruge dens værktøjer. Første forbindelse
        låses til serverens identitet — skifter den bagefter, blokeres den indtil
        du godkender på ny.
      </p>
      <SettingsActionError message={actionError} />
      <div className="mcp-add">
        <input aria-label="Serverens navn" placeholder="Navn" value={name} onChange={(e) => setName(e.target.value)} />
        <input aria-label="Serverens adresse" placeholder="URL (https://…)" value={url} onChange={(e) => setUrl(e.target.value)} />
        <button type="button" disabled={!!travl || !name.trim() || !/^https?:\/\//i.test(url.trim())} onClick={() => config && void change('add', () => addMcpServer(config, name.trim(), url.trim()), true)}>Tilføj</button>
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
                disabled={!!travl}
                aria-label={godkendt ? 'Tilbagekald' : 'Godkend'}
                title={godkendt
                  ? 'Tilbagekald godkendelsen og glem serverens identitet'
                  : 'Godkend, så Jarvis må forbinde og bruge serverens værktøjer'}
                onClick={() => config && void change(s.id, () => godkendt ? revokeMcpServer(config, s.name) : allowMcpServer(config, s.name))}
              >
                {godkendt ? <ShieldOff size={13} /> : <ShieldCheck size={13} />}
              </button>
              <button type="button" aria-label="Fjern" className="todo-del-btn" disabled={!!travl} onClick={() => config && void change(s.id, () => removeMcpServer(config, s.id))}>
                <Trash2 size={13} />
              </button>
            </div>
          )
        })}
      </div>

      <h3>Markedsplads</h3>
      <p className="settings-hint">
        Kuraterede servere med ét klik. Installation registrerer serveren — den
        godkender den ikke. Godkendelsen er stadig din, og står i listen ovenfor.
      </p>
      {katalog.length === 0 && (
        <div className="cowork-empty">Kataloget kunne ikke hentes.</div>
      )}
      <div className="mcp-katalog">
        {katalog.map((k) => (
          <div key={k.id} className="mcp-katalog-kort">
            <div className="mcp-katalog-top">
              <span className="mcp-name">{k.name}</span>
              <span className="mcp-katalog-transport">{k.transport}</span>
            </div>
            <p className="mcp-katalog-tekst">{k.description}</p>
            {k.tools.length > 0 && (
              <span className="mcp-katalog-vaerktoejer">
                {k.tools.length} værktøjer · {k.tools.slice(0, 3).join(', ')}
                {k.tools.length > 3 ? ' …' : ''}
              </span>
            )}
            <div className="mcp-katalog-bund">
              <button
                type="button"
                disabled={!!travl || k.installed}
                onClick={() => config && void change(`kat-${k.id}`, () => installMcpCatalogEntry(config, k.id))}
              >
                {k.installed ? 'Installeret' : 'Installer'}
              </button>
              {k.source_url && (
                <a className="mcp-katalog-kilde" href={k.source_url} target="_blank" rel="noreferrer">
                  Kilde
                </a>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
