import { Square, Check } from 'lucide-react'
import type { ReactNode } from 'react'
import {
  bucketLabel, erKontraktAaben, kontraktVarighed,
  type ContractAgentRow, type ContractGroup,
} from '../../lib/agentContractApi'
import '../../styles/agent-contract.css'

/** Rækkerne i Baggrundsjob-panelet for kontrakt-agenter: ÉN logisk række pr. aktivt agentrun (ikke pr.
 *  OS-proces). Klik åbner AgentInspector; Stop går over samme rute og samme rettighedstjek som inspectoren.
 *  Et råd vises som en gruppering af almindelige rækker med medlemsstatus og syntese. */
export function AgentJobRows({
  rows, groups, busyId, onOpen, onStop, onAck,
}: {
  rows: ContractAgentRow[]
  groups: ContractGroup[]
  busyId: string
  onOpen: (row: ContractAgentRow) => void
  onStop: (row: ContractAgentRow) => void
  onAck: (row: ContractAgentRow) => void
}) {
  const rendered = new Set<string>()
  const out: ReactNode[] = []

  const raekke = (r: ContractAgentRow, indent = false) => {
    const aaben = erKontraktAaben(r)
    const fejl = r.error && (r.error.code || r.error.reason)
    return (
      <li key={r.assignment_id || r.agent_id}
          className={`jobs-kort ac-job${r.attention ? ' er-opmaerksomhed' : ''}${indent ? ' i-gruppe' : ''}`}
          data-testid={`ac-job-${r.agent_id}`} data-bucket={r.bucket}>
        <button type="button" className="jobs-kort-tekst ac-job-aaben" onClick={() => onOpen(r)}
                aria-label={`Åbn agent ${r.goal || r.agent_id}`}>
          <span className="jobs-navn" title={`${r.agent_id} · ${r.run_id}`}>{r.goal || r.agent_id}</span>
          <span className="jobs-meta">
            <span className="jobs-kilde">{r.role || 'Agent'}</span>
            <span className="jobs-kilde">{r.target === 'runtime-container' ? 'container' : r.target}</span>
            <span className={`ac-status${r.attention ? ' er-fejl' : ''}`}>{bucketLabel(r.bucket)}</span>
            {r.duration_s !== null && <span className="jobs-tid">{kontraktVarighed(r.duration_s)}</span>}
          </span>
          {(r.reason || fejl) && (
            <span className="jobs-meta ac-aarsag">
              {r.reason}{fejl && r.error?.reason ? ` · ${r.error.reason}` : ''}
            </span>
          )}
        </button>
        <div className="jobs-knapper">
          {aaben && (
            <button type="button" className="jobs-stop" title="Stop agenten"
                    aria-label={`Stop agent ${r.goal || r.agent_id}`} disabled={busyId === r.agent_id}
                    onClick={() => onStop(r)}>
              <Square size={12} />
            </button>
          )}
          {!aaben && r.attention && (
            <button type="button" className="jobs-stop" title="Kvittér"
                    aria-label={`Kvittér ${r.goal || r.agent_id}`} disabled={busyId === r.agent_id}
                    onClick={() => onAck(r)}>
              <Check size={12} />
            </button>
          )}
        </div>
      </li>
    )
  }

  for (const r of rows) {
    if (!r.council_id) { out.push(raekke(r)); continue }
    if (rendered.has(r.council_id)) continue
    rendered.add(r.council_id)
    const g = groups.find((x) => x.council_id === r.council_id)
    const members = rows.filter((x) => x.council_id === r.council_id)
    out.push(
      <li key={`raad-${r.council_id}`} className="ac-raad-hoved" data-testid={`ac-raad-${r.council_id}`}>
        Råd {r.council_id} · {members.length} {members.length === 1 ? 'række' : 'rækker'}
        {g?.synthesis ? ` · syntese: ${bucketLabel(g.synthesis.bucket)}` : ' · syntese: ikke startet'}
      </li>,
    )
    for (const m of members) out.push(raekke(m, true))
  }
  return <ul className="jobs-liste">{out}</ul>
}
