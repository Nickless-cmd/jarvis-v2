import type { AgentDispatchView, AgentStatus } from '../../lib/coworkApi'

const STATUS_LABEL: Record<AgentStatus, string> = {
  planned: 'planlagt',
  running: 'kører',
  done: 'færdig',
  error: 'fejl',
}

// §19.5: cowork som command center — vis dispatch-plan + agent-status.
export function AgentDispatchPane({ view }: { view: AgentDispatchView | null }) {
  if (!view) {
    return <div className="cowork-empty">Ingen agenter kører</div>
  }
  if (view.mode === 'inline') {
    return <div className="cowork-empty">Inline — ingen dispatch ({view.decision})</div>
  }
  if (view.entries.length === 0) {
    return <div className="cowork-empty">Ingen agenter kører</div>
  }
  const s = view.summary
  return (
    <div className="cowork-agents">
      <div className="cowork-agents-summary">
        {s.total} agenter · {s.running} kører · {s.done} færdige
        {s.error > 0 ? ` · ${s.error} fejl` : ''}
      </div>
      {view.entries.map((e, i) => (
        <div key={`${e.role}-${i}`} className={`cowork-agent cowork-agent-${e.status}`}>
          <span className="cowork-agent-role">{e.role}</span>
          <span className="cowork-agent-status">{STATUS_LABEL[e.status]}</span>
          {e.parallel ? <span className="cowork-agent-parallel">∥</span> : null}
          <div className="cowork-agent-goal">{e.goal}</div>
        </div>
      ))}
    </div>
  )
}
