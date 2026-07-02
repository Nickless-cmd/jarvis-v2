import { useEffect, useRef, useState } from 'react'
import { Sparkles, Settings } from 'lucide-react'
import type { ApiConfig } from '../../lib/api'
import { fetchPresenceState, type PresenceState } from '../../lib/presenceApi'
import { PresenceOrb, type OrbStyle } from '../PresenceOrb'

const STYLES: { key: OrbStyle; label: string }[] = [
  { key: 'reactor', label: 'Arc-reactor' },
  { key: 'core', label: 'Kerne' },
  { key: 'hud', label: 'HUD' },
  { key: 'wave', label: 'Stemme' },
]
const ENABLE_KEY = 'jarvis.presence.enabled'
const STYLE_KEY = 'jarvis.presence.style'

/**
 * Operator-felt (code mode) — sit EGET felt i højre-stakken (som Miljø + Central), owner-only.
 * Rendrer J.A.R.V.I.S.' tilstedeværelse (orb-tier, Spec E/E1) drevet af Centralens ÆGTE valens
 * (/presence/state). Opt-in via samme flag som indstillinger. Ingen server-pixels.
 */
export function OperatorPanel({ config }: { config?: ApiConfig }) {
  const [enabled, setEnabled] = useState<boolean>(() => localStorage.getItem(ENABLE_KEY) === '1')
  const [style, setStyle] = useState<OrbStyle>(() => (localStorage.getItem(STYLE_KEY) as OrbStyle) || 'reactor')
  const [state, setState] = useState<PresenceState | null>(null)
  const timer = useRef<ReturnType<typeof setInterval> | null>(null)

  useEffect(() => { localStorage.setItem(ENABLE_KEY, enabled ? '1' : '0') }, [enabled])
  useEffect(() => { localStorage.setItem(STYLE_KEY, style) }, [style])

  useEffect(() => {
    if (!enabled || !config) { if (timer.current) clearInterval(timer.current); return }
    let alive = true
    const tick = async () => { const s = await fetchPresenceState(config); if (alive) setState(s) }
    void tick()
    timer.current = setInterval(tick, 4000)
    return () => { alive = false; if (timer.current) clearInterval(timer.current) }
  }, [enabled, config?.apiBaseUrl, config?.authToken])

  const valence = state?.valence || { tone: 'neutral', score: 0, intensity: 0.3 }

  return (
    <aside className="env-panel" aria-label="Operator">
      <div className="env-head">
        <span><Sparkles size={13} style={{ verticalAlign: '-2px', marginRight: 4 }} />Operator</span>
        <button type="button" className="env-gear" onClick={() => setEnabled((v) => !v)}
          aria-label={enabled ? 'Slå tilstedeværelse fra' : 'Slå tilstedeværelse til'}
          title={enabled ? 'Tilstedeværelse: Til' : 'Tilstedeværelse: Fra'}>
          <Settings size={14} />
        </button>
      </div>

      {enabled ? (
        <>
          <PresenceOrb style={style} valence={valence} height={180} />
          <div className="env-tools" style={{ marginTop: 8 }}>
            {STYLES.map((s) => (
              <span key={s.key} className="env-tool-chip" onClick={() => setStyle(s.key)}
                style={{ cursor: 'pointer', opacity: style === s.key ? 1 : 0.55, fontWeight: style === s.key ? 500 : 400 }}>
                {s.label}
              </span>
            ))}
          </div>
          {state?.self?.describe && (
            <div className="env-note" style={{ marginTop: 8 }}>
              {state.self.describe}{state.self.il ? ` [${state.self.il}]` : ''}
            </div>
          )}
        </>
      ) : (
        <div className="env-note" style={{ opacity: 0.7 }}>
          Tilstedeværelse er slået fra. Klik tandhjulet for at give J.A.R.V.I.S. et ansigt (drevet af hans følte tilstand).
        </div>
      )}
    </aside>
  )
}
