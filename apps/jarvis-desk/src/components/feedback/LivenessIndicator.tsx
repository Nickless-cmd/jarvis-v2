import { useEffect, useState } from 'react'
import { JarvisRing } from '../shell/JarvisRing'
import { LiveVerb } from '../shell/LiveVerb'

/** Skiftende status-verber i Jarvis' stemme (når der ikke er en konkret tool-
 *  handling). Roterer hvert par sekunder så det føles levende. */
const VERBS = ['tænker', 'grunder', 'samler trådene', 'regner den ud', 'vejer mulighederne', 'kigger nærmere']

/** Vedvarende liveness-linje (som Claude): Jarvis' ring står ALTID nederst i
 *  transcript'en — drejer + viser hvad han laver mens han arbejder, og bliver
 *  stående stille med "klar" når turen er slut. "Thinking via <model>"-boilerplate
 *  filtreres væk; uden konkret handling vises et skiftende verbum. */
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

  // Roter verbum hvert 2,5s mens han arbejder.
  const [verbIdx, setVerbIdx] = useState(0)
  useEffect(() => {
    if (!working) return
    const id = setInterval(() => setVerbIdx((i) => (i + 1) % VERBS.length), 2500)
    return () => clearInterval(id)
  }, [working])

  const s = Math.floor(elapsedMs / 1000)
  const t = `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`

  // Konkret tool-handling beholdes; model-boilerplate ("Thinking via …") droppes
  // til fordel for et skiftende verbum.
  const step = (workingStep || '').trim()
  const isBoilerplate = !step || /^thinking via/i.test(step) || /^arbejder$/i.test(step)
  const action = working ? (isBoilerplate ? (VERBS[verbIdx] ?? 'tænker') : step) : tone === 'error' ? 'afbrudt' : 'klar'

  return (
    <div className={`liveness liveness-${density} ${working ? 'is-working' : 'is-idle'}`}>
      <JarvisRing size={14} spinning={working} tone={tone} />
      <span className="liveness-label">
        {working ? <><LiveVerb text={action} /> <span className="liveness-time">· {t}</span></> : action}
      </span>
    </div>
  )
}
