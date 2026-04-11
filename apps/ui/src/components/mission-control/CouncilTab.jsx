import { Crown, Users, MessageSquare } from 'lucide-react'
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

const COUNCIL_MEMBERS_PLACEHOLDER = [
  { id: 'strategist', name: 'Strategen', role: 'Long-horizon planning and goal coherence', status: 'idle' },
  { id: 'critic', name: 'Kritikeren', role: 'Challenges assumptions, flags blind spots', status: 'idle' },
  { id: 'ethicist', name: 'Etikeren', role: 'Values alignment and boundary enforcement', status: 'idle' },
  { id: 'executor', name: 'Eksekvøren', role: 'Breaks down tasks, tracks progress', status: 'idle' },
]

const STATUS_COLOR = { active: T.green, idle: T.text3, speaking: T.accent }

export function CouncilTab() {
  return (
    <div style={s({ display: 'flex', flexDirection: 'column', gap: 16, maxWidth: 900 })}>

      {/* Header */}
      <div style={s({ display: 'flex', alignItems: 'center', gap: 10 })}>
        <Crown size={16} color={T.accent} />
        <span style={s({ fontSize: 14, fontWeight: 500, color: T.text1 })}>Council</span>
        <span
          style={s({
            ...mono, fontSize: 9, padding: '2px 8px', borderRadius: 10,
            background: `${T.amber}18`, border: `1px solid ${T.amber}35`, color: T.amber,
          })}
        >
          UNDER DESIGN
        </span>
      </div>

      {/* Members */}
      <PlaceholderSection
        title="Council Members"
        description="Specialised perspectives that advise Jarvis — each runs as a cheap-lane subagent when convened"
      >
        <div style={s({ display: 'flex', flexDirection: 'column', gap: 8 })}>
          {COUNCIL_MEMBERS_PLACEHOLDER.map((member) => {
            const color = STATUS_COLOR[member.status] || T.text3
            return (
              <div
                key={member.id}
                style={s({
                  display: 'flex', alignItems: 'center', gap: 12,
                  padding: '10px 12px', borderRadius: 8,
                  background: T.bgOverlay, border: `1px solid ${T.border0}`,
                })}
              >
                <div
                  style={s({
                    width: 7, height: 7, borderRadius: '50%',
                    background: color,
                    boxShadow: member.status !== 'idle' ? `0 0 6px ${color}` : 'none',
                    flexShrink: 0,
                  })}
                />
                <div style={s({ flex: 1, minWidth: 0 })}>
                  <div style={s({ fontSize: 11, fontWeight: 500, color: T.text1 })}>{member.name}</div>
                  <div style={s({ ...mono, fontSize: 9, color: T.text3, marginTop: 2 })}>{member.role}</div>
                </div>
                <span style={s({ ...mono, fontSize: 9, color })}>{member.status}</span>
              </div>
            )
          })}
        </div>
      </PlaceholderSection>

      {/* Last session */}
      <PlaceholderSection
        title="Last Council Session"
        description="Most recent convening — topic, participants, and outcome"
      >
        <div
          style={s({
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            padding: '24px 0',
          })}
        >
          <div style={s({ textAlign: 'center' })}>
            <MessageSquare size={24} color={T.border1} style={{ marginBottom: 8 }} />
            <div style={s({ ...mono, fontSize: 10, color: T.text3 })}>No council sessions yet</div>
            <div style={s({ ...mono, fontSize: 9, color: T.text3, marginTop: 4 })}>
              Council convening not yet wired into the runtime
            </div>
          </div>
        </div>
      </PlaceholderSection>

    </div>
  )
}
