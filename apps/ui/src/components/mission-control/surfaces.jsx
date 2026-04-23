import { useEffect, useState } from 'react'
import { s, T, mono } from '../../shared/theme/tokens'
import { backend } from '../../lib/adapters'

/* ─── Shared data hook ──────────────────────────────────────────────── */

export function useCognitiveSurfaces(refreshMs = 60000) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    let cancelled = false
    async function load() {
      try {
        const result = await backend.getCognitiveSurfaces()
        if (!cancelled) {
          setData(result?.surfaces || {})
          setError(null)
        }
      } catch (err) {
        if (!cancelled) setError(err)
      }
      if (!cancelled) setLoading(false)
    }
    load()
    const interval = setInterval(load, refreshMs)
    return () => {
      cancelled = true
      clearInterval(interval)
    }
  }, [refreshMs])

  return { surfaces: data, loading, error }
}

/* ─── Layout primitives ─────────────────────────────────────────────── */

export function SurfaceGrid({ children }) {
  return (
    <div
      style={s({
        padding: '16px 20px',
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(340px, 1fr))',
        gap: 10,
      })}
    >
      {children}
    </div>
  )
}

export function Section({ icon: Icon, title, active, children, subtitle }) {
  return (
    <div
      style={s({
        background: T.bgRaised,
        border: `1px solid ${T.border0}`,
        borderRadius: T.r_sm,
        padding: 14,
        opacity: active === false ? 0.75 : 1,
      })}
    >
      <div style={s({ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 10 })}>
        {Icon ? <Icon size={13} style={{ color: active === false ? T.text3 : T.accent }} /> : null}
        <span
          style={s({
            ...mono,
            fontSize: 9,
            textTransform: 'uppercase',
            letterSpacing: '0.08em',
            color: T.text2,
            flex: 1,
          })}
        >
          {title}
        </span>
        {active === false ? (
          <span style={s({ ...mono, fontSize: 8, color: T.text3 })}>idle</span>
        ) : null}
      </div>
      {subtitle ? (
        <div style={s({ ...mono, fontSize: 10, color: T.text2, marginBottom: 8 })}>{subtitle}</div>
      ) : null}
      {children}
    </div>
  )
}

export function KV({ label, value, accent, mutedWhenEmpty = true }) {
  if (mutedWhenEmpty && (value === undefined || value === null || value === '')) {
    return (
      <div style={s({ display: 'flex', justifyContent: 'space-between', padding: '3px 0', borderBottom: `1px solid ${T.border0}` })}>
        <span style={s({ ...mono, fontSize: 10, color: T.text3 })}>{label}</span>
        <span style={s({ ...mono, fontSize: 10, color: T.text3 })}>—</span>
      </div>
    )
  }
  let display = value
  if (typeof value === 'number') {
    display = Number.isFinite(value) ? value : '—'
  } else if (Array.isArray(value)) {
    display = value.length ? value.slice(0, 4).join(', ') + (value.length > 4 ? '…' : '') : '—'
  } else if (typeof value === 'object' && value !== null) {
    display = JSON.stringify(value).slice(0, 80)
  } else if (typeof value === 'boolean') {
    display = value ? 'ja' : 'nej'
  } else {
    display = String(value ?? '—')
  }
  return (
    <div style={s({ display: 'flex', justifyContent: 'space-between', padding: '3px 0', borderBottom: `1px solid ${T.border0}`, gap: 12 })}>
      <span style={s({ ...mono, fontSize: 10, color: T.text3, flexShrink: 0 })}>{label}</span>
      <span style={s({ ...mono, fontSize: 10, color: accent ? T.accentText : T.text1, textAlign: 'right', wordBreak: 'break-word' })}>
        {display}
      </span>
    </div>
  )
}

export function Summary({ text }) {
  if (!text) return null
  return (
    <div
      style={s({
        ...mono,
        fontSize: 10,
        color: T.text2,
        background: T.bgOverlay,
        padding: '6px 8px',
        borderRadius: 4,
        marginBottom: 8,
      })}
    >
      {text}
    </div>
  )
}

export function EmptySurface({ name }) {
  return (
    <div style={s({ ...mono, fontSize: 10, color: T.text3 })}>
      Surface {`"${name}"`} er ikke tilgængelig
    </div>
  )
}

export function JsonBadges({ data, max = 6 }) {
  if (!data || typeof data !== 'object' || Object.keys(data).length === 0) {
    return <span style={s({ ...mono, fontSize: 10, color: T.text3 })}>—</span>
  }
  const entries = Object.entries(data).slice(0, max)
  return (
    <div style={s({ display: 'flex', flexWrap: 'wrap', gap: 6, marginTop: 4 })}>
      {entries.map(([k, v]) => {
        let val = v
        if (typeof v === 'number') val = v.toFixed(3)
        else if (typeof v === 'object' && v !== null) val = JSON.stringify(v).slice(0, 20)
        return (
          <span
            key={k}
            style={s({
              ...mono,
              fontSize: 9,
              color: T.text2,
              background: T.bgOverlay,
              padding: '2px 6px',
              borderRadius: 4,
            })}
          >
            {k}={String(val)}
          </span>
        )
      })}
    </div>
  )
}
