import { Clock3, Plus } from 'lucide-react'

export function SidebarSessions({ sessions, activeSessionId, onSelect, onCreate }) {
  return (
    <section className="panel sidebar-sessions">
      <div className="panel-header">
        <h2>Chats</h2>
        <button className="icon-btn" onClick={onCreate}><Plus size={15} /></button>
      </div>

      <div className="session-list">
        {sessions.map((session) => (
          <button
            className={session.id === activeSessionId ? 'session-item active' : 'session-item'}
            key={session.id}
            onClick={() => onSelect(session.id)}
          >
            <div>
              <strong>{session.title}</strong>
              <span><Clock3 size={12} /> {session.lastMessage || session.last_message}</span>
            </div>
          </button>
        ))}
      </div>
    </section>
  )
}
