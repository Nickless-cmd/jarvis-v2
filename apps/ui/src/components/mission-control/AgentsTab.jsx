import { useEffect, useMemo, useState } from 'react'
import { Bot, Clock3, Cpu, MessageSquare, PlugZap, Zap } from 'lucide-react'
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
    status === 'active' ? T.green :
    status === 'completed' ? T.accent :
    status === 'failed' ? T.red :
    status === 'expired' ? T.amber :
    T.text3
  return (
    <span style={s({ ...mono, fontSize: 9, color: tone, background: `${tone}18`, border: `1px solid ${tone}33`, padding: '2px 8px', borderRadius: 999 })}>
      {status}
    </span>
  )
}

function KV({ label, value }) {
  return (
    <div style={s({ display: 'flex', justifyContent: 'space-between', gap: 12, padding: '4px 0', borderBottom: `1px solid ${T.border0}` })}>
      <span style={s({ ...mono, fontSize: 10, color: T.text3 })}>{label}</span>
      <span style={s({ ...mono, fontSize: 10, color: T.text1, textAlign: 'right' })}>{String(value ?? '—')}</span>
    </div>
  )
}

function SafeJson({ value }) {
  const text = typeof value === 'string' ? value : JSON.stringify(value || {}, null, 2)
  return (
    <pre style={s({ margin: 0, whiteSpace: 'pre-wrap', wordBreak: 'break-word', background: T.bgBase, border: `1px solid ${T.border0}`, borderRadius: 8, padding: 10, ...mono, fontSize: 10, color: T.text2, maxHeight: 220, overflow: 'auto' })}>
      {text || '{}'}
    </pre>
  )
}

