/** Jarvis' presence-mærke: hans brudte ring. ALTID synlig (som Claudes "blomst")
 *  — står stille når intet sker, DREJER rundt mens han arbejder. Erstatter den
 *  forsvindende gule prik. Farve/glød følger status: grøn=klar, gul=arbejder,
 *  rød=fejl/afbrudt. Kun liveness fra StreamContext — ingen affektiv polling. */
export function PresenceDot({ status }: { status: string }) {
  const tone =
    status === 'working' ? 'working' : status === 'error' || status === 'interrupted' ? 'error' : 'idle'
  const stroke = tone === 'error' ? 'var(--error-fg)' : tone === 'working' ? 'var(--warn-fg)' : 'var(--accent)'
  return (
    <span
      className={`presence-mark ${tone}`}
      title={tone === 'working' ? 'Jarvis arbejder…' : tone === 'error' ? 'Afbrudt' : 'Jarvis'}
      aria-label="Jarvis status"
    >
      <svg viewBox="0 0 100 100" width="15" height="15">
        <circle
          cx="50" cy="50" r="34" fill="none" stroke={stroke} strokeWidth="11"
          strokeLinecap="round" strokeDasharray="158 56" transform="rotate(-58 50 50)"
        />
      </svg>
    </span>
  )
}
