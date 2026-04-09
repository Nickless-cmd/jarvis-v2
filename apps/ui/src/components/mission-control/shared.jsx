import { s, T, mono } from '../../shared/theme/tokens'

export function Chip({ children, color = T.text3, bg }) {
  return (
    <span
      style={s({
        ...mono,
        fontSize: 9,
        padding: '2px 7px',
        borderRadius: 10,
        background: bg || `${color}18`,
        border: `1px solid ${color}35`,
        color,
        letterSpacing: '0.05em',
      })}
    >
      {children}
    </span>
  )
}

export function StatusDot({ status }) {
  const colors = { ok: T.green, warn: T.amber, error: T.red, firing: T.red, idle: T.text3 }
  const color = colors[status] || T.text3

  return (
    <div
      style={s({
        width: 7,
        height: 7,
        borderRadius: '50%',
        background: color,
        boxShadow: status !== 'idle' ? `0 0 6px ${color}` : 'none',
        flexShrink: 0,
      })}
    />
  )
}

export function MetricCard({ label, value, sub, color, icon: Icon, alert }) {
  return (
    <div
      style={s({
        padding: '12px 14px',
        background: T.cardGradient,
        border: `1px solid ${alert ? `${T.amber}40` : T.border0}`,
        borderRadius: 10,
        flex: 1,
        minWidth: 100,
        boxShadow: alert ? `0 0 12px ${T.amber}20` : T.shadowSm,
      })}
    >
      <div style={s({ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 6 })}>
        <span style={s({ ...mono, fontSize: 9, color: T.text3, letterSpacing: '0.1em', textTransform: 'uppercase' })}>{label}</span>
        {Icon && <Icon size={11} color={T.text3} />}
      </div>
      <div style={s({ fontSize: 22, fontWeight: 400, color: color || T.text1, letterSpacing: '-0.02em' })}>{value}</div>
      {sub && <div style={s({ ...mono, fontSize: 9, color: T.text3, marginTop: 3 })}>{sub}</div>}
    </div>
  )
}

export function SectionTitle({ children }) {
  return (
    <div style={s({ ...mono, fontSize: 9, color: T.text3, letterSpacing: '0.1em', textTransform: 'uppercase', marginBottom: 10 })}>
      {children}
    </div>
  )
}

export function HintDot({ text, label = '?' }) {
  const hint = String(text || '').trim()
  if (!hint) return null
  return (
    <span
      title={hint}
      style={s({
        ...mono,
        display: 'inline-flex',
        alignItems: 'center',
        justifyContent: 'center',
        width: 14,
        height: 14,
        borderRadius: '50%',
        border: `1px solid ${T.border1}`,
        color: T.text3,
        fontSize: 9,
        cursor: 'help',
        flexShrink: 0,
      })}
    >
      {label}
    </span>
  )
}

export function SurfaceNotice({ title, children, actions = [] }) {
  return (
    <div
      style={s({
        padding: '10px 12px',
        background: T.bgSurface,
        border: `1px solid ${T.border0}`,
        borderRadius: 10,
      })}
    >
      <div style={s({ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 10 })}>
        <div style={s({ minWidth: 0 })}>
          <div style={s({ ...mono, fontSize: 9, color: T.accentText, letterSpacing: '0.08em', textTransform: 'uppercase', marginBottom: 4 })}>
            {title}
          </div>
          <div style={s({ fontSize: 11, lineHeight: 1.55, color: T.text2 })}>{children}</div>
        </div>
        {actions.length > 0 ? (
          <div style={s({ display: 'flex', gap: 6, flexWrap: 'wrap', justifyContent: 'flex-end' })}>{actions}</div>
        ) : null}
      </div>
    </div>
  )
}

export function ScrollPanel({ children, maxHeight = 180, style = {} }) {
  return (
    <div
      style={s({
        maxHeight,
        overflowX: 'hidden',
        overflowY: 'auto',
        border: `1px solid ${T.border0}`,
        borderRadius: 10,
        padding: 10,
        background: T.bgSurface,
        scrollbarGutter: 'stable',
        ...style,
      })}
    >
      {children}
    </div>
  )
}

export function Card({ children, style = {} }) {
  return (
    <div
      style={s({
        background: T.bgRaised,
        border: `1px solid ${T.border0}`,
        borderRadius: 10,
        padding: '14px 16px',
        ...style,
      })}
    >
      {children}
    </div>
  )
}

export function Btn({ children, onClick, variant = 'ghost', icon: Icon, small, disabled }) {
  const variants = {
    ghost: { background: T.bgOverlay, border: `1px solid ${T.border1}`, color: T.text2 },
    accent: { background: T.accentDim, border: `1px solid ${T.accent}`, color: T.accentText },
    danger: { background: 'rgba(192,80,80,0.1)', border: `1px solid ${T.red}40`, color: T.red },
  }

  const selected = variants[variant] || variants.ghost

  return (
    <button
      onClick={onClick}
      disabled={disabled}
      style={s({
        display: 'flex',
        alignItems: 'center',
        gap: 5,
        padding: small ? '4px 8px' : '6px 12px',
        borderRadius: 7,
        cursor: disabled ? 'not-allowed' : 'pointer',
        fontSize: small ? 10 : 11,
        fontFamily: T.sans,
        opacity: disabled ? 0.5 : 1,
        transition: 'all 0.15s',
        ...selected,
      })}
      onMouseEnter={(e) => !disabled && (e.currentTarget.style.background = T.bgHover)}
      onMouseLeave={(e) => !disabled && (e.currentTarget.style.background = selected.background)}
    >
      {Icon && <Icon size={small ? 10 : 12} />}
      {children}
    </button>
  )
}

