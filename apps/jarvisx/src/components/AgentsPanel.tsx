import { Bot, X, RefreshCw, Loader2, CheckCircle2, AlertCircle, Pause } from 'lucide-react'
import { useMcEndpoint } from '../lib/useMcEndpoint'

interface Agent {
  agent_id: string
  parent_agent_id?: string
  council_id?: string
  kind?: string
  role?: string
  goal?: string
  status?: string
  lane?: string
  provider?: string
  model?: string
  created_at?: string
}

interface AgentsResp {
  agents: Agent[]
  summary?: { active?: number; total?: number; failed?: number }
}

interface Props {
  apiBaseUrl: string
  onClose: () => void
}

/**
 * Side-panel showing all sub-agents Jarvis has dispatched. Each agent
 * is a row with goal, role, status (running/completed/failed/blocked),
 * and a model+lane footnote. Live polling every 5s.
 *
 * In Claude Code subagents are invisible until they reply — JarvisX
 * makes them legible: you see the council deliberating, the swarm
 * working, the dispatched claude-code agent crunching, in real time.
 */
export function AgentsPanel({ apiBaseUrl, onClose }: Props) {
  const { data, loading, error, refresh } = useMcEndpoint<AgentsResp>(
    apiBaseUrl,
    '/mc/agents',
    5000,
  )

  // Filter to interesting agents — running first, then recently active
  const all = data?.agents ?? []
  const live = all.filter(
    (a) => a.status === 'active' || a.status === 'running' || a.status === 'spawning',
  )
  const blocked = all.filter((a) => a.status === 'blocked' || a.status === 'waiting')
  const recent = all
    .filter((a) => !live.includes(a) && !blocked.includes(a))
    .slice(0, 30)

  return (
    <aside className="flex h-full w-[380px] flex-shrink-0 flex-col border-l border-line bg-bg1">
      <header className="flex flex-shrink-0 items-center gap-2 border-b border-line px-3 py-2">
        <Bot size={12} className="text-accent" />
        <div className="min-w-0 flex-1">
          <div className="text-[11px] font-semibold">Sub-agents</div>
          <div className="font-mono text-[9px] text-fg3">
            {live.length} live · {blocked.length} blocked · {all.length} total
          </div>
        </div>
        <button
          onClick={refresh}
          title="Refresh"
          className="flex h-6 w-6 items-center justify-center rounded text-fg3 hover:bg-bg2 hover:text-accent"
        >
          <RefreshCw size={11} />
        </button>
        <button
          onClick={onClose}
          className="flex h-6 w-6 items-center justify-center rounded text-fg3 hover:bg-bg2 hover:text-fg"
        >
          <X size={11} />
        </button>
      </header>

      <div className="min-h-0 flex-1 overflow-y-auto">
        {loading && !data && (
          <div className="px-3 py-3 text-[10px] text-fg3">loading agents…</div>
        )}
        {error && (
          <div className="m-2 rounded-md border border-danger/30 bg-danger/10 px-2 py-1.5 font-mono text-[10px] text-danger">
            {error}
          </div>
        )}
        {data && all.length === 0 && (
          <div className="px-3 py-6 text-center text-[11px] text-fg3">
            No agents spawned yet. Jarvis dispatches them via{' '}
            <code className="font-mono text-accent">dispatch_to_claude_code</code>{' '}
            or council runs.
          </div>
        )}

        {live.length > 0 && (
          <Section title={`Live · ${live.length}`}>
            {live.map((a) => (
              <AgentRow key={a.agent_id} agent={a} />
            ))}
          </Section>
        )}
        {blocked.length > 0 && (
          <Section title={`Waiting · ${blocked.length}`}>
            {blocked.map((a) => (
              <AgentRow key={a.agent_id} agent={a} />
            ))}
          </Section>
        )}
        {recent.length > 0 && (
          <Section title={`Recent · ${recent.length}`}>
            {recent.map((a) => (
              <AgentRow key={a.agent_id} agent={a} compact />
            ))}
          </Section>
        )}
      </div>
    </aside>
  )
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div>
      <div className="sticky top-0 border-b border-line/40 bg-bg1 px-3 py-1.5 text-[9px] font-semibold uppercase tracking-wider text-fg3 backdrop-blur">
        {title}
      </div>
      {children}
    </div>
  )
}

function AgentRow({ agent, compact }: { agent: Agent; compact?: boolean }) {
  const status = agent.status || 'unknown'
  const Icon =
    status === 'completed'
      ? CheckCircle2
      : status === 'failed' || status === 'cancelled'
      ? AlertCircle
      : status === 'blocked' || status === 'waiting'
      ? Pause
      : Loader2
  const color =
    status === 'completed'
      ? '#3fb950'
      : status === 'failed' || status === 'cancelled'
      ? '#f85149'
      : status === 'blocked' || status === 'waiting'
      ? '#d4963a'
      : '#5ab8a0'
  const isRunning = status === 'active' || status === 'running' || status === 'spawning'

  return (
    <div
      className="border-b border-line/30 px-3 py-2"
      title={`${agent.agent_id}\n${agent.goal || '(no goal)'}`}
    >
      <div className="flex items-start gap-2">
        <Icon
          size={11}
          color={color}
          className={`mt-0.5 flex-shrink-0 ${isRunning ? 'animate-spin' : ''}`}
        />
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <span className="text-[10px] font-semibold uppercase tracking-wider" style={{ color }}>
              {agent.role || agent.kind || 'agent'}
            </span>
            <span className="font-mono text-[9px] text-fg3">{status}</span>
          </div>
          {agent.goal && !compact && (
            <div className="mt-0.5 line-clamp-2 text-[11px] leading-snug text-fg2">
              {agent.goal}
            </div>
          )}
          {compact && agent.goal && (
            <div className="mt-0.5 truncate text-[10px] text-fg3">{agent.goal}</div>
          )}
          <div className="mt-1 font-mono text-[9px] text-fg3 opacity-60">
            {agent.lane && `${agent.lane} · `}
            {agent.provider && agent.model
              ? `${agent.provider}/${agent.model.split('/').slice(-1)[0]}`
              : agent.provider || agent.model || ''}
          </div>
        </div>
      </div>
    </div>
  )
}
