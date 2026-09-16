import { useCallback, useEffect, useRef, useState } from 'react'
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

  // Hvilken agent er panelet PAA lige nu. Uden den skriver et sent svar fra
  // den forrige agent sig ind under den nyes id: klik agent 1, klik straks
  // agent 2 — overskriften siger 2, koerslerne er 1's. Og lander A's svar
  // efter B's, vinder A permanent.
  const aktuelRef = useRef(agent.agentId)

  const load = useCallback(async (background = false) => {
    const bedtOm = agent.agentId
    if (background) setRefreshing(true)
    else setLoading(true)
    try {
      const value = await getAgentDetalje(config, bedtOm)
      if (aktuelRef.current !== bedtOm) return      // panelet er gaaet videre
      setDetail(value)
      setError('')
    } catch (reason) {
      if (aktuelRef.current !== bedtOm) return
      setError(reason instanceof Error ? reason.message : 'Agentdetaljen kunne ikke hentes')
    } finally {
      if (aktuelRef.current === bedtOm) {
        setLoading(false)
        setRefreshing(false)
      }
    }
  }, [agent.agentId, config])

  useEffect(() => {
    // Ny agent = tom tavle. Ellers staar den forriges data under det nye id,
    // mens hentningen loeber.
    aktuelRef.current = agent.agentId
    setDetail(null)
    setError('')
    setNotice('')
  }, [agent.agentId])

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
  // Summér prisen fra koerslerne. null (ikke 0) naar INGEN koersel har et
  // beloeb — «ingen data» og «gratis» er ikke det samme.
  const prisRaekker = runs.filter((r) => typeof r.cost_usd === 'number')
  const pris = prisRaekker.length ? prisRaekker.reduce((sum, r) => sum + (r.cost_usd ?? 0), 0) : null
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
          {/* Pris og antal koersler stod i Agent Pool-overlayet foer refaktoren
              og forsvandt med den. «Se alt» var hele pointen med den flade. */}
          {detail && <div><dt>Kørsler</dt><dd>{runs.length.toLocaleString('da-DK')}</dd></div>}
          {pris !== null && (
            <div><dt>Pris</dt><dd>{pris.toLocaleString('da-DK', { style: 'currency', currency: 'USD', maximumFractionDigits: 4 })}</dd></div>
          )}
          {/* «0» under hentningen er ikke til at skelne fra en agent der intet
              har brugt — og tokens_burned er NOT NULL DEFAULT 0 i skemaet, saa
              nul ER aegte data naar det foerst er hentet. */}
          <div><dt>Tokens</dt><dd>{detail
            ? Number(detail.tokens_burned ?? detail.tokens ?? 0).toLocaleString('da-DK')
            : '—'}</dd></div>
        </dl>
        {detail?.last_error && (
          // Var med i Agent Pool-overlayet foer refaktoren og forsvandt uden
          // erstatning. Feltet er typet i agentPoolApi — det blev bare aldrig
          // vist. En fejlet agent uden sin fejl er ikke til megen nytte.
          <div className="agent-last-error" role="status">Fejl: {detail.last_error}</div>
        )}
        {refreshing && <div className="agent-refreshing">Opdaterer…</div>}
      </section>

      {/* canMessage gater BEGGE dele. Composeren gjorde det allerede; knapperne
          gjorde ikke — og de er de farligste af de to: Stop og «Luk som
          udloebet» afbryder en koersel, mens en besked blot lander i en koe. */}
      {active && canMessage && (
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
      {error && (
        <div className="agent-feedback is-error" role="alert">
          {error}
          {/* Pollingen gater paa detail?.status. Fejler den FOERSTE hentning,
              er detail null, og saa poller ingenting — uden den her knap er
              panelet en blindgyde til man lukker og aabner det igen. */}
          <button type="button" className="agent-retry" onClick={() => void load()} disabled={loading}>
            Prøv igen
          </button>
        </div>
      )}
      {notice && <div className="agent-feedback">{notice}</div>}

      <section className="inspector-section">
        <div className="inspector-kicker">Kørsler</div>
        {loading && !detail ? <div className="inspector-empty">Henter…</div> : (
          <div className="agent-run-list">
            {runs.map((run) => (
              <article key={run.run_id ?? `${run.started_at}-${run.status}`}>
                <div><strong>{run.status || 'ukendt'}</strong><span>{tid(run.started_at)}</span></div>
                <p>{run.output_summary || run.failure_reason || run.input_summary || 'Intet resumé'}</p>
                {(run.model || typeof run.input_tokens === 'number' || typeof run.output_tokens === 'number') && (
                  <div className="agent-run-meta">
                    {run.model && <span>{run.model}</span>}
                    {typeof run.input_tokens === 'number' && <span>ind {run.input_tokens.toLocaleString('da-DK')}</span>}
                    {typeof run.output_tokens === 'number' && <span>ud {run.output_tokens.toLocaleString('da-DK')}</span>}
                  </div>
                )}
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
