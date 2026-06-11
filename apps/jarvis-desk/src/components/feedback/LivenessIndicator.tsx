/** Rolig liveness-indikator mens Jarvis arbejder. Density-aware: compact (Chat)
 *  vs full (Code). Viser forløbet tid m:ss. */
export function LivenessIndicator({
  status,
  elapsedMs,
  density,
}: {
  status: string
  elapsedMs: number
  density: 'compact' | 'full'
}) {
  if (status !== 'working') return null
  const s = Math.floor(elapsedMs / 1000)
  const t = `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`
  return (
    <div className={`liveness liveness-${density}`}>
      <span className="liveness-dot" /> arbejder — {t}
    </div>
  )
}
