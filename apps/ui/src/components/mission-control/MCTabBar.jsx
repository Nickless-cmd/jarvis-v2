import { useState } from 'react'
import { ChevronDown, Activity, FolderKanban, ListChecks, Cable, Eye, Rocket, DollarSign, Bot, MoreHorizontal } from 'lucide-react'

const PRIMARY_TABS = [
  { id: 'overview', label: 'Overview', icon: Activity },
  { id: 'runs', label: 'Runs', icon: FolderKanban },
  { id: 'approvals', label: 'Approvals', icon: ListChecks },
  { id: 'sessions', label: 'Channels', icon: Cable },
  { id: 'observability', label: 'Observability', icon: Eye },
  { id: 'incident', label: 'Incident', icon: Rocket },
  { id: 'cost', label: 'Cost', icon: DollarSign },
  { id: 'agents', label: 'Agents', icon: Bot },
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

const JARVIS_SUB_TABS = [
  { id: 'jarvis-core', label: 'Core', parent: 'jarvis' },
  { id: 'jarvis-identity', label: 'Identity', parent: 'jarvis' },
  { id: 'jarvis-continuity', label: 'Continuity', parent: 'jarvis' },
  { id: 'jarvis-selfreview', label: 'Self-Review', parent: 'jarvis' },
]

export function MCTabBar({ activeTab, onChange, activeJarvisSubTab, onJarvisSubTabChange }) {
  const [moreOpen, setMoreOpen] = useState(false)
  const isJarvisActive = activeTab === 'jarvis'
  
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
