import { useRef, useState } from 'react'
import type { ApiConfig } from '../../lib/api'
import {
  bucketLabel, erKontraktAaben, kontraktBesked, kontraktLuk, kontraktOpfoelgning, kontraktStop,
  kontraktVarighed, kvitteringTekst, laesArtefakt,
  type ArtifactContent, type ContractDetail, type ContractReceipt,
} from '../../lib/agentContractApi'
import '../../styles/agent-contract.css'

function tid(value?: string | null): string {
  if (!value) return '–'
  const date = new Date(value)
  return Number.isNaN(date.getTime())
    ? String(value).slice(0, 16)
    : date.toLocaleString('da-DK', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' })
}

/** Hvad vi FAKTISK ved om effekten, afledt af projektionen — aldrig af kvitteringen. */
function bekraeftet(kind: ContractReceipt['kind'], d: ContractDetail): boolean {
  if (kind === 'stop') return d.agent.assignment_status === 'cancelled'
  if (kind === 'close') return d.agent.lifecycle_status === 'closed'
  return false          // en besked er aldrig bevist leveret; en opfølgning bekræftes af et nyt assignment, ikke her
}

const ARTEFAKT_FEJL: Record<string, string> = {
  NOT_FOUND: 'Artefakten findes ikke for dig.',
  MISSING: 'Filen mangler på disken — outputtet er ikke tilgængeligt.',
  CORRUPT: 'Filen er beskadiget (checksum passer ikke) — vises ikke.',
  EXPIRED: 'Artefakten er udløbet (retention) og kan ikke længere hentes.',
}

/** Kontrakt-delen af AgentInspector: træ, mål, target, runstatus, heartbeat, omkostning, rute, fejlårsag,
 *  artefakter og styring. Alt kommer fra ÉN projektion (`/agents/contract/agents/{id}`) — status udledes
 *  aldrig af tekst, og en kvittering siger «accepteret», ikke «leveret»/«stoppet». */
export function AgentContractSection({
  config, detail, canMessage, onChanged,
}: {
  config: ApiConfig
  detail: ContractDetail
  canMessage: boolean
  onChanged: () => void | Promise<void>
}) {
  const a = detail.agent
  const [busy, setBusy] = useState(false)
  const [draft, setDraft] = useState('')
  const [followup, setFollowup] = useState('')
  const [error, setError] = useState('')
  const [receipt, setReceipt] = useState<ContractReceipt | null>(null)
  const [artifact, setArtifact] = useState<{ name: string; out: ArtifactContent } | null>(null)
  const nøgle = useRef('')

  const open = erKontraktAaben(a)
  const canFollowUp = !open && a.lifecycle_status !== 'closing' && a.lifecycle_status !== 'closed'

  const run = async (fn: () => Promise<{ receipt: ContractReceipt }>, after?: () => void) => {
    setBusy(true); setError('')
    try {
      const out = await fn()
      setReceipt(out.receipt)
      after?.()
      await onChanged()
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Handlingen fejlede')
    } finally { setBusy(false) }
  }

  const aabn = async (runId: string, name: string) => {
    setError('')
    try {
      setArtifact({ name, out: await laesArtefakt(config, a.agent_id, runId, name) })
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Artefakten kunne ikke hentes')
    }
  }

  return (
    <>
      <section className="inspector-section ac-section" data-testid="ac-status">
        <div className="inspector-kicker">Kontrakt</div>
        <dl className="inspector-facts">
          <div>
            <dt>Status</dt>
            <dd className={a.attention ? 'ac-attention' : ''} data-bucket={a.bucket}>
              {bucketLabel(a.bucket)}{a.attention ? ' · kræver opmærksomhed' : ''}
            </dd>
          </div>
          {a.reason && <div><dt>Hvorfor</dt><dd>{a.reason}</dd></div>}
          <div><dt>Target</dt><dd>{a.target === 'runtime-container' ? 'container' : a.target}</dd></div>
          <div><dt>Opgave</dt><dd className="inspector-mono">{a.assignment_id || '–'} ({a.assignment_status || '–'})</dd></div>
          <div><dt>Forsøg</dt><dd>{a.attempts}{a.run_status ? ` · seneste run: ${a.run_status}` : ''}</dd></div>
          <div>
            <dt>Heartbeat</dt>
            <dd className={a.heartbeat?.state === 'expired' ? 'ac-attention' : ''}>
              {a.heartbeat ? `${tid(a.heartbeat.at)} · ${a.heartbeat.state === 'ok' ? 'levende' : 'lease udløbet'}` : 'ingen'}
            </dd>
          </div>
          {a.duration_s !== null && <div><dt>Varighed</dt><dd>{kontraktVarighed(a.duration_s)}</dd></div>}
          <div><dt>Tokens</dt><dd>{a.tokens.toLocaleString('da-DK')}</dd></div>
          <div>
            <dt>Omkostning</dt>
            <dd>{a.cost_usd === null ? 'ikke meldt' : a.cost_usd.toLocaleString('da-DK', { style: 'currency', currency: 'USD', maximumFractionDigits: 4 })}</dd>
          </div>
          {a.route && <div><dt>Rute</dt><dd>{a.route.route_source} · {a.route.provider}/{a.route.model}</dd></div>}
          {a.parent_agent_id && <div><dt>Forælder</dt><dd className="inspector-mono">{a.parent_agent_id}</dd></div>}
          {detail.children.length > 0 && (
            <div><dt>Børn</dt><dd className="inspector-mono">{detail.children.join(', ')}</dd></div>
          )}
          <div><dt>Livscyklus</dt><dd>{a.lifecycle_status || '–'}</dd></div>
        </dl>
        {a.error && (a.error.code || a.error.reason) && (
          <div className="agent-last-error" role="status" data-testid="ac-error">
            Fejlårsag: {[a.error.phase && `fase ${a.error.phase}`, a.error.code, a.error.reason].filter(Boolean).join(' · ')}
          </div>
        )}
        {a.bucket === 'outcome_unknown' && (
          <div className="agent-last-error" role="alert">
            Udfaldet er ukendt. Handlingen kan allerede være udført — den gentages ikke automatisk.
          </div>
        )}
        {detail.approvals.filter((p) => p.status === 'pending').map((p) => (
          <div className="ac-approval" key={p.approval_id}>
            <strong>Venter på godkendelse:</strong> <code>{p.safe_view}</code>
            <span className="ac-hint"> Afgøres under «Venter på dig» i notifikationerne.</span>
          </div>
        ))}
      </section>

      {canMessage && (
        <section className="inspector-section ac-section">
          <div className="inspector-kicker">Styring</div>
          {!detail.capability.enabled && (
            <div className="ac-hint">Agent-kontrakten er slukket — nye handlinger afvises ({detail.capability.reason}).</div>
          )}
          {open && (
            <div className="agent-actions">
              <button type="button" disabled={busy} onClick={() => void run(() => kontraktStop(config, a.agent_id))}>Stop</button>
              <button type="button" disabled={busy || a.lifecycle_status === 'closing'}
                      onClick={() => void run(() => kontraktLuk(config, a.agent_id))}>Luk agent</button>
            </div>
          )}
          {open && (
            <div className="agent-composer">
              <input aria-label="Besked til agenten" value={draft} placeholder="Send en besked til agenten"
                     onChange={(e) => setDraft(e.target.value)}
                     onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey && draft.trim() && !busy) void run(() => kontraktBesked(config, a.agent_id, draft.trim()), () => setDraft('')) }} />
              <button type="button" disabled={busy || !draft.trim()}
                      onClick={() => void run(() => kontraktBesked(config, a.agent_id, draft.trim()), () => setDraft(''))}>Send</button>
            </div>
          )}
          {canFollowUp && (
            <div className="agent-composer">
              <input aria-label="Opfølgning til agenten" value={followup} placeholder="Ny opgave til samme agent"
                     onChange={(e) => { if (!followup) nøgle.current = `desk-${crypto.randomUUID()}`; setFollowup(e.target.value) }} />
              <button type="button" disabled={busy || !followup.trim()}
                      onClick={() => void run(() => kontraktOpfoelgning(config, a.agent_id, followup.trim(), nøgle.current), () => setFollowup(''))}>Start opfølgning</button>
            </div>
          )}
          {!open && !canFollowUp && <div className="agent-finished">Agenten er {a.lifecycle_status === 'closing' ? 'ved at lukke' : 'lukket'} og tager ikke imod nye opgaver.</div>}
          {receipt && (
            <div className="ac-receipt" role="status" data-testid="ac-receipt">
              <div>{kvitteringTekst(receipt)}</div>
              <div className="ac-hint">
                Accepteret: {receipt.accepted ? 'ja' : 'nej'} · Registreret i databasen: {bekraeftet(receipt.kind, detail) ? 'ja' : 'nej'}
                {receipt.kind === 'stop' && bekraeftet(receipt.kind, detail) ? ' (assignmentet er afbrudt — workerens faktiske stop måles ikke her)' : ''}
              </div>
            </div>
          )}
          {error && <div className="agent-feedback is-error" role="alert">{error}</div>}
        </section>
      )}

      <section className="inspector-section ac-section">
        <div className="inspector-kicker">Artefakter</div>
        {detail.artifacts.length === 0 ? <div className="inspector-empty">Ingen artefakter endnu.</div> : (
          <ul className="ac-artifacts">
            {detail.artifacts.map((f) => (
              <li key={`${f.run_id}/${f.name}`}>
                <button type="button" className="ac-link" onClick={() => void aabn(f.run_id, f.name)}>{f.name}</button>
                <span className="ac-hint"> forsøg {f.attempt_no ?? '?'} · {f.size.toLocaleString('da-DK')} B{f.status === 'partial' ? ' · delvist' : ''}</span>
              </li>
            ))}
          </ul>
        )}
        {artifact && (
          <div className="ac-artifact-view" data-testid="ac-artifact">
            <div className="ac-hint">{artifact.name}{artifact.out.partial ? ' (delvist output)' : ''}</div>
            {artifact.out.status === 'ok'
              ? <pre>{artifact.out.content}{artifact.out.truncated ? '\n… (afkortet)' : ''}</pre>
              : <div className="agent-feedback is-error" role="alert">{ARTEFAKT_FEJL[artifact.out.status] ?? artifact.out.status}</div>}
          </div>
        )}
      </section>

      <section className="inspector-section ac-section">
        <div className="inspector-kicker">Opgaver og forsøg</div>
        <div className="agent-run-list">
          {detail.assignments.map((x) => (
            <article key={x.assignment_id}>
              <div><strong>{x.status}</strong><span>{tid(x.created_at)}</span></div>
              <p>{x.goal}</p>
              {x.outcome.summary && <p className="ac-hint">Resumé: {x.outcome.summary}</p>}
            </article>
          ))}
          {detail.runs.map((r) => (
            <article key={r.run_id}>
              <div><strong>forsøg {r.attempt_no}: {r.status}</strong><span>{tid(r.started_at)}</span></div>
              {(r.error_code || r.failure_reason) && <p>{[r.error_phase, r.error_code, r.failure_reason].filter(Boolean).join(' · ')}</p>}
              <div className="agent-run-meta">
                {r.model && <span>{r.model}</span>}
                <span>ind {r.input_tokens.toLocaleString('da-DK')}</span>
                <span>ud {r.output_tokens.toLocaleString('da-DK')}</span>
              </div>
            </article>
          ))}
          {!detail.assignments.length && <div className="inspector-empty">Ingen opgaver.</div>}
        </div>
      </section>

      {detail.tool_calls.length > 0 && (
        <section className="inspector-section ac-section">
          <div className="inspector-kicker">Værktøjskald</div>
          <ul className="ac-artifacts">
            {detail.tool_calls.map((t) => (
              <li key={t.tool_call_id}><span className="inspector-mono">{t.tool_name}</span>
                <span className="ac-hint"> {t.status}{t.finished_at ? '' : ' · ikke afsluttet'}</span></li>
            ))}
          </ul>
        </section>
      )}

      <section className="inspector-section ac-section">
        <div className="inspector-kicker">Beskeder</div>
        <div className="agent-message-list">
          {detail.messages.map((m) => (
            <article key={m.message_id}>
              <div><strong>{m.direction}</strong><span>{tid(m.created_at)}</span></div>
              <p>{m.content}</p>
            </article>
          ))}
          {!detail.messages.length && <div className="inspector-empty">Ingen beskeder.</div>}
        </div>
      </section>
    </>
  )
}
