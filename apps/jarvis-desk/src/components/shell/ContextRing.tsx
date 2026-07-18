/** Context-ring (#9): viser hvor fyldt samtalens kontekst-vindue er.
 *  blå → gul → rød → autocompact. Kun ægte tal: tokens kommer fra streamens
 *  usage (input + cache), compactAt fra backend-config.
 *
 *  Zoner (af compactAt): <60% blå, <85% gul, <100% rød, ≥100% pulserende rød
 *  (autocompact-zone). */
export function ContextRing({
  tokens,
  compactAt,
  size = 18,
  modelLabel,
  onManualCompact,
}: {
  tokens: number
  compactAt: number
  size?: number
  /** Navnet på den valgte model — vises i tooltip så ringen er gennemsigtig. */
  modelLabel?: string
  /** Når sat: ringen bliver en knap der udløser manuel compaction (Claude-Code /compact). */
  onManualCompact?: () => void
}) {
  if (!compactAt || compactAt <= 0) return null
  const safeTokens = Math.max(0, tokens)
  const frac = Math.min(1, safeTokens / compactAt)
  const pct = Math.round(frac * 100)

  const color =
    frac >= 1 ? '#ef4444' : frac >= 0.85 ? '#ef4444' : frac >= 0.6 ? '#eab308' : '#5b9bd5'
  const atCompact = frac >= 1

  const stroke = 2
  const r = (size - stroke) / 2
  const c = 2 * Math.PI * r
  const dash = c * frac

  const kTokens = (n: number) => (n >= 1000 ? `${(n / 1000).toFixed(n >= 10000 ? 0 : 1)}k` : `${n}`)

  const baseTitle = `${modelLabel ? modelLabel + ' · ' : ''}` + (safeTokens > 0
    ? `Kontekst: ${pct}% (${kTokens(safeTokens)} / ${kTokens(compactAt)} loft)`
    : `Kontekst: tom (loft ${kTokens(compactAt)})`)
  const title = onManualCompact ? `${baseTitle} · klik for at komprimere nu` : baseTitle
  return (
    <span
      className={`context-ring ${atCompact ? 'at-compact' : ''} ${onManualCompact ? 'clickable' : ''}`}
      title={title}
      aria-label={onManualCompact ? `Komprimér kontekst nu (${pct} procent fyldt)` : `Kontekst ${pct} procent fyldt`}
      role={onManualCompact ? 'button' : undefined}
      tabIndex={onManualCompact ? 0 : undefined}
      style={onManualCompact ? { cursor: 'pointer' } : undefined}
      onClick={onManualCompact}
      onKeyDown={onManualCompact ? (e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); onManualCompact() } } : undefined}
    >
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="var(--bg-4)" strokeWidth={stroke} />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          fill="none"
          stroke={color}
          strokeWidth={stroke}
          strokeLinecap="round"
          strokeDasharray={`${dash} ${c}`}
          transform={`rotate(-90 ${size / 2} ${size / 2})`}
        />
      </svg>
    </span>
  )
}
