import { Activity, Clock3, Cpu, RadioTower, Sparkles } from 'lucide-react'

function messageCount(session) {
  return Array.isArray(session?.messages) ? session.messages.length : 0
}

function firstUserPrompt(session) {
  const firstUser = Array.isArray(session?.messages)
    ? session.messages.find((message) => message.role === 'user')
    : null
  const text = String(firstUser?.content || '').trim()
  if (!text) return 'No user prompt yet.'
  return text.length > 120 ? `${text.slice(0, 120)}…` : text
}

export function ChatSupportRail({ session, selection, isStreaming }) {
  const items = [
    {
      icon: Cpu,
      label: 'Provider',
      value: selection.currentProvider || 'unknown',
    },
    {
      icon: RadioTower,
      label: 'Model',
      value: selection.currentModel || 'unknown',
    },
    {
      icon: Activity,
      label: 'Status',
      value: isStreaming ? 'Generating' : 'Idle',
    },
    {
      icon: Clock3,
      label: 'Messages',
      value: String(messageCount(session)),
    },
  ]

  return (
    <aside className="chat-support-rail">
      <section className="support-card support-card-system">
        <div className="support-card-header">
          <span className="support-card-kicker">Operator</span>
          <strong>Runtime</strong>
        </div>
        <div className="support-status-banner">
          <span className={isStreaming ? 'status-dot live' : 'status-dot'} />
          <div>
            <strong>{isStreaming ? 'Generation active' : 'Ready for input'}</strong>
            <span>{selection.currentProvider || 'unknown'} · {selection.currentModel || 'unknown'}</span>
          </div>
        </div>
        <div className="support-stat-list">
          {items.map(({ icon: Icon, label, value }) => (
            <div className="support-stat-row" key={label}>
              <div className="support-stat-label">
                <Icon size={12} />
                <span>{label}</span>
              </div>
              <strong>{value}</strong>
            </div>
          ))}
        </div>
      </section>

      <section className="support-card support-card-focus">
        <div className="support-card-header">
          <span className="support-card-kicker">Session</span>
          <strong>Current focus</strong>
        </div>
        <p>{firstUserPrompt(session)}</p>
        <div className="support-note">
          <Sparkles size={12} />
          <span>{isStreaming ? 'Streaming active. Jarvis is responding now.' : 'Chat stays primary. Mission Control remains separate.'}</span>
        </div>
      </section>
    </aside>
  )
}
