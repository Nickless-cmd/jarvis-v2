const TABS = [
  { id: 'overview', label: 'Overview' },
  { id: 'operations', label: 'Operations' },
  { id: 'observability', label: 'Observability' },
  { id: 'jarvis', label: 'Jarvis', hasSubTabs: true },
]

const JARVIS_SUB_TABS = [
  { id: 'jarvis-core', label: 'Core', parent: 'jarvis' },
  { id: 'jarvis-identity', label: 'Identity', parent: 'jarvis' },
  { id: 'jarvis-continuity', label: 'Continuity', parent: 'jarvis' },
  { id: 'jarvis-selfreview', label: 'Self-Review', parent: 'jarvis' },
]

export function MCTabBar({ activeTab, onChange, activeJarvisSubTab, onJarvisSubTabChange }) {
  const isJarvisActive = activeTab === 'jarvis'
  
  return (
    <>
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
      {isJarvisActive && (
        <nav className="mc-sub-tabbar">
          {JARVIS_SUB_TABS.map((tab) => (
            <button
              className={tab.id === activeJarvisSubTab ? 'mc-sub-tab active' : 'mc-sub-tab'}
              key={tab.id}
              onClick={() => onJarvisSubTabChange(tab.id)}
            >
              {tab.label}
            </button>
          ))}
        </nav>
      )}
    </>
  )
}
