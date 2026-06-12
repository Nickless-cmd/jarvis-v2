/** Jarvis' brudte ring som genbrugeligt mærke. Drejer når `spinning`, ellers
 *  står den stille. Bruges både i header (PresenceDot) og liveness-linjen. */
export function JarvisRing({
  size = 15,
  spinning = false,
  tone = 'idle',
}: {
  size?: number
  spinning?: boolean
  tone?: 'idle' | 'working' | 'error'
}) {
  const stroke = tone === 'error' ? 'var(--error-fg)' : tone === 'working' ? 'var(--warn-fg)' : 'var(--accent)'
  return (
    <span className={`jarvis-ring ${spinning ? 'spinning' : ''} tone-${tone}`} aria-hidden="true">
      <svg viewBox="0 0 100 100" width={size} height={size}>
        <circle
          cx="50" cy="50" r="34" fill="none" stroke={stroke} strokeWidth="11"
          strokeLinecap="round" strokeDasharray="158 56" transform="rotate(-58 50 50)"
        />
      </svg>
    </span>
  )
}
