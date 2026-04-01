import { useState } from 'react'
import { Activity, Eye, Bot, Brain, Layers, Shield, TrendingUp, MoreHorizontal } from 'lucide-react'

const PRIMARY_TABS = [
  { id: 'overview', label: 'Overview', icon: Activity },
  { id: 'operations', label: 'Operations', icon: Bot },
  { id: 'observability', label: 'Observability', icon: Eye },
  { id: 'living-mind', label: 'Living Mind', icon: Brain },
  { id: 'self-review', label: 'Self-Review', icon: Shield },
  { id: 'continuity', label: 'Continuity', icon: Layers },
  { id: 'development', label: 'Development', icon: TrendingUp },
]

const MORE_TABS = [
  { id: 'policy', label: 'Policy' },
  { id: 'memory', label: 'Memory' },
  { id: 'mind', label: 'Mind' },
  { id: 'council', label: 'Council' },
  { id: 'hardening', label: 'Hardening' },
  { id: 'lab', label: 'Lab' },
  { id: 'debug', label: 'Debug' },
  { id: 'workspace', label: 'Workspace' },
  { id: 'self', label: 'Self' },
]

export function MCTabBar({ activeTab, onChange }) {
  const [moreOpen, setMoreOpen] = useState(false)

  const activePrimaryTab = PRIMARY_TABS.find(t => t.id === activeTab)
  const isMoreTab = !PRIMARY_TABS.find(t => t.id === activeTab)
  
  return (
    <>
      <nav className="mc-tabbar">
        {PRIMARY_TABS.map((tab) => {
          const Icon = tab.icon
          const isActive = activeTab === tab.id
          return (
            <button
              className={isActive ? 'mc-tab active' : 'mc-tab'}
              key={tab.id}
              onClick={() => onChange(tab.id)}
            >
              {Icon && <Icon size={12} />}
              {tab.label}
            </button>
          )
        })}
        <div className="mc-tab-more-wrapper">
          <button
            className={`mc-tab mc-tab-more ${moreOpen ? 'active' : ''} ${isMoreTab ? 'active' : ''}`}
            onClick={() => setMoreOpen(!moreOpen)}
          >
            <MoreHorizontal size={12} />
            More
          </button>
          {moreOpen && (
            <div className="mc-tab-more-dropdown">
              {MORE_TABS.map((tab) => (
                <button
                  key={tab.id}
                  className={activeTab === tab.id ? 'mc-tab-more-item active' : 'mc-tab-more-item'}
                  onClick={() => {
                    onChange(tab.id)
                    setMoreOpen(false)
                  }}
                >
                  {tab.label}
                </button>
              ))}
            </div>
          )}
        </div>
      </nav>
    </>
  )
}
