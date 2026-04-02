import { Bot, LayoutDashboard, MessageSquare, Brain, Layers, Plus } from 'lucide-react'

export function AppShell({ activeView, onChangeView, sidebarContent, systemHealth, onNewChat, children }) {
  const health = systemHealth || { cpu_pct: 0, ram_pct: 0, disk_free_mb: 0 }

  return (
    <div className="app-shell">
      <aside className="global-sidebar">
        <div className="brand-block">
          <div className="brand-icon"><Bot size={14} /></div>
          <span className="brand-name-text">JARVIS</span>
          <div className="brand-status-dot" />
        </div>

        <button className="sidebar-new-chat-btn" onClick={onNewChat}>
          <Plus size={12} />
          Ny chat
        </button>

        <nav className="global-nav">
          {[
            { id: 'chat', icon: MessageSquare, label: 'Chat' },
            { id: 'memory', icon: Brain, label: 'Memory' },
            { id: 'skills', icon: Layers, label: 'Skills' },
            { id: 'mission-control', icon: LayoutDashboard, label: 'Mission Control' },
          ].map(({ id, icon: Icon, label }) => (
            <button
              key={id}
              className={activeView === id ? 'nav-item active' : 'nav-item'}
              onClick={() => onChangeView(id)}
              title={label}
            >
              <Icon size={13} />
              <span>{label}</span>
            </button>
          ))}
        </nav>

        {sidebarContent ? <div className="sidebar-section">{sidebarContent}</div> : null}

        <div className="sidebar-system-stats">
          {[
            { label: 'CPU', value: health.cpu_pct, unit: '%' },
            { label: 'RAM', value: health.ram_pct, unit: '%' },
          ].map(({ label, value, unit }) => (
            <div key={label} className="sidebar-stat-row">
              <div className="sidebar-stat-labels">
                <span className="sidebar-stat-name mono">{label}</span>
                <span className="sidebar-stat-value mono">{value}{unit}</span>
              </div>
              <div className="progress-bar">
                <div className="progress-bar-fill" style={{ width: `${value}%`, background: value > 80 ? '#c05050' : '#3d8f7c' }} />
              </div>
            </div>
          ))}
          <div className="sidebar-stat-labels" style={{ marginTop: 4 }}>
            <span className="sidebar-stat-name mono">DISK</span>
            <span className="sidebar-stat-value mono">{health.disk_free_mb} MB free</span>
          </div>
        </div>
      </aside>

      <div className="app-content">{children}</div>
    </div>
  )
}
