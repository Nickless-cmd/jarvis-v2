import { Activity, Eye, Bot, Brain, DollarSign, Layers, Shield, TrendingUp, Database, Package, Lock, FlaskConical, Fingerprint, Heart } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { s, T } from '../../shared/theme/tokens'

const PRIMARY_TABS = [
  { id: 'overview', label: 'Overview', icon: Activity },
  { id: 'operations', label: 'Operations', icon: Bot },
  { id: 'observability', label: 'Observability', icon: Eye },
  { id: 'living-mind', label: 'Living Mind', icon: Brain },
  { id: 'cost', label: 'Cost', icon: DollarSign },
  { id: 'memory', label: 'Memory', icon: Database },
]

const MORE_TABS = [
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
  const [moreOpen, setMoreOpen] = useState(false)
  const moreRef = useRef(null)

  useEffect(() => {
    if (!moreOpen) return

    const onPointerDown = (event) => {
      if (!moreRef.current) return
      if (!moreRef.current.contains(event.target)) setMoreOpen(false)
    }

    const onKeyDown = (event) => {
      if (event.key === 'Escape') setMoreOpen(false)
    }

    window.addEventListener('mousedown', onPointerDown)
    window.addEventListener('keydown', onKeyDown)
    return () => {
      window.removeEventListener('mousedown', onPointerDown)
      window.removeEventListener('keydown', onKeyDown)
    }
  }, [moreOpen])

  const moreTabActive = MORE_TABS.some((tab) => tab.id === activeTab)

  return (
    <div
      style={s({
        display: 'flex',
        alignItems: 'center',
        padding: '0 24px',
        background: T.bgSurface,
        borderBottom: `1px solid ${T.border0}`,
        flexShrink: 0,
        gap: 2,
        overflow: 'visible',
      })}
    >
      {PRIMARY_TABS.map(({ id, label, icon: Icon }) => {
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
            })}
            onMouseEnter={(e) => !active && (e.currentTarget.style.color = T.text2)}
            onMouseLeave={(e) => !active && (e.currentTarget.style.color = active ? T.accentText : T.text3)}
          >
            <Icon size={12} />
            {label}
          </button>
        )
      })}

      <div style={s({ position: 'relative', marginLeft: 2 })} ref={moreRef}>
        <button
          onClick={() => setMoreOpen((value) => !value)}
          style={s({
            display: 'flex',
            alignItems: 'center',
            gap: 6,
            padding: '10px 12px',
            background: 'transparent',
            border: 'none',
            borderBottom: `2px solid ${moreOpen || moreTabActive ? T.accent : 'transparent'}`,
            color: moreOpen || moreTabActive ? T.accentText : T.text3,
            cursor: 'pointer',
            fontSize: 11,
            fontFamily: T.sans,
            fontWeight: moreOpen || moreTabActive ? 500 : 400,
            whiteSpace: 'nowrap',
          })}
        >
          More
        </button>

        <div
          style={s({
            position: 'absolute',
            top: 36,
            right: 0,
            minWidth: 190,
            maxHeight: 320,
            overflowY: 'auto',
            background: T.bgRaised,
            border: `1px solid ${T.border0}`,
            borderRadius: 8,
            padding: 6,
            display: moreOpen ? 'block' : 'none',
            zIndex: 20,
            boxShadow: '0 12px 28px rgba(0, 0, 0, 0.35)',
          })}
        >
          {MORE_TABS.map(({ id, label, icon: Icon }) => {
            const active = activeTab === id
            return (
              <button
                key={id}
                onClick={() => {
                  onChange(id)
                  setMoreOpen(false)
                }}
                style={s({
                  width: '100%',
                  display: 'flex',
                  alignItems: 'center',
                  gap: 8,
                  padding: '8px 10px',
                  borderRadius: 6,
                  border: 'none',
                  background: active ? T.accentDim : 'transparent',
                  color: active ? T.accentText : T.text2,
                  cursor: 'pointer',
                  fontSize: 11,
                  textAlign: 'left',
                })}
                onMouseEnter={(e) => !active && (e.currentTarget.style.background = T.bgHover)}
                onMouseLeave={(e) => !active && (e.currentTarget.style.background = active ? T.accentDim : 'transparent')}
              >
                <Icon size={12} />
                {label}
              </button>
            )
          })}
        </div>
      </div>
    </div>
  )
}
