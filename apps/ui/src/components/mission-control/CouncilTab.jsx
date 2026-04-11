import { useEffect, useMemo, useState } from 'react'
import { Crown, MessageSquare, Users } from 'lucide-react'
import { s, T, mono } from '../../shared/theme/tokens'
import { backend } from '../../lib/adapters'

function Section({ title, description, children }) {
  return (
    <div style={s({ background: T.cardGradient, border: `1px solid ${T.border1}`, borderRadius: 10, padding: '16px 18px' })}>
      <div style={s({ marginBottom: 12 })}>
        <div style={s({ fontSize: 12, fontWeight: 500, color: T.text1, marginBottom: 4 })}>{title}</div>
        <div style={s({ ...mono, fontSize: 10, color: T.text3 })}>{description}</div>
      </div>
      {children}
    </div>
  )
}

function StatusPill({ status }) {
  const tone =
    status === 'deliberating' ? T.green :
    status === 'closed' ? T.accent :
    status === 'forming' ? T.amber :
    T.text3
  return (
    <span style={s({ ...mono, fontSize: 9, color: tone, background: `${tone}18`, border: `1px solid ${tone}33`, padding: '2px 8px', borderRadius: 999 })}>
      {status}
    </span>
  )
}

function SafeBlock({ text }) {
  return (
    <pre style={s({ margin: 0, whiteSpace: 'pre-wrap', wordBreak: 'break-word', background: T.bgBase, border: `1px solid ${T.border0}`, borderRadius: 8, padding: 10, ...mono, fontSize: 10, color: T.text2, maxHeight: 240, overflow: 'auto' })}>
      {text || '—'}
    </pre>
  )
}

