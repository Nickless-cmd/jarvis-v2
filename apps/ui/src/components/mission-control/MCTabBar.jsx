const TABS = [
  { id: 'overview', label: 'Overview' },
  { id: 'operations', label: 'Operations' },
  { id: 'observability', label: 'Observability' },
  { id: 'jarvis', label: 'Jarvis' },
]

export function MCTabBar({ activeTab, onChange }) {
  return (
    <nav className="mc-tabbar">
      {TABS.map((tab) => (
        <button
          className={tab.id === activeTab ? 'mc-tab active' : 'mc-tab'}
          key={tab.id}
          onClick={() => onChange(tab.id)}
        >
          {tab.label}
        </button>
      ))}
    </nav>
  )
}
