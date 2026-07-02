import { useEffect, useRef, useState } from 'react'
import { useSettings } from '../../hooks/useSettings'
import { fetchPresenceState, type PresenceState } from '../../lib/presenceApi'
import { PresenceOrb, type OrbStyle } from '../PresenceOrb'

const STYLES: { key: OrbStyle; label: string }[] = [
  { key: 'reactor', label: 'Arc-reactor' },
  { key: 'core', label: 'Energi-kerne' },
  { key: 'hud', label: 'Holografisk HUD' },
  { key: 'wave', label: 'Stemme-væsen' },
]

const ENABLE_KEY = 'jarvis.presence.enabled'
const STYLE_KEY = 'jarvis.presence.style'

/**
 * Spec E / E1 — orb-tieren i operator/Miljø-feltet. OPT-IN (default fra), aldrig påtvunget.
 * Rendrer Jarvis' tilstedeværelse client-side, drevet af Centralens ÆGTE valens (/presence/state).
 * Ingen server-pixels. 3D-ansigt/MetaHuman-tiers kommer senere (hardware-gated).
 */
export function PresenceSection() {
  const { settings } = useSettings()
  const [enabled, setEnabled] = useState<boolean>(() => localStorage.getItem(ENABLE_KEY) === '1')
  const [style, setStyle] = useState<OrbStyle>(() => (localStorage.getItem(STYLE_KEY) as OrbStyle) || 'reactor')
  const [state, setState] = useState<PresenceState | null>(null)
  const timer = useRef<ReturnType<typeof setInterval> | null>(null)

  useEffect(() => { localStorage.setItem(ENABLE_KEY, enabled ? '1' : '0') }, [enabled])
  useEffect(() => { localStorage.setItem(STYLE_KEY, style) }, [style])

  useEffect(() => {
    if (!enabled || !settings) { if (timer.current) clearInterval(timer.current); return }
    const cfg = { apiBaseUrl: settings.apiBaseUrl, authToken: settings.authToken }
    let alive = true
    const tick = async () => { const s = await fetchPresenceState(cfg); if (alive) setState(s) }
    void tick()
    timer.current = setInterval(tick, 4000)
    return () => { alive = false; if (timer.current) clearInterval(timer.current) }
  }, [enabled, settings?.apiBaseUrl, settings?.authToken])

  const valence = state?.valence || { tone: 'neutral', score: 0, intensity: 0.3 }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div>
          <div style={{ fontWeight: 500 }}>Tilstedeværelse</div>
          <div style={{ fontSize: 13, opacity: 0.7 }}>
            Et ansigt for Jarvis — drevet af hans ægte følte tilstand. Opt-in, kører på din maskine.
          </div>
        </div>
        <label style={{ display: 'inline-flex', alignItems: 'center', gap: 8, cursor: 'pointer' }}>
          <input type="checkbox" checked={enabled} onChange={(e) => setEnabled(e.target.checked)} />
          <span style={{ fontSize: 13 }}>{enabled ? 'Til' : 'Fra'}</span>
        </label>
      </div>

      {enabled && (
        <>
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
            {STYLES.map((s) => (
              <button key={s.key} onClick={() => setStyle(s.key)}
                style={{
                  padding: '6px 12px', borderRadius: 20, fontSize: 13, cursor: 'pointer',
                  border: style === s.key ? '1px solid transparent' : '1px solid rgba(140,180,255,.3)',
                  background: style === s.key ? '#378add' : 'transparent',
                  color: style === s.key ? '#fff' : 'inherit',
                }}>{s.label}</button>
            ))}
          </div>

          <PresenceOrb style={style} valence={valence} height={220} />

          <div style={{ fontSize: 13, opacity: 0.85, lineHeight: 1.6 }}>
            {state?.self?.describe
              ? <span>{state.self.describe}{state.self.il ? <span style={{ opacity: 0.6 }}>{`  [${state.self.il}]`}</span> : null}</span>
              : <span style={{ opacity: 0.6 }}>Læser hans tilstand…</span>}
          </div>
          <div style={{ fontSize: 12, opacity: 0.5 }}>
            Tier: orb. 3D-ansigt og foto-real (MetaHuman) kommer — kun hvis din maskine kan.
          </div>
        </>
      )}
    </div>
  )
}