function AgentRow({ agent, active, onSelect }) {
  return (
    <button
      onClick={() => onSelect(agent)}
      style={s({
        width: '100%',
        textAlign: 'left',
        padding: '10px 12px',
        borderRadius: 8,
        border: `1px solid ${active ? T.accent : T.border0}`,
        background: active ? T.accentDim : T.bgOverlay,
        color: T.text1,
        cursor: 'pointer',
      })}
    >
      <div style={s({ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 12 })}>
        <div style={s({ minWidth: 0 })}>
          <div style={s({ fontSize: 11, fontWeight: 600 })}>{agent.role || agent.kind || 'agent'}</div>
          <div style={s({ ...mono, fontSize: 9, color: T.text3, marginTop: 3, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' })}>
            {agent.goal || 'No goal'}
          </div>
        </div>
        <StatusPill status={agent.status || 'unknown'} />
      </div>
      <div style={s({ display: 'flex', flexWrap: 'wrap', gap: 8, marginTop: 8 })}>
        <span style={s({ ...mono, fontSize: 9, color: T.text2 })}>{agent.provider || 'none'} / {agent.model || 'none'}</span>
        <span style={s({ ...mono, fontSize: 9, color: T.text3 })}>{agent.progress_label || 'idle'}</span>
        <span style={s({ ...mono, fontSize: 9, color: T.text3 })}>{agent.tokens_burned || 0} tok</span>
      </div>
    </button>
  )
}

export function AgentsTab() {
  const [data, setData] = useState(null)
  const [selectedId, setSelectedId] = useState('')
  const [loading, setLoading] = useState(true)
  const [draft, setDraft] = useState('')
  const [scheduleDelay, setScheduleDelay] = useState('900')
  const [submitting, setSubmitting] = useState(false)

  useEffect(() => {
    let cancelled = false
    async function load() {
      try {
        const result = await backend.getMissionControlAgents()
        if (!cancelled) {
          setData(result)
          const firstId = selectedId || result?.agents?.[0]?.agent_id || ''
          setSelectedId(firstId)
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
  }, [selectedId])

  async function refresh() {
    const result = await backend.getMissionControlAgents()
    setData(result)
    setSelectedId((current) => current || result?.agents?.[0]?.agent_id || '')
    return result
  }

  async function handleSendMessage() {
    if (!selected?.agent_id || !draft.trim() || submitting) return
    setSubmitting(true)
    try {
      const result = await backend.messageMissionControlAgent(selected.agent_id, {
        content: draft.trim(),
        execution_mode: 'solo-task',
        auto_execute: true,
      })
      setDraft('')
      await refresh()
      setSelectedId(result?.agent_id || selected.agent_id)
    } finally {
      setSubmitting(false)
    }
  }

  async function handleSchedule() {
    if (!selected?.agent_id || submitting) return
    setSubmitting(true)
    try {
      const delay = Math.max(30, Number(scheduleDelay || 0) || 900)
      const result = await backend.scheduleMissionControlAgent(selected.agent_id, {
        schedule_kind: 'interval-seconds',
        delay_seconds: delay,
      })
      await refresh()
      setSelectedId(result?.agent_id || selected.agent_id)
    } finally {
      setSubmitting(false)
    }
  }

  async function handleRunDue() {
    if (submitting) return
    setSubmitting(true)
    try {
      await backend.runDueMissionControlAgents({ limit: 10 })
      await refresh()
    } finally {
      setSubmitting(false)
    }
  }

  const selected = useMemo(
    () => (data?.agents || []).find((item) => item.agent_id === selectedId) || data?.agents?.[0] || null,
    [data, selectedId],
  )

  if (loading) return <div style={s({ padding: 24, color: T.text3, ...mono, fontSize: 11 })}>Indlæser agents...</div>

  return (
    <div style={s({ display: 'flex', flexDirection: 'column', gap: 16 })}>
      <div style={s({ display: 'flex', alignItems: 'center', gap: 10 })}>
        <Bot size={16} color={T.accent} />
        <span style={s({ fontSize: 14, fontWeight: 500, color: T.text1 })}>Agents</span>
        <span style={s({ ...mono, fontSize: 9, color: T.text3 })}>
          {data?.summary?.agent_count || 0} total · {data?.summary?.active_count || 0} aktive
        </span>
      </div>

      <Section title="Cheap Lane Pool" description="Tilgaengelige cheap-lane providere og modeller til offspring">
        <div style={s({ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: 10 })}>
          {(data?.cheap_lane?.providers || []).map((item) => (
            <div key={`${item.provider}:${item.model}`} style={s({ padding: '10px 12px', borderRadius: 8, background: T.bgOverlay, border: `1px solid ${T.border0}` })}>
              <div style={s({ display: 'flex', justifyContent: 'space-between', gap: 8 })}>
                <span style={s({ fontSize: 11, fontWeight: 500, color: T.text1 })}>{item.provider}</span>
                <StatusPill status={item.status || 'unknown'} />
              </div>
              <div style={s({ ...mono, fontSize: 9, color: T.text3, marginTop: 4 })}>{item.model}</div>
              <div style={s({ ...mono, fontSize: 9, color: item.selected ? T.green : T.text3, marginTop: 8 })}>
                {item.selected ? 'selected target' : `priority ${item.effective_priority ?? item.priority ?? 0}`}
              </div>
            </div>
          ))}
        </div>
      </Section>

      <div style={s({ display: 'grid', gridTemplateColumns: 'minmax(320px, 0.95fr) minmax(360px, 1.05fr)', gap: 16 })}>
        <Section title="Agent Registry" description="Aktive, planlagte, failede og persistente offspring under Jarvis">
          <div style={s({ display: 'flex', flexDirection: 'column', gap: 10, maxHeight: 720, overflow: 'auto' })}>
            {(data?.agents || []).length ? (
              (data.agents || []).map((agent) => (
                <AgentRow
                  key={agent.agent_id}
                  agent={agent}
                  active={agent.agent_id === selected?.agent_id}
                  onSelect={(item) => setSelectedId(item.agent_id)}
                />
              ))
            ) : (
              <div style={s({ padding: 24, color: T.text3, ...mono, fontSize: 10 })}>Ingen agents endnu</div>
            )}
          </div>
        </Section>

        <Section title="Agent Detail" description="Input, dialog, outcome og token burn for den valgte agent">
          {selected ? (
            <div style={s({ display: 'flex', flexDirection: 'column', gap: 14 })}>
              <div style={s({ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 12 })}>
                <div>
                  <div style={s({ fontSize: 13, fontWeight: 600, color: T.text1 })}>{selected.role || selected.kind || selected.agent_id}</div>
                  <div style={s({ ...mono, fontSize: 9, color: T.text3, marginTop: 3 })}>{selected.agent_id}</div>
                </div>
                <StatusPill status={selected.status || 'unknown'} />
              </div>

              <div style={s({ display: 'grid', gridTemplateColumns: 'repeat(2, minmax(0, 1fr))', gap: 12 })}>
                <div>
                  <KV label="Provider / model" value={`${selected.provider || 'none'} / ${selected.model || 'none'}`} />
                  <KV label="Lane" value={selected.lane} />
                  <KV label="Tool policy" value={selected.tool_policy} />
                  <KV label="Token burn" value={selected.tokens_burned || 0} />
                  <KV label="Budget" value={selected.budget_tokens || 0} />
                  <KV label="Next wake" value={selected.next_wake_at || '—'} />
                  <KV label="Schedule" value={selected.latest_schedule?.schedule_kind || selected.schedule?.schedule_kind || '—'} />
                </div>
                <div>
                  <KV label="Progress" value={selected.progress_label} />
                  <KV label="Persistent" value={selected.persistent ? 'yes' : 'no'} />
                  <KV label="Messages" value={selected.message_count || 0} />
                  <KV label="Tool calls" value={selected.tool_call_count || 0} />
                  <KV label="Failures" value={selected.failure_count || 0} />
                  <KV label="Last error" value={selected.last_error || '—'} />
                </div>
              </div>

              <div>
                <div style={s({ fontSize: 11, fontWeight: 500, marginBottom: 6 })}>Goal</div>
                <div style={s({ ...mono, fontSize: 10, color: T.text2, whiteSpace: 'pre-wrap' })}>{selected.goal || '—'}</div>
              </div>

              <div>
                <div style={s({ fontSize: 11, fontWeight: 500, marginBottom: 6 })}>System prompt</div>
                <SafeJson value={selected.system_prompt || ''} />
              </div>

              <div style={s({ display: 'grid', gridTemplateColumns: 'repeat(2, minmax(0, 1fr))', gap: 12 })}>
                <div>
                  <div style={s({ fontSize: 11, fontWeight: 500, marginBottom: 6 })}>Allowed tools</div>
                  <SafeJson value={selected.allowed_tools || []} />
                </div>
                <div>
                  <div style={s({ fontSize: 11, fontWeight: 500, marginBottom: 6 })}>Context package</div>
                  <SafeJson value={selected.context || {}} />
                </div>
              </div>

              <div style={s({ display: 'flex', flexDirection: 'column', gap: 10, padding: '10px 12px', borderRadius: 8, background: T.bgOverlay, border: `1px solid ${T.border0}` })}>
                <div style={s({ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 12 })}>
                  <div style={s({ fontSize: 11, fontWeight: 500 })}>Jarvis controls</div>
                  <button
                    onClick={handleRunDue}
                    disabled={submitting}
                    style={s({ borderRadius: 8, border: `1px solid ${T.border0}`, background: T.bgBase, color: T.text2, padding: '6px 10px', cursor: 'pointer', ...mono, fontSize: 9 })}
                  >
                    fire due schedules
                  </button>
                </div>
                <textarea
                  value={draft}
                  onChange={(event) => setDraft(event.target.value)}
                  placeholder="Skriv besked fra Jarvis til agenten..."
                  style={s({ width: '100%', minHeight: 88, resize: 'vertical', borderRadius: 8, border: `1px solid ${T.border0}`, background: T.bgBase, color: T.text1, padding: 10, ...mono, fontSize: 10 })}
                />
                <div style={s({ display: 'flex', flexWrap: 'wrap', gap: 8, alignItems: 'center' })}>
                  <button
                    onClick={handleSendMessage}
                    disabled={submitting || !draft.trim()}
                    style={s({ borderRadius: 8, border: `1px solid ${T.accent}`, background: T.accentDim, color: T.text1, padding: '6px 10px', cursor: 'pointer', ...mono, fontSize: 9 })}
                  >
                    send og koer
                  </button>
                  <input
                    value={scheduleDelay}
                    onChange={(event) => setScheduleDelay(event.target.value)}
                    style={s({ width: 96, borderRadius: 8, border: `1px solid ${T.border0}`, background: T.bgBase, color: T.text1, padding: '6px 8px', ...mono, fontSize: 9 })}
                  />
                  <button
                    onClick={handleSchedule}
                    disabled={submitting}
                    style={s({ borderRadius: 8, border: `1px solid ${T.border0}`, background: T.bgBase, color: T.text2, padding: '6px 10px', cursor: 'pointer', ...mono, fontSize: 9 })}
                  >
                    schedule sek.
                  </button>
                </div>
              </div>

              <div>
                <div style={s({ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 6 })}>
                  <MessageSquare size={13} color={T.accent} />
                  <span style={s({ fontSize: 11, fontWeight: 500 })}>Transcript</span>
                </div>
                <div style={s({ display: 'flex', flexDirection: 'column', gap: 8, maxHeight: 260, overflow: 'auto' })}>
                  {(selected.messages || []).map((message) => (
                    <div key={message.message_id} style={s({ padding: '8px 10px', borderRadius: 8, background: T.bgOverlay, border: `1px solid ${T.border0}` })}>
                      <div style={s({ display: 'flex', justifyContent: 'space-between', gap: 8 })}>
                        <span style={s({ ...mono, fontSize: 9, color: T.text3 })}>{message.direction} · {message.kind}</span>
                        <span style={s({ ...mono, fontSize: 9, color: T.text3 })}>{message.created_at}</span>
                      </div>
                      <div style={s({ ...mono, fontSize: 10, color: T.text2, whiteSpace: 'pre-wrap', marginTop: 6 })}>{message.content || '—'}</div>
                    </div>
                  ))}
                </div>
              </div>

              <div style={s({ display: 'grid', gridTemplateColumns: 'repeat(2, minmax(0, 1fr))', gap: 12 })}>
                <div>
                  <div style={s({ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 6 })}>
                    <Clock3 size={13} color={T.accent} />
                    <span style={s({ fontSize: 11, fontWeight: 500 })}>Runs</span>
                  </div>
                  <div style={s({ display: 'flex', flexDirection: 'column', gap: 8, maxHeight: 220, overflow: 'auto' })}>
                    {(selected.runs || []).map((run) => (
                      <div key={run.run_id} style={s({ padding: '8px 10px', borderRadius: 8, background: T.bgOverlay, border: `1px solid ${T.border0}` })}>
                        <div style={s({ display: 'flex', justifyContent: 'space-between', gap: 8 })}>
                          <span style={s({ ...mono, fontSize: 9, color: T.text2 })}>{run.execution_mode}</span>
                          <StatusPill status={run.status || 'unknown'} />
                        </div>
                        <div style={s({ ...mono, fontSize: 9, color: T.text3, marginTop: 4 })}>{run.provider || 'none'} / {run.model || 'none'}</div>
                        <div style={s({ ...mono, fontSize: 10, color: T.text2, whiteSpace: 'pre-wrap', marginTop: 6 })}>{run.output_summary || run.input_summary || '—'}</div>
                      </div>
                    ))}
                  </div>
                </div>
                <div>
                  <div style={s({ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 6 })}>
                    <PlugZap size={13} color={T.accent} />
                    <span style={s({ fontSize: 11, fontWeight: 500 })}>Tool activity</span>
                  </div>
                  <div style={s({ display: 'flex', flexDirection: 'column', gap: 8, maxHeight: 220, overflow: 'auto' })}>
                    {(selected.tool_calls || []).length ? (
                      (selected.tool_calls || []).map((call) => (
                        <div key={call.tool_call_id} style={s({ padding: '8px 10px', borderRadius: 8, background: T.bgOverlay, border: `1px solid ${T.border0}` })}>
                          <div style={s({ display: 'flex', justifyContent: 'space-between', gap: 8 })}>
                            <span style={s({ ...mono, fontSize: 9, color: T.text2 })}>{call.tool_name}</span>
                            <StatusPill status={call.status || 'queued'} />
                          </div>
                          <div style={s({ ...mono, fontSize: 9, color: T.text3, marginTop: 6, whiteSpace: 'pre-wrap' })}>{call.result_preview || 'No tool output yet'}</div>
                        </div>
                      ))
                    ) : (
                      <div style={s({ padding: 16, color: T.text3, ...mono, fontSize: 10 })}>Ingen tool calls endnu</div>
                    )}
                  </div>
                </div>
              </div>

              <div>
                <div style={s({ fontSize: 11, fontWeight: 500, marginBottom: 6 })}>Schedules</div>
                <div style={s({ display: 'flex', flexDirection: 'column', gap: 8, maxHeight: 180, overflow: 'auto' })}>
                  {(selected.schedules || []).length ? (
                    (selected.schedules || []).map((schedule) => (
                      <div key={schedule.schedule_id} style={s({ padding: '8px 10px', borderRadius: 8, background: T.bgOverlay, border: `1px solid ${T.border0}` })}>
                        <div style={s({ display: 'flex', justifyContent: 'space-between', gap: 8 })}>
                          <span style={s({ ...mono, fontSize: 9, color: T.text2 })}>{schedule.schedule_kind}</span>
                          <span style={s({ ...mono, fontSize: 9, color: schedule.active ? T.green : T.text3 })}>{schedule.active ? 'active' : 'inactive'}</span>
                        </div>
                        <div style={s({ ...mono, fontSize: 9, color: T.text3, marginTop: 4 })}>expr: {schedule.schedule_expr || '—'}</div>
                        <div style={s({ ...mono, fontSize: 9, color: T.text3, marginTop: 4 })}>next: {schedule.next_fire_at || '—'}</div>
                      </div>
                    ))
                  ) : (
                    <div style={s({ padding: 16, color: T.text3, ...mono, fontSize: 10 })}>Ingen schedules endnu</div>
                  )}
                </div>
              </div>
            </div>
          ) : (
            <div style={s({ padding: 24, color: T.text3, ...mono, fontSize: 10 })}>Vaelg en agent for detaljer</div>
          )}
        </Section>
      </div>

      <Section title="Template Roster" description="Roller Jarvis kan spawn'e paa cheap lane i fase 1">
        <div style={s({ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: 10 })}>
          {(data?.templates || []).map((template) => (
            <div key={template.role} style={s({ padding: '10px 12px', borderRadius: 8, background: T.bgOverlay, border: `1px solid ${T.border0}` })}>
              <div style={s({ display: 'flex', alignItems: 'center', gap: 8 })}>
                <Zap size={13} color={T.accent} />
                <span style={s({ fontSize: 11, fontWeight: 500 })}>{template.title}</span>
              </div>
              <div style={s({ ...mono, fontSize: 9, color: T.text3, marginTop: 6 })}>{template.role}</div>
              <div style={s({ ...mono, fontSize: 9, color: T.text2, marginTop: 4 })}>tool policy: {template.default_tool_policy}</div>
            </div>
          ))}
        </div>
      </Section>
    </div>
  )
}
