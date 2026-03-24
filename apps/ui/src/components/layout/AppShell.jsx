import { Bot, LayoutDashboard, MessageSquare } from 'lucide-react'

export function AppShell({ activeView, onChangeView, sidebarContent, children }) {
  return (
    <div className="app-shell">
      <aside className="global-sidebar">
        <div className="brand-block">
          <div className="brand-icon"><Bot size={14} /></div>
          <div>
            <div className="brand-name">Jarvis</div>
            <div className="brand-subtitle">Control Surface</div>
          </div>
          <div className="brand-status-dot" />
        </div>

        <nav className="global-nav">
          <button
            className={activeView === 'chat' ? 'nav-item active' : 'nav-item'}
            onClick={() => onChangeView('chat')}
            title="Open Chat"
          >
            <MessageSquare size={14} />
            <span>Chat</span>
          </button>
          <button
            className={activeView === 'mission-control' ? 'nav-item active' : 'nav-item'}
            onClick={() => onChangeView('mission-control')}
            title="Open Mission Control"
          >
            <LayoutDashboard size={14} />
            <span>Mission Control</span>
          </button>
        </nav>

        {sidebarContent ? <div className="sidebar-section">{sidebarContent}</div> : null}

        <div className="sidebar-footer">
          <span className="sidebar-footer-label">Workspace</span>
          <p>Same shell, separate rooms.</p>
        </div>
      </aside>

      <div className="app-content">{children}</div>
    </div>
  )
}
