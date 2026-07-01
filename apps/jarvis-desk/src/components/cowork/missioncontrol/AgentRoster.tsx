import type { McAgent } from '../../../lib/missionControlApi'
import { StatusChip } from './StatusChip'

/** Agent-roster: hvert kort = én agent med status + mål + token-forbrug. "Opfører mine
 *  baggrunds-agenter sig?" i ét blik. Owner-only (kaldes kun for owner i MC-containeren). */
export function AgentRoster({ agents }: { agents: McAgent[] }) {
  if (agents.length === 0) {
    return <div className="cowork-empty">Ingen aktive agenter</div>
  }
  return (
    <div className="mc-agents">
      {agents.map((a) => (
        <div key={a.agent_id} className="mc-agent-card">
          <div className="mc-agent-top">
            <span className="mc-agent-name">{a.name || a.role || a.agent_id.slice(0, 12)}</span>
            <StatusChip status={a.status} />
          </div>
          {a.role && <div className="mc-agent-role">{a.role}{a.kind ? ` · ${a.kind}` : ''}</div>}
          {a.goal && <div className="mc-agent-goal">{a.goal}</div>}
          <div className="mc-agent-stats">
            {typeof a.tokens_burned === 'number' && <span>{fmtNum(a.tokens_burned)} tok</span>}
            {typeof a.run_count === 'number' && <span>{a.run_count} runs</span>}
            {typeof a.tool_call_count === 'number' && <span>{a.tool_call_count} tools</span>}
          </div>
        </div>
      ))}
    </div>
  )
}

function fmtNum(n: number): string {
  if (n >= 1000) return `${(n / 1000).toFixed(1)}k`
  return String(n)
}
