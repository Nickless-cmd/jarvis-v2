import { Plus } from 'lucide-react'

function relativeTime(dateStr) {
  if (!dateStr) return ''
  const delta = Date.now() - new Date(dateStr).getTime()
  if (isNaN(delta) || delta < 0) return ''
  const sec = Math.floor(delta / 1000)
  if (sec < 60) return 'lige nu'
  const min = Math.floor(sec / 60)
  if (min < 60) return `${min}m siden`
  const hr = Math.floor(min / 60)
  if (hr < 24) return `${hr}t siden`
  return `${Math.floor(hr / 24)}d siden`
}

export function SidebarSessions({ sessions, activeSessionId, onSelect, onCreate }) {
  return (
    <section className="sidebar-sessions">
      <div className="sidebar-sessions-head">
        <span className="sidebar-mini-label mono">Seneste</span>
      </div>

      <div className="session-list">
        {sessions.map((session) => (
          <button
            className={session.id === activeSessionId ? 'session-item active' : 'session-item'}
            key={session.id}
            onClick={() => onSelect(session.id)}
            title={session.title}
          >
            <div className="session-item-title">{session.title}</div>
            <div className="session-item-time mono">{relativeTime(session.updated_at)}</div>
          </button>
        ))}

        {!sessions.length ? (
          <div className="sidebar-empty-state">
            <span>Ingen chats endnu</span>
          </div>
        ) : null}
      </div>
    </section>
  )
}
