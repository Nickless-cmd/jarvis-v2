import { Activity, Eye, Bot, Brain, DollarSign, Layers, Shield, TrendingUp, Database, Package, Lock, FlaskConical } from 'lucide-react'

const PRIMARY_TABS = [
  { id: 'overview', label: 'Overview', icon: Activity },
  { id: 'operations', label: 'Operations', icon: Bot },
  { id: 'observability', label: 'Observability', icon: Eye },
  { id: 'living-mind', label: 'Living Mind', icon: Brain },
  { id: 'self-review', label: 'Self-Review', icon: Shield },
  { id: 'continuity', label: 'Continuity', icon: Layers },
  { id: 'cost', label: 'Cost', icon: DollarSign },
  { id: 'development', label: 'Development', icon: TrendingUp },
  { id: 'memory', label: 'Memory', icon: Database },
  { id: 'skills', label: 'Skills', icon: Package },
  { id: 'hardening', label: 'Hardening', icon: Lock },
  { id: 'lab', label: 'Lab', icon: FlaskConical },
]

export function MCTabBar({ activeTab, onChange }) {
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
      </nav>
    </>
  )
}
