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

const DEFAULT_COUNCIL_ROLES = ['planner', 'critic', 'researcher', 'synthesizer']

function RoleModelRow({ role, value, onChange }) {
  return (
    <div style={s({ display: 'flex', alignItems: 'center', gap: 8, padding: '6px 0', borderBottom: `1px solid ${T.border0}` })}>
      <span style={s({ ...mono, fontSize: 10, color: T.text2, width: 120, flexShrink: 0 })}>{role}</span>
      <input
        type="text"
        placeholder="provider (tom = cheap lane)"
        value={value.provider}
        onChange={(e) => onChange({ ...value, provider: e.target.value })}
        style={s({ flex: 1, borderRadius: 6, border: `1px solid ${T.border0}`, background: T.bgBase, color: T.text1, padding: '4px 8px', ...mono, fontSize: 9 })}
      />
      <input
        type="text"
        placeholder="model"
        value={value.model}
        onChange={(e) => onChange({ ...value, model: e.target.value })}
        style={s({ flex: 1, borderRadius: 6, border: `1px solid ${T.border0}`, background: T.bgBase, color: T.text1, padding: '4px 8px', ...mono, fontSize: 9 })}
      />
    </div>
  )
}

export function CouncilTab() {
  const [data, setData] = useState(null)
  const [selectedCouncilId, setSelectedCouncilId] = useState('')
  const [loading, setLoading] = useState(true)
  const [draft, setDraft] = useState('')
  const [topicDraft, setTopicDraft] = useState('')
  const [swarmTopicDraft, setSwarmTopicDraft] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [councilRoles, setCouncilRoles] = useState(DEFAULT_COUNCIL_ROLES)
  const [councilMemberModels, setCouncilMemberModels] = useState(
    () => Object.fromEntries(DEFAULT_COUNCIL_ROLES.map((r) => [r, { provider: '', model: '' }]))
  )

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

  async function refresh() {
    const result = await backend.getMissionControlCouncil()
    setData(result)
    setSelectedCouncilId((current) => current || result?.sessions?.[0]?.council_id || '')
    return result
  }

  async function handleRunRound() {
    if (!selected?.council_id || submitting) return
    setSubmitting(true)
    try {
      const result =
        selected?.mode === 'swarm'
          ? await backend.runMissionControlSwarmRound(selected.council_id)
          : await backend.runMissionControlCouncilRound(selected.council_id)
      await refresh()
      setSelectedCouncilId(result?.council_id || selected.council_id)
    } finally {
      setSubmitting(false)
    }
  }

  async function handleSendMessage() {
    if (!selected?.council_id || !draft.trim() || submitting) return
    setSubmitting(true)
    try {
      const result = await backend.messageMissionControlCouncil(selected.council_id, {
        content: draft.trim(),
      })
      setDraft('')
      await refresh()
      setSelectedCouncilId(result?.council_id || selected.council_id)
    } finally {
      setSubmitting(false)
    }
  }

  async function handleSpawnCouncil() {
    if (!topicDraft.trim() || submitting) return
    setSubmitting(true)
    try {
      const member_models = councilRoles
        .map((role) => ({ role, ...councilMemberModels[role] }))
        .filter((m) => m.provider || m.model)
      const result = await backend.spawnMissionControlCouncil({
        topic: topicDraft.trim(),
        roles: councilRoles,
        member_models,
      })
      setTopicDraft('')
      await refresh()
      setSelectedCouncilId(result?.council_id || '')
    } finally {
      setSubmitting(false)
    }
  }

  async function handleSpawnSwarm() {
    if (!swarmTopicDraft.trim() || submitting) return
    setSubmitting(true)
    try {
      const result = await backend.spawnMissionControlSwarm({
        topic: swarmTopicDraft.trim(),
      })
      setSwarmTopicDraft('')
      await refresh()
      setSelectedCouncilId(result?.council_id || '')
    } finally {
      setSubmitting(false)
    }
  }

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
          {data?.summary?.session_count || 0} sessions · {data?.summary?.active_count || 0} aktive · {data?.summary?.swarm_count || 0} swarms
        </span>
      </div>

      <div style={s({ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 })}>
        <Section title="Spawn Council" description="Deliberativ session — roller taler sekventielt, Jarvis synthesizer til sidst">
          <div style={s({ display: 'flex', flexDirection: 'column', gap: 10 })}>
            <textarea
              value={topicDraft}
              onChange={(event) => setTopicDraft(event.target.value)}
              placeholder="Council-emne..."
              style={s({ width: '100%', minHeight: 56, resize: 'vertical', borderRadius: 8, border: `1px solid ${T.border0}`, background: T.bgBase, color: T.text1, padding: 10, ...mono, fontSize: 10 })}
            />
            <div>
              <div style={s({ ...mono, fontSize: 9, color: T.text3, marginBottom: 6 })}>Model per rolle (tom = cheap lane)</div>
              {councilRoles.map((role) => (
                <RoleModelRow
                  key={role}
                  role={role}
                  value={councilMemberModels[role] || { provider: '', model: '' }}
                  onChange={(v) => setCouncilMemberModels((prev) => ({ ...prev, [role]: v }))}
                />
              ))}
            </div>
            <div>
              <button
                onClick={handleSpawnCouncil}
                disabled={submitting || !topicDraft.trim()}
                style={s({ borderRadius: 8, border: `1px solid ${T.accent}`, background: T.accentDim, color: T.text1, padding: '6px 10px', cursor: 'pointer', ...mono, fontSize: 9 })}
              >
                spawn council
              </button>
            </div>
          </div>
        </Section>

        <Section title="Spawn Swarm" description="Parallel fanout — workers kører simultant, coordinator merger resultater">
          <div style={s({ display: 'flex', flexDirection: 'column', gap: 10 })}>
            <textarea
              value={swarmTopicDraft}
              onChange={(event) => setSwarmTopicDraft(event.target.value)}
              placeholder="Swarm-opgave..."
              style={s({ width: '100%', minHeight: 56, resize: 'vertical', borderRadius: 8, border: `1px solid ${T.border0}`, background: T.bgBase, color: T.text1, padding: 10, ...mono, fontSize: 10 })}
            />
            <div>
              <button
                onClick={handleSpawnSwarm}
                disabled={submitting || !swarmTopicDraft.trim()}
                style={s({ borderRadius: 8, border: `1px solid ${T.border0}`, background: T.bgBase, color: T.text2, padding: '6px 10px', cursor: 'pointer', ...mono, fontSize: 9 })}
              >
                spawn swarm
              </button>
            </div>
          </div>
        </Section>
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
                  <div style={s({ ...mono, fontSize: 9, color: T.text3, marginTop: 4 })}>{session.mode || 'council'}</div>
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
                  <div style={s({ ...mono, fontSize: 9, color: T.text3, marginTop: 3 })}>{selected.council_id} · {selected.mode || 'council'}</div>
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

              <div style={s({ display: 'flex', flexDirection: 'column', gap: 10, padding: '10px 12px', borderRadius: 8, background: T.bgOverlay, border: `1px solid ${T.border0}` })}>
                <div style={s({ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 12 })}>
                  <div style={s({ fontSize: 11, fontWeight: 500 })}>Jarvis controls</div>
                  <button
                    onClick={handleRunRound}
                    disabled={submitting}
                    style={s({ borderRadius: 8, border: `1px solid ${T.accent}`, background: T.accentDim, color: T.text1, padding: '6px 10px', cursor: 'pointer', ...mono, fontSize: 9 })}
                  >
                    {selected?.mode === 'swarm' ? 'koer swarm round' : 'koer council round'}
                  </button>
                </div>
                <textarea
                  value={draft}
                  onChange={(event) => setDraft(event.target.value)}
                  placeholder="Skriv note fra Jarvis til council..."
                  style={s({ width: '100%', minHeight: 72, resize: 'vertical', borderRadius: 8, border: `1px solid ${T.border0}`, background: T.bgBase, color: T.text1, padding: 10, ...mono, fontSize: 10 })}
                />
                <div>
                  <button
                    onClick={handleSendMessage}
                    disabled={submitting || !draft.trim()}
                    style={s({ borderRadius: 8, border: `1px solid ${T.border0}`, background: T.bgBase, color: T.text2, padding: '6px 10px', cursor: 'pointer', ...mono, fontSize: 9 })}
                  >
                    send note
                  </button>
                </div>
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
