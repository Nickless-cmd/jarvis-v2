import { useCallback, useEffect, useRef, useState } from 'react'
import { MoreHorizontal, Search, X } from 'lucide-react'
import type { ApiConfig } from '../../lib/api'
import {
  getConnectors, setEnabled, deleteConnector, startConnect, type Connector,
} from '../../lib/connectorsApi'
import { connectorIcon } from '../../lib/connectorIcon'
import { setPendingHint } from '../../lib/postConnect'

function openBrowser(url: string): void {
  const b = (window as unknown as { jarvisDesk?: { openExternal?: (u: string) => Promise<void> } }).jarvisDesk
  void b?.openExternal?.(url)
}

/** Marketplace-zonen: forbind/til-fra/slet connectors med scope-transparens.
 *  Privatlivs-først — alt går via brugerens egen session/token. */
export function MarketplacePane({ config }: { config?: ApiConfig }) {
  const [items, setItems] = useState<Connector[]>([])
  const [query, setQuery] = useState('')
  const [busy, setBusy] = useState<string | null>(null)
  const [toast, setToast] = useState<string | null>(null)
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const refresh = useCallback(async () => {
    if (!config) return
    try { setItems(await getConnectors(config)) } catch { /* behold sidste */ }
  }, [config])

  useEffect(() => { void refresh() }, [refresh])
  useEffect(() => () => { if (pollRef.current) clearInterval(pollRef.current) }, [])

  const onConnect = async (c: Connector) => {
    if (!config) return
    setBusy(c.id)
    try {
      const url = await startConnect(config, c.id)
      if (url) openBrowser(url)
    } catch { setBusy(null); return }
    // Poll til connected (browser-flow afsluttes ude i browseren).
    let n = 0
    if (pollRef.current) clearInterval(pollRef.current)
    pollRef.current = setInterval(async () => {
      n += 1
      await refresh()
      const fresh = (await getConnectors(config).catch(() => [])).find((x) => x.id === c.id)
      if (fresh?.connected) {
        // Delight: kvittér + gem connector-specifikt hint til næste chat-tom-skærm.
        setToast(`✅ Forbundet til ${c.name}`)
        setTimeout(() => setToast(null), 4000)
        setPendingHint(fresh.post_connect_hint)
      }
      if (fresh?.connected || n > 60) {
        if (pollRef.current) clearInterval(pollRef.current)
        pollRef.current = null
        setBusy(null)
      }
    }, 2000)
  }

  const onToggle = async (c: Connector) => {
    if (!config) return
    await setEnabled(config, c.id, !c.enabled).catch(() => {})
    await refresh()
  }

  const onDelete = async (c: Connector) => {
    if (!config) return
    await deleteConnector(config, c.id).catch(() => {})
    await refresh()
  }

  const q = query.trim().toLowerCase()
  const visible = q
    ? items.filter((c) => c.name.toLowerCase().includes(q) || c.desc.toLowerCase().includes(q))
    : items
  const connected = visible.filter((c) => c.connected)
  const rest = visible.filter((c) => !c.connected && c.status !== 'coming_soon')
  const soon = visible.filter((c) => c.status === 'coming_soon')

  return (
    <div className="marketplace">
      {toast && <div className="marketplace-toast">{toast}</div>}
      <div className="marketplace-head">
        <h2>Marketplace</h2>
        <div className="marketplace-search">
          <Search size={13} />
          <input
            type="text"
            placeholder="Søg apps…"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
          {query && (
            <button type="button" aria-label="Ryd søgning" onClick={() => setQuery('')}><X size={13} /></button>
          )}
        </div>
      </div>

      {connected.length > 0 && (
        <>
          <div className="marketplace-label">Forbundet · {connected.length}</div>
          <div className="marketplace-grid">
            {connected.map((c) => (
              <ConnectorCard key={c.id} c={c} busy={busy === c.id} onConnect={onConnect} onToggle={onToggle} onDelete={onDelete} />
            ))}
          </div>
        </>
      )}

      <div className="marketplace-label">Alle connectors</div>
      <div className="marketplace-grid">
        {rest.map((c) => (
          <ConnectorCard key={c.id} c={c} busy={busy === c.id} onConnect={onConnect} onToggle={onToggle} onDelete={onDelete} />
        ))}
        {rest.length === 0 && connected.length === 0 && soon.length === 0 && (
          <div className="marketplace-empty">Ingen connectors matcher.</div>
        )}
      </div>

      {soon.length > 0 && (
        <>
          <div className="marketplace-label">Kommer snart · {soon.length}</div>
          <div className="marketplace-grid">
            {soon.map((c) => (
              <ConnectorCard key={c.id} c={c} busy={false} onConnect={onConnect} onToggle={onToggle} onDelete={onDelete} />
            ))}
          </div>
        </>
      )}
    </div>
  )
}

function ConnectorCard({
  c, busy, onConnect, onToggle, onDelete,
}: {
  c: Connector
  busy: boolean
  onConnect: (c: Connector) => void
  onToggle: (c: Connector) => void
  onDelete: (c: Connector) => void
}) {
  const [menu, setMenu] = useState(false)
  const [confirm, setConfirm] = useState(false)
  const Icon = connectorIcon(c.icon)
  const isSoon = c.status === 'coming_soon'

  useEffect(() => {
    if (!menu) return
    const close = () => { setMenu(false); setConfirm(false) }
    window.addEventListener('click', close)
    return () => window.removeEventListener('click', close)
  }, [menu])

  const statusPill = isSoon
    ? <span className="pill soon">Kommer snart</span>
    : c.kind === 'local'
      ? <span className="pill active">Aktiv</span>
      : c.connected
        ? <span className="pill connected">● forbundet</span>
        : (
          <button type="button" className="pill connect" disabled={busy} onClick={() => onConnect(c)}>
            {busy ? 'Forbinder…' : 'Forbind'}
          </button>
        )

  return (
    <div className={`connector-card ${c.connected ? 'is-connected' : ''} ${!c.enabled ? 'is-disabled' : ''} ${isSoon ? 'is-soon' : ''}`}>
      <div className="connector-icon"><Icon size={18} /></div>
      <div className="connector-body">
        <div className="connector-name">{c.name}</div>
        <div className="connector-desc">{c.desc}</div>
        {c.kind === 'oauth' && c.scopes.length > 0 && (
          <div className="connector-scopes">beder om: {c.scopes.join(', ')}</div>
        )}
      </div>
      <div className="connector-actions">
        {statusPill}
        {!isSoon && (c.connected || c.kind === 'local') && (
          <div className="connector-menu-anchor" onClick={(e) => e.stopPropagation()}>
            <button type="button" aria-label="Mere" onClick={() => { setMenu((m) => !m); setConfirm(false) }}>
              <MoreHorizontal size={15} />
            </button>
            {menu && (
              <div className="connector-menu">
                <button type="button" onClick={() => { setMenu(false); onToggle(c) }}>
                  {c.enabled ? 'Slå fra' : 'Slå til'}
                </button>
                {c.kind === 'oauth' && (
                  <button type="button" className="danger" onClick={() => {
                    if (!confirm) { setConfirm(true); return }
                    setMenu(false); onDelete(c)
                  }}>
                    {confirm ? 'Sikker? Slet token' : 'Afbryd & slet'}
                  </button>
                )}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