/* StatusPill — kept for drawer + tab compatibility */
export function StatusPill({ status }) {
  if (!status) return null
  const normalizedStatus = String(status).toLowerCase().replace(/[-_\s]+/g, '-')
  const colorMap = {
    active: T.accentText,
    idle: T.text3,
    cooling: T.blue,
    blocked: T.red,
    completed: T.green,
    pending: T.amber,
    approved: T.green,
    rejected: T.red,
    proposed: T.blue,
    applied: T.green,
    expired: T.text3,
    failed: T.red,
    running: T.green,
    'in-progress': T.accentText,
    direct: T.accentText,
    careful: T.amber,
    exploratory: T.blue,
    constrained: T.purple,
    corrected: T.red,
  }
  const color = colorMap[normalizedStatus] || T.text2
  return (
    <span
      style={s({
        ...mono,
        display: 'inline-flex',
        alignItems: 'center',
        gap: 4,
        padding: '3px 8px',
        borderRadius: 999,
        fontSize: 9,
        fontWeight: 500,
        textTransform: 'capitalize',
        background: `${color}18`,
        border: `1px solid ${color}30`,
        color,
      })}
    >
      {status}
    </span>
  )
}

/* ListRow — common clickable row used across tabs */
export function ListRow({ children, onClick, active, subtle, staticRow }) {
  return (
    <button
      onClick={onClick}
      style={s({
        width: '100%',
        textAlign: 'left',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        gap: 8,
        padding: '8px 10px',
        borderRadius: 8,
        border: `1px solid ${active ? `${T.accent}40` : T.border0}`,
        background: active ? T.bgOverlay : subtle ? T.bgSurface : T.bgRaised,
        color: T.text1,
        cursor: staticRow ? 'default' : 'pointer',
        transition: 'border-color .14s ease',
      })}
      onMouseEnter={(e) => !staticRow && (e.currentTarget.style.borderColor = `${T.accent}30`)}
      onMouseLeave={(e) => !staticRow && (e.currentTarget.style.borderColor = active ? `${T.accent}40` : T.border0)}
    >
      {children}
    </button>
  )
}

/* CodeCard — monospace content block */
export function CodeCard({ children, tone, style = {} }) {
  const toneColors = { danger: `${T.red}40` }
  return (
    <div
      style={s({
        padding: '10px 12px',
        borderRadius: 8,
        background: T.bgSurface,
        border: `1px solid ${toneColors[tone] || T.border0}`,
        ...mono,
        fontSize: 10,
        color: T.text2,
        whiteSpace: 'pre-wrap',
        wordBreak: 'break-word',
        overflowX: 'auto',
        ...style,
      })}
    >
      {children}
    </div>
  )
}

/* KeyValGrid — two-column grid for detail views */
export function KeyValGrid({ children }) {
  return (
    <div style={s({ display: 'grid', gridTemplateColumns: 'repeat(2, minmax(0, 1fr))', gap: 8 })}>
      {children}
    </div>
  )
}

export function KeyValCell({ label, value, color }) {
  return (
    <div style={s({ padding: 8, background: T.bgOverlay, borderRadius: 6 })}>
      <div style={s({ ...mono, fontSize: 8, color: T.text3, marginBottom: 3 })}>{label}</div>
      <div style={s({ ...mono, fontSize: 11, color: color || T.text1 })}>{value}</div>
    </div>
  )
}

/* EmptyState — consistent empty data message */
export function EmptyState({ title, children }) {
  return (
    <div style={s({ padding: '14px 16px', textAlign: 'center' })}>
      {title && <div style={s({ fontSize: 12, fontWeight: 500, color: T.text2, marginBottom: 4 })}>{title}</div>}
      {children && <div style={s({ fontSize: 11, color: T.text3 })}>{children}</div>}
    </div>
  )
}

/* Skeleton — shimmer loading placeholder */
export function Skeleton({ width = '100%', height = 20, style = {} }) {
  return (
    <div
      style={s({
        width,
        height,
        borderRadius: 8,
        background: `linear-gradient(90deg, ${T.bgOverlay} 25%, ${T.bgHover} 50%, ${T.bgOverlay} 75%)`,
        backgroundSize: '200% 100%',
        animation: 'shimmer 1.5s ease-in-out infinite',
        ...style,
      })}
    />
  )
}

const shimmerKeyframes = `
  @keyframes shimmer {
    0% { background-position: 200% 0; }
    100% { background-position: -200% 0; }
  }
`

if (typeof document !== 'undefined') {
  const styleSheet = document.createElement('style')
  styleSheet.textContent = shimmerKeyframes
  document.head.appendChild(styleSheet)
}
