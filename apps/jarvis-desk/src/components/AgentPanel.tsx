import { useCallback, useEffect, useState } from 'react'
import { X, Bot, RefreshCw } from 'lucide-react'
import type { ApiConfig } from '../lib/api'
import { getPoolListe, type PoolAgent } from '../lib/agentPoolApi'
import { AgentInspector } from './panel/AgentInspector'
import '../styles/kode-flader.css'

const POLL_MS = 5000

type Visning = 'queued' | 'active' | 'done' | 'failed'
const NAVN: Record<Visning, string> = { queued: 'I kø', active: 'Aktiv', done: 'Færdig', failed: 'Fejlet' }

/** Backendens statusser samles i de fire kontrakt-tilstande. Ukendt status
 *  vises som «Ukendt» i stedet for at gætte — se `visning`. */
export function visning(status?: string): Visning | null {
  switch (String(status ?? '').trim().toLowerCase()) {
    case 'planned': case 'queued': case 'pending': return 'queued'
    case 'active': case 'running': return 'active'
    case 'completed': case 'closed': case 'done': return 'done'
    case 'failed': case 'cancelled': case 'expired': return 'failed'
    default: return null
  }
}

/** Agent-panel: hvilke agenter findes, hvad er deres rolle/status, og vejen til resultatet.
 *  Kilde: `/mc/agent-pool` (samme som cowork-fladen). Resultat/kørsler/beskeder åbnes i
 *  den eksisterende AgentInspector. */
export function AgentPanel({
  config, canMessage, onClose,
}: {
  config: ApiConfig
  canMessage: boolean
  onClose: () => void
}) {
  const [agenter, setAgenter] = useState<PoolAgent[] | null>(null)
  const [fejl, setFejl] = useState('')
  const [valgt, setValgt] = useState('')

  const hent = useCallback(async () => {
    try {
      const r = await getPoolListe(config, { limit: 50 })
      setAgenter(r.agenter ?? [])
      setFejl('')
    } catch (e) {
      setFejl(e instanceof Error && e.message ? e.message : 'Kunne ikke hente agenter')
    }
  }, [config])

  useEffect(() => {
    void hent()
    const id = window.setInterval(() => { void hent() }, POLL_MS)
    return () => window.clearInterval(id)
  }, [hent])

  const aaben = agenter?.find((a) => a.agent_id === valgt)

  return (
    <div className="artifact-panel">
      <div className="artifact-head">
        <Bot size={14} /> <span className="artifact-title">Agenter</span>
        <button type="button" className="artifact-close" aria-label="Opdatér agenter" onClick={() => void hent()}>
          <RefreshCw size={13} />
        </button>
        <button type="button" className="artifact-close" aria-label="Luk panel" onClick={onClose}>
          <X size={15} />
        </button>
      </div>
      <div className="artifact-body">
        {fejl && <div className="artifact-error" role="alert">{fejl}</div>}
        {!fejl && !agenter && <div className="artifact-loading">Henter…</div>}
        {agenter && agenter.length === 0 && <div className="artifact-empty">Ingen agenter endnu.</div>}
        {agenter && agenter.length > 0 && (
          <ul className="agentpanel-liste">
            {agenter.map((a) => {
              const v = visning(a.status)
              return (
                <li key={a.agent_id}>
                  <button type="button" className={`agentpanel-raekke ${a.agent_id === valgt ? 'active' : ''}`}
                    onClick={() => setValgt(a.agent_id === valgt ? '' : a.agent_id)}>
                    <span className="agentpanel-id" title={a.agent_id}>{a.agent_id.slice(0, 12)}</span>
                    <span className="agentpanel-rolle">{a.role || a.kind || '—'}</span>
                    <span className="agentpanel-maal" title={a.goal}>{a.goal || ''}</span>
                    <span className={`agentpanel-status ${v ?? ''}`} title={a.status}>
                      {v ? NAVN[v] : `Ukendt${a.status ? ` (${a.status})` : ''}`}
                    </span>
                  </button>
                </li>
              )
            })}
          </ul>
        )}
        {aaben && (
          <div className="agentpanel-detalje">
            <AgentInspector config={config} canMessage={canMessage}
              agent={{ agentId: aaben.agent_id, role: aaben.role, goal: aaben.goal, status: aaben.status, dispatchToolUseId: '' }}
              onChanged={hent} />
          </div>
        )}
      </div>
    </div>
  )
}