export function CouncilTab() {
  const [data, setData] = useState(null)
  const [selectedCouncilId, setSelectedCouncilId] = useState('')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let cancelled = false
    async function load() {
      try {
        const result = await backend.getMissionControlCouncil()
        if (!cancelled) {
          setData(result)
          setSelectedCouncilId((current) => current || result?.sessions?.[0]?.council_id || '')
        }
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    load()
    const timer = setInterval(load, 15000)
    return () => {
      cancelled = true
      clearInterval(timer)
    }
  }, [])

  const selected = useMemo(
    () => (data?.sessions || []).find((item) => item.council_id === selectedCouncilId) || data?.sessions?.[0] || null,
    [data, selectedCouncilId],
  )

  if (loading) return <div style={s({ padding: 24, color: T.text3, ...mono, fontSize: 11 })}>Indlæser council...</div>

  return (
    <div style={s({ display: 'flex', flexDirection: 'column', gap: 16 })}>
      <div style={s({ display: 'flex', alignItems: 'center', gap: 10 })}>
        <Crown size={16} color={T.accent} />
        <span style={s({ fontSize: 14, fontWeight: 500, color: T.text1 })}>Council</span>
        <span style={s({ ...mono, fontSize: 9, color: T.text3 })}>
          {data?.summary?.session_count || 0} sessions · {data?.summary?.active_count || 0} aktive
        </span>
      </div>

      <Section title="Council Roster" description="Roller Jarvis kan samle i en council-session">
        <div style={s({ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: 10 })}>
          {(data?.roster || []).map((member) => (
            <div key={member.role} style={s({ padding: '10px 12px', borderRadius: 8, background: T.bgOverlay, border: `1px solid ${T.border0}` })}>
              <div style={s({ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 8 })}>
                <span style={s({ fontSize: 11, fontWeight: 500 })}>{member.title}</span>
                <StatusPill status={member.status || 'available'} />
              </div>
              <div style={s({ ...mono, fontSize: 9, color: T.text3, marginTop: 6 })}>{member.role}</div>
              <div style={s({ ...mono, fontSize: 9, color: T.text2, marginTop: 4 })}>tool policy: {member.default_tool_policy}</div>
            </div>
          ))}
        </div>
      </Section>

      <div style={s({ display: 'grid', gridTemplateColumns: 'minmax(320px, 0.9fr) minmax(380px, 1.1fr)', gap: 16 })}>
        <Section title="Council Sessions" description="Topic, deltagere, status og outcome under Jarvis">
          <div style={s({ display: 'flex', flexDirection: 'column', gap: 10, maxHeight: 720, overflow: 'auto' })}>
            {(data?.sessions || []).length ? (
              (data.sessions || []).map((session) => (
                <button
                  key={session.council_id}
                  onClick={() => setSelectedCouncilId(session.council_id)}
                  style={s({
                    width: '100%',
                    textAlign: 'left',
                    padding: '10px 12px',
                    borderRadius: 8,
                    border: `1px solid ${selected?.council_id === session.council_id ? T.accent : T.border0}`,
                    background: selected?.council_id === session.council_id ? T.accentDim : T.bgOverlay,
                    color: T.text1,
                    cursor: 'pointer',
                  })}
                >
                  <div style={s({ display: 'flex', justifyContent: 'space-between', gap: 8, alignItems: 'center' })}>
                    <div style={s({ fontSize: 11, fontWeight: 600 })}>{session.topic || 'Council session'}</div>
                    <StatusPill status={session.status || 'forming'} />
                  </div>
                  <div style={s({ ...mono, fontSize: 9, color: T.text3, marginTop: 4 })}>
                    {(session.members || []).map((item) => item.role).join(', ') || 'no members'}
                  </div>
                  <div style={s({ ...mono, fontSize: 9, color: T.text2, marginTop: 6 })}>{session.summary || '—'}</div>
                </button>
              ))
            ) : (
              <div style={s({ padding: 24, color: T.text3, ...mono, fontSize: 10 })}>Ingen council sessions endnu</div>
            )}
          </div>
        </Section>

        <Section title="Council Detail" description="Jarvis input, medlemssammensaetning, samtale og outcome">
          {selected ? (
            <div style={s({ display: 'flex', flexDirection: 'column', gap: 14 })}>
              <div style={s({ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 12 })}>
                <div>
                  <div style={s({ fontSize: 13, fontWeight: 600 })}>{selected.topic || 'Council session'}</div>
                  <div style={s({ ...mono, fontSize: 9, color: T.text3, marginTop: 3 })}>{selected.council_id}</div>
                </div>
                <StatusPill status={selected.status || 'forming'} />
              </div>

              <div>
                <div style={s({ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 6 })}>
                  <Users size={13} color={T.accent} />
                  <span style={s({ fontSize: 11, fontWeight: 500 })}>Members</span>
                </div>
                <div style={s({ display: 'flex', flexDirection: 'column', gap: 8 })}>
                  {(selected.members || []).map((member) => (
                    <div key={member.agent_id} style={s({ padding: '8px 10px', borderRadius: 8, background: T.bgOverlay, border: `1px solid ${T.border0}` })}>
                      <div style={s({ display: 'flex', justifyContent: 'space-between', gap: 8 })}>
                        <span style={s({ fontSize: 11, fontWeight: 500 })}>{member.role}</span>
                        <span style={s({ ...mono, fontSize: 9, color: T.text3 })}>{member.confidence || 'pending'}</span>
                      </div>
                      <div style={s({ ...mono, fontSize: 9, color: T.text2, marginTop: 6 })}>{member.position_summary || 'awaiting deliberation'}</div>
                    </div>
                  ))}
                </div>
              </div>

              <div>
                <div style={s({ fontSize: 11, fontWeight: 500, marginBottom: 6 })}>Outcome summary</div>
                <SafeBlock text={selected.summary || '—'} />
              </div>

              <div>
                <div style={s({ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 6 })}>
                  <MessageSquare size={13} color={T.accent} />
                  <span style={s({ fontSize: 11, fontWeight: 500 })}>Council transcript</span>
                </div>
                <div style={s({ display: 'flex', flexDirection: 'column', gap: 8, maxHeight: 320, overflow: 'auto' })}>
                  {(selected.messages || []).length ? (
                    (selected.messages || []).map((message) => (
                      <div key={message.message_id} style={s({ padding: '8px 10px', borderRadius: 8, background: T.bgOverlay, border: `1px solid ${T.border0}` })}>
                        <div style={s({ display: 'flex', justifyContent: 'space-between', gap: 8 })}>
                          <span style={s({ ...mono, fontSize: 9, color: T.text3 })}>{message.direction} · {message.kind}</span>
                          <span style={s({ ...mono, fontSize: 9, color: T.text3 })}>{message.created_at}</span>
                        </div>
                        <div style={s({ ...mono, fontSize: 10, color: T.text2, whiteSpace: 'pre-wrap', marginTop: 6 })}>{message.content || '—'}</div>
                      </div>
                    ))
                  ) : (
                    <div style={s({ padding: 16, color: T.text3, ...mono, fontSize: 10 })}>Ingen council transcript endnu</div>
                  )}
                </div>
              </div>
            </div>
          ) : (
            <div style={s({ padding: 24, color: T.text3, ...mono, fontSize: 10 })}>Vælg en council session for detaljer</div>
          )}
        </Section>
      </div>
    </div>
  )
}
