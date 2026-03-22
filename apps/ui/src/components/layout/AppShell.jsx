import { Bot, LayoutDashboard, MessageSquare } from 'lucide-react'

export function AppShell({ activeView, onChangeView, children }) {
  return (
    <div className="app-shell">
      <aside className="global-sidebar">
        <div className="brand-block">
          <div className="brand-icon"><Bot size={16} /></div>
          <div>
            <div className="brand-name">Jarvis</div>
            <div className="brand-subtitle">Unified UI</div>
          </div>
        </div>

        <nav className="global-nav">
          <button className={activeView === 'chat' ? 'nav-item active' : 'nav-item'} onClick={() => onChangeView('chat')}>
            <MessageSquare size={16} />
            <span>Chat</span>
          </button>
          <button className={activeView === 'mission-control' ? 'nav-item active' : 'nav-item'} onClick={() => onChangeView('mission-control')}>
            <LayoutDashboard size={16} />
            <span>Mission Control</span>
          </button>
        </nav>

        <div className="sidebar-footer">
          <p>Same shell. Same palette. Different room.</p>
        </div>
      </aside>

      <div className="app-content">{children}</div>
    </div>
  )
}
