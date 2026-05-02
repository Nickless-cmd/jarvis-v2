import { Activity, Eye, Bot, Brain, Database, Package, Lock, FlaskConical, Heart, Crown, Anchor, Network, ShieldCheck, Zap } from 'lucide-react'
import { s, T } from '../../shared/theme/tokens'

const ALL_TABS = [
  { id: 'overview', label: 'Overview', icon: Activity },
  { id: 'operations', label: 'Ops', icon: Bot },
  { id: 'observability', label: 'Observability', icon: Eye },
  { id: 'mind', label: 'Mind', icon: Brain },
  { id: 'proprioception', label: 'Proprioception', icon: Anchor },
  { id: 'threads', label: 'Threads', icon: Network },
  { id: 'memory', label: 'Memory', icon: Database },
  { id: 'council', label: 'Council', icon: Crown },
  { id: 'relationship', label: 'Relationship', icon: Heart },
  { id: 'reflection', label: 'Reflection', icon: Eye },
  { id: 'skills', label: 'Skills', icon: Package },
  { id: 'balancer', label: 'Balancer', icon: Zap },
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
