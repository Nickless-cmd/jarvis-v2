import { useCallback, useEffect, useState } from 'react'
import type { ApiConfig } from '../../lib/api'
import {
  agentHandling, getAgentDetalje, sendTilAgent,
  type AgentDetail,
} from '../../lib/agentPoolApi'
import type { AgentReference } from '../../lib/environmentEvidence'

const ACTIVE_STATUSES = new Set(['active', 'queued', 'starting', 'waiting'])

function tid(value?: string | null): string {
  if (!value) return '–'
  const date = new Date(value)
  return Number.isNaN(date.getTime())
    ? String(value).slice(0, 16)
    : date.toLocaleString('da-DK', {
      day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit',
    })
}

function statusErAktiv(status?: string): boolean {
  return ACTIVE_STATUSES.has(String(status || '').toLowerCase())
}

export function AgentInspector({
  config, agent, canMessage, onChanged,
}: {
  config: ApiConfig
  agent: AgentReference
  canMessage: boolean
  onChanged?: () => void | Promise<void>
}) {
  const [detail, setDetail] = useState<AgentDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [busy, setBusy] = useState(false)
  const [draft, setDraft] = useState('')
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')

  const load = useCallback(async (background = false) => {
    if (background) setRefreshing(true)
    else setLoading(true)
    try {
      const value = await getAgentDetalje(config, agent.agentId)
      setDetail(value)
      setError('')
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Agentdetaljen kunne ikke hentes')
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }, [agent.agentId, config])

  useEffect(() => { void load() }, [load])

  useEffect(() => {
    if (!statusErAktiv(detail?.status)) return
    const interval = window.setInterval(() => {
      if (!document.hidden) void load(true)
    }, 3000)
    return () => window.clearInterval(interval)
  }, [detail?.status, load])

  const runAction = async (action: 'cancel' | 'suspend' | 'resume' | 'expire') => {
    setBusy(true)
    setError('')
    setNotice('')
    try {
      await agentHandling(config, agent.agentId, action)
      setNotice(action === 'cancel' ? 'Agenten er stoppet'
        : action === 'expire' ? 'Agenten er lukket som udløbet'
          : action === 'suspend' ? 'Markeret som pauset i databasen'
            : 'Agenten er sat i gang igen')
      await load(true)
      await onChanged?.()
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Handlingen fejlede')
    } finally {
      setBusy(false)
    }
  }

  const send = async () => {
    const message = draft.trim()
    if (!message || busy) return
    setBusy(true)
    setError('')
    setNotice('')
    try {
      await sendTilAgent(config, agent.agentId, message)
      setDraft('')
      setNotice('Beskeden er lagt i agentens tråd')
      await load(true)
      await onChanged?.()
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Beskeden kunne ikke sendes')
    } finally {
      setBusy(false)
    }
  }

  const status = detail?.status ?? agent.status
  const active = statusErAktiv(status)
  const finished = !!detail && !active
  const runs = detail?.runs ?? []
  const messages = detail?.messages ?? []

  return (
    <div className="inspector-body agent-inspector">
      <section className="inspector-section">
        <div className="inspector-kicker">Agent</div>
        <div className="agent-inspector-role">{detail?.role || agent.role || 'Agent'}</div>
        <div className="agent-inspector-goal">{detail?.goal || agent.goal || 'Intet mål registreret'}</div>
        <dl className="inspector-facts">
          <div><dt>ID</dt><dd className="inspector-mono">{agent.agentId}</dd></div>
          <div><dt>Status</dt><dd className={status === 'failed' ? 'agent-status-error' : ''}>{status || 'ukendt'}</dd></div>
          {detail?.model && <div><dt>Model</dt><dd>{detail.model}</dd></div>}
          <div><dt>Tokens</dt><dd>{Number(detail?.tokens_burned ?? detail?.tokens ?? 0).toLocaleString('da-DK')}</dd></div>
        </dl>
        {refreshing && <div className="agent-refreshing">Opdaterer…</div>}
      </section>

      {active && (
        <section className="inspector-section">
          <div className="inspector-kicker">Kontrol</div>
          <div className="agent-actions">
            <button type="button" disabled={busy} onClick={() => void runAction('cancel')}>Stop</button>
            <button type="button" disabled={busy} onClick={() => void runAction('suspend')}>Marker pauset</button>
            <button type="button" disabled={busy} onClick={() => void runAction('resume')}>Genoptag</button>
            <button type="button" disabled={busy} onClick={() => void runAction('expire')}>Luk som udløbet</button>
          </div>
        </section>
      )}

      {canMessage && active && (
        <section className="inspector-section">
          <div className="inspector-kicker">Besked</div>
          <div className="agent-composer">
            <input
              aria-label="Besked til agenten"
              value={draft}
              onChange={(event) => setDraft(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === 'Enter' && !event.shiftKey) void send()
              }}
              placeholder="Send en besked til agenten"
            />
            <button type="button" disabled={busy || !draft.trim()} onClick={() => void send()}>Send</button>
          </div>
        </section>
      )}

      {finished && canMessage && (
        <div className="agent-finished">Agenten er afsluttet og kan ikke modtage beskeder.</div>
      )}
      {error && <div className="agent-feedback is-error" role="alert">{error}</div>}
      {notice && <div className="agent-feedback">{notice}</div>}

      <section className="inspector-section">
        <div className="inspector-kicker">Kørsler</div>
        {loading && !detail ? <div className="inspector-empty">Henter…</div> : (
          <div className="agent-run-list">
            {runs.map((run) => (
              <article key={run.run_id ?? `${run.started_at}-${run.status}`}>
                <div><strong>{run.status || 'ukendt'}</strong><span>{tid(run.started_at)}</span></div>
                <p>{run.output_summary || run.failure_reason || run.input_summary || 'Intet resumé'}</p>
              </article>
            ))}
            {!runs.length && <div className="inspector-empty">Ingen kørsler.</div>}
          </div>
        )}
      </section>

      <section className="inspector-section">
        <div className="inspector-kicker">Beskeder</div>
        <div className="agent-message-list">
          {messages.slice(-20).map((message, index) => (
            <article key={message.message_id ?? index}>
              <div><strong>{message.role || message.direction || 'besked'}</strong><span>{tid(message.created_at)}</span></div>
              <p>{message.content}</p>
            </article>
          ))}
          {!messages.length && <div className="inspector-empty">Ingen beskeder.</div>}
        </div>
      </section>
    </div>
  )
}
