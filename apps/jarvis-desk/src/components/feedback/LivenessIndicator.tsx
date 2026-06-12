import { JarvisRing } from '../shell/JarvisRing'

/** Vedvarende liveness-linje (som Claude): Jarvis' ring står ALTID nederst i
 *  transcript'en — drejer + viser working-step og tid mens han arbejder, og
 *  bliver stående stille med "klar" når turen er slut. Density-aware. */
export function LivenessIndicator({
  status,
  elapsedMs,
  density,
  workingStep,
}: {
  status: string
  elapsedMs: number
  density: 'compact' | 'full'
  workingStep?: string | null
}) {
  const working = status === 'working'
  const tone = working ? 'working' : status === 'error' || status === 'interrupted' ? 'error' : 'idle'
  const s = Math.floor(elapsedMs / 1000)
  const t = `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`
  const label = working
    ? `${workingStep || 'arbejder'} — ${t}`
    : tone === 'error' ? 'afbrudt' : 'klar'
  return (
    <div className={`liveness liveness-${density} ${working ? 'is-working' : 'is-idle'}`}>
      <JarvisRing size={14} spinning={working} tone={tone} />
      <span className="liveness-label">{label}</span>
    </div>
  )
}
