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
}: {
  tokens: number
  compactAt: number
  size?: number
}) {
  if (!compactAt || compactAt <= 0 || tokens <= 0) return null
  const frac = Math.min(1, tokens / compactAt)
  const pct = Math.round(frac * 100)

  const color =
    frac >= 1 ? '#ef4444' : frac >= 0.85 ? '#ef4444' : frac >= 0.6 ? '#eab308' : '#5b9bd5'
  const atCompact = frac >= 1

  const stroke = 2
  const r = (size - stroke) / 2
  const c = 2 * Math.PI * r
  const dash = c * frac

  const kTokens = (n: number) => (n >= 1000 ? `${(n / 1000).toFixed(n >= 10000 ? 0 : 1)}k` : `${n}`)

  return (
    <span
      className={`context-ring ${atCompact ? 'at-compact' : ''}`}
      title={`Kontekst: ${pct}% (${kTokens(tokens)} / ${kTokens(compactAt)} før autocompact)`}
      aria-label={`Kontekst ${pct} procent fyldt`}
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
