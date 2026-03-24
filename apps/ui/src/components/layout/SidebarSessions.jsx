import { Clock3, Plus } from 'lucide-react'

export function SidebarSessions({ sessions, activeSessionId, onSelect, onCreate }) {
  return (
    <section className="sidebar-sessions">
      <div className="sidebar-sessions-head">
        <div>
          <div className="sidebar-mini-label">Recent</div>
          <h2>Chats</h2>
        </div>
        <button className="icon-btn sidebar-plus-btn" onClick={onCreate} title="New chat">
          <Plus size={14} />
        </button>
      </div>

      <div className="session-list">
        {sessions.map((session) => (
          <button
            className={session.id === activeSessionId ? 'session-item active' : 'session-item'}
            key={session.id}
            onClick={() => onSelect(session.id)}
          >
            <div className="session-item-copy">
              <strong>{session.title}</strong>
              <span>{session.lastMessage || session.last_message || 'No messages yet'}</span>
            </div>
            <small>
              <Clock3 size={11} />
              {session.updated_at ? 'saved' : 'recent'}
            </small>
          </button>
        ))}

        {!sessions.length ? (
          <div className="sidebar-empty-state">
            <strong>No chats yet</strong>
            <span>Create a session to start a persisted thread.</span>
          </div>
        ) : null}
      </div>
    </section>
  )
}
