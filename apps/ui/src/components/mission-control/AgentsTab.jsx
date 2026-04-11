import { Bot, Cpu, Zap, Clock } from 'lucide-react'
import { s, T, mono } from '../../shared/theme/tokens'

function PlaceholderSection({ title, description, children }) {
  return (
    <div
      style={s({
        background: T.cardGradient,
        border: `1px solid ${T.border1}`,
        borderRadius: 10,
        padding: '16px 18px',
      })}
    >
      <div style={s({ marginBottom: 12 })}>
        <div style={s({ fontSize: 12, fontWeight: 500, color: T.text1, marginBottom: 4 })}>{title}</div>
        <div style={s({ ...mono, fontSize: 10, color: T.text3 })}>{description}</div>
      </div>
      {children}
    </div>
  )
}

function PoolBar({ label, used = 0, total = 0, color = T.accent }) {
  const pct = total > 0 ? Math.min(1, used / total) : 0
  return (
    <div style={s({ display: 'flex', flexDirection: 'column', gap: 5 })}>
      <div style={s({ display: 'flex', justifyContent: 'space-between', alignItems: 'center' })}>
        <span style={s({ ...mono, fontSize: 10, color: T.text2 })}>{label}</span>
        <span style={s({ ...mono, fontSize: 10, color: T.text3 })}>{used} / {total} active</span>
      </div>
      <div
        style={s({
          height: 6,
          borderRadius: 3,
          background: T.bgOverlay,
          border: `1px solid ${T.border0}`,
          overflow: 'hidden',
        })}
      >
        <div
          style={s({
            height: '100%',
            width: `${pct * 100}%`,
            background: color,
            borderRadius: 3,
            transition: 'width 0.4s ease',
          })}
        />
      </div>
    </div>
  )
}

export function AgentsTab() {
  return (
    <div style={s({ display: 'flex', flexDirection: 'column', gap: 16, maxWidth: 900 })}>

      {/* Header */}
      <div style={s({ display: 'flex', alignItems: 'center', gap: 10 })}>
        <Bot size={16} color={T.accent} />
        <span style={s({ fontSize: 14, fontWeight: 500, color: T.text1 })}>Agents</span>
        <span
          style={s({
            ...mono, fontSize: 9, padding: '2px 8px', borderRadius: 10,
            background: `${T.amber}18`, border: `1px solid ${T.amber}35`, color: T.amber,
          })}
        >
          UNDER DESIGN
        </span>
      </div>

      {/* Cheap lane pool */}
      <PlaceholderSection
        title="Cheap Lane Pool"
        description="Subagent slots powered by fast/cheap models — used for parallel tasks, summarisation, and internal jobs"
      >
        <div style={s({ display: 'flex', flexDirection: 'column', gap: 10 })}>
          <PoolBar label="haiku-4-5  (fast, cheap)" used={0} total={8} color={T.green} />
          <PoolBar label="sonnet-4-6 (mid tier)" used={0} total={4} color={T.accent} />
          <PoolBar label="opus-4-6   (primary)" used={0} total={2} color={`${T.accent}bb`} />
        </div>
      </PlaceholderSection>

      {/* Active agents */}
      <PlaceholderSection
        title="Active Agents"
        description="Agents spawned in this session or still running from previous runs"
      >
        <div
          style={s({
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            padding: '24px 0', color: T.text3,
          })}
        >
          <div style={s({ textAlign: 'center' })}>
            <Cpu size={24} color={T.border1} style={{ marginBottom: 8 }} />
            <div style={s({ ...mono, fontSize: 10 })}>No active agents</div>
            <div style={s({ ...mono, fontSize: 9, color: T.text3, marginTop: 4 })}>
              Architecture in progress — agent spawning not yet wired up
            </div>
          </div>
        </div>
      </PlaceholderSection>

      {/* Recent */}
      <PlaceholderSection
        title="Recent Agents"
        description="Completed or failed agent runs from this session"
      >
        <div
          style={s({
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            padding: '24px 0', color: T.text3,
          })}
        >
          <div style={s({ textAlign: 'center' })}>
            <Clock size={24} color={T.border1} style={{ marginBottom: 8 }} />
            <div style={s({ ...mono, fontSize: 10 })}>No recent agents</div>
          </div>
        </div>
      </PlaceholderSection>

    </div>
  )
}
