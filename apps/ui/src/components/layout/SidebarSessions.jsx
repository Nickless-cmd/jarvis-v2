import { Clock3, Plus } from 'lucide-react'

export function SidebarSessions({ sessions }) {
  return (
    <section className="panel sidebar-sessions">
      <div className="panel-header">
        <h2>Chats</h2>
        <button className="icon-btn"><Plus size={15} /></button>
      </div>

      <div className="session-list">
        {sessions.map((session) => (
          <button className="session-item" key={session.id}>
            <div>
              <strong>{session.title}</strong>
              <span><Clock3 size={12} /> {session.lastMessage}</span>
            </div>
          </button>
        ))}
      </div>
    </section>
  )
}
