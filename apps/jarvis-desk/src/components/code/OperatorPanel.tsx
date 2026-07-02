import { useEffect, useRef, useState } from 'react'
import { Sparkles } from 'lucide-react'
import type { ApiConfig } from '../../lib/api'
import { fetchPresenceState, type PresenceState } from '../../lib/presenceApi'
import { PresenceOrb, type OrbStyle } from '../PresenceOrb'

const ENABLE_KEY = 'jarvis.presence.enabled'
const STYLE_KEY = 'jarvis.presence.style'

/** Læs tilstedeværelses-valg fra indstillingerne (PresenceSection ejer disse
 *  nøgler). Operator-feltet HAR ingen egne kontroller — det spejler kun det
 *  brugeren har valgt i indstillingerne. */
function readSettings(): { enabled: boolean; style: OrbStyle } {
  let enabled = false
  let style: OrbStyle = 'reactor'
  try { enabled = localStorage.getItem(ENABLE_KEY) === '1' } catch { /* ignore */ }
  try { style = (localStorage.getItem(STYLE_KEY) as OrbStyle) || 'reactor' } catch { /* ignore */ }
  return { enabled, style }
}

/**
 * Operator-felt (code mode) — sit EGET felt i højre-stakken (som Miljø + Central),
 * owner-only. Rendrer KUN den orb-stil brugeren har valgt i indstillingerne, drevet
 * af Centralens ÆGTE valens (/presence/state) — det afspejler hvad der sker i ham.
 * Ingen egne kontroller, ingen selv-beskrivende tekst. Ingen server-pixels.
 */
export function OperatorPanel({ config }: { config?: ApiConfig }) {
  const [{ enabled, style }, setSettings] = useState(readSettings)
  const [state, setState] = useState<PresenceState | null>(null)
  const timer = useRef<ReturnType<typeof setInterval> | null>(null)

  useEffect(() => {
    let alive = true
    const tick = async () => {
      // Gen-læs indstillingerne hver tick, så et valg i indstillinger slår igennem
      // uden genstart (localStorage deles, men fyrer ikke event i samme vindue).
      const s = readSettings()
      setSettings((prev) => (prev.enabled === s.enabled && prev.style === s.style ? prev : s))
      if (!s.enabled || !config) { if (alive) setState(null); return }
      const st = await fetchPresenceState(config)
      if (alive) setState(st)
    }
    void tick()
    timer.current = setInterval(tick, 4000)
    return () => { alive = false; if (timer.current) clearInterval(timer.current) }
  }, [config?.apiBaseUrl, config?.authToken])

  const valence = state?.valence || { tone: 'neutral', score: 0, intensity: 0.3 }

  return (
    <aside className="env-panel" aria-label="Operator">
      <div className="env-head">
        <span><Sparkles size={13} style={{ verticalAlign: '-2px', marginRight: 4 }} />Operator</span>
      </div>

      {enabled ? (
        <PresenceOrb style={style} valence={valence} height={180} />
      ) : (
        <div className="env-note" style={{ opacity: 0.7 }}>
          Slå tilstedeværelse til i Indstillinger for at give J.A.R.V.I.S. et ansigt.
        </div>
      )}
    </aside>
  )
}
