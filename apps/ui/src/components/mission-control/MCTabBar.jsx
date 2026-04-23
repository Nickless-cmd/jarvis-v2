import { Activity, Eye, Bot, Brain, DollarSign, Layers, Shield, TrendingUp, Database, Package, Lock, FlaskConical, Fingerprint, Heart, Users, Crown, Hourglass, Anchor, Network, ShieldCheck } from 'lucide-react'
import { s, T } from '../../shared/theme/tokens'

const ALL_TABS = [
  { id: 'overview', label: 'Overview', icon: Activity },
  { id: 'operations', label: 'Operations', icon: Bot },
  { id: 'observability', label: 'Observability', icon: Eye },
  { id: 'living-mind', label: 'Living Mind', icon: Brain },
  { id: 'soul', label: 'Soul', icon: Hourglass },
  { id: 'proprioception', label: 'Proprioception', icon: Anchor },
  { id: 'threads', label: 'Threads', icon: Network },
  { id: 'cost', label: 'Cost', icon: DollarSign },
  { id: 'memory', label: 'Memory', icon: Database },
  { id: 'agents', label: 'Agents', icon: Users },
  { id: 'council', label: 'Council', icon: Crown },
  { id: 'cognitive-state', label: 'Cognitive', icon: Fingerprint },
  { id: 'relationship', label: 'Relationship', icon: Heart },
  { id: 'self-review', label: 'Self-Review', icon: Shield },
  { id: 'continuity', label: 'Continuity', icon: Layers },
  { id: 'development', label: 'Development', icon: TrendingUp },
  { id: 'skills', label: 'Skills', icon: Package },
  { id: 'hardening', label: 'Hardening', icon: Lock },
  { id: 'lab', label: 'Lab', icon: FlaskConical },
]

export function MCTabBar({ activeTab, onChange }) {
  return (
    <div
      style={s({
        display: 'flex',
        alignItems: 'center',
        flexWrap: 'wrap',
        rowGap: 2,
        padding: '4px 24px 0',
        background: T.headerGlass,
        backdropFilter: 'blur(12px)',
        borderBottom: `1px solid ${T.border0}`,
        flexShrink: 0,
        gap: 2,
      })}
    >
      {ALL_TABS.map(({ id, label, icon: Icon }) => {
        const active = activeTab === id
        return (
          <button
            key={id}
            onClick={() => onChange(id)}
            style={s({
              display: 'flex',
              alignItems: 'center',
              gap: 6,
              padding: '10px 12px',
              background: 'transparent',
              border: 'none',
              borderBottom: `2px solid ${active ? T.accent : 'transparent'}`,
              color: active ? T.accentText : T.text3,
              cursor: 'pointer',
              fontSize: 11,
              fontFamily: T.sans,
              fontWeight: active ? 500 : 400,
              transition: 'all 0.15s',
              whiteSpace: 'nowrap',
            })}
            onMouseEnter={(e) => !active && (e.currentTarget.style.color = T.text2)}
            onMouseLeave={(e) => !active && (e.currentTarget.style.color = active ? T.accentText : T.text3)}
          >
            <Icon size={12} />
            {label}
          </button>
        )
      })}
    </div>
  )
}
