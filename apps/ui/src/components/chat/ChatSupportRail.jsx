import { Activity, Battery, Compass, Eye, Frown, Gauge, Lightbulb, Smile } from 'lucide-react'

function PanelSection({ title, children }) {
  return (
    <div className="rail-panel-section">
      <div className="rail-panel-title mono">{title}</div>
      {children}
    </div>
  )
}

/**
 * Derive emotional percentages from the real affective meta state.
 *
 * The backend produces categorical states (settled, attentive, reflective,
 * tense, burdened) and bearings (even, forward, inward, held, taut,
 * compressed).  We map those to four intuitive gauges so the sidebar
 * shows something immediately legible.
 */
function deriveEmotions(affective) {
  const state = affective.state || 'unknown'
  const bearing = affective.bearing || 'unknown'
  const reflectiveLoad = affective.reflective_load || 'low'

  // Confidence: high when settled/forward, low when burdened
  const confidenceMap = { settled: 0.85, attentive: 0.70, reflective: 0.60, tense: 0.35, burdened: 0.15, unknown: 0.50 }
  const bearingBoost = { even: 0.05, forward: 0.10, inward: -0.05, held: -0.05, taut: -0.10, compressed: -0.15 }
  const confidence = Math.min(1, Math.max(0, (confidenceMap[state] ?? 0.50) + (bearingBoost[bearing] ?? 0)))

  // Curiosity: high when reflective/attentive, low when burdened
  const curiosityMap = { settled: 0.40, attentive: 0.65, reflective: 0.80, tense: 0.30, burdened: 0.10, unknown: 0.30 }
  const loadBoost = { low: 0, medium: 0.10, high: 0.15 }
  const curiosity = Math.min(1, Math.max(0, (curiosityMap[state] ?? 0.30) + (loadBoost[reflectiveLoad] ?? 0)))

  // Frustration: high when tense/burdened
  const frustrationMap = { settled: 0.05, attentive: 0.10, reflective: 0.15, tense: 0.55, burdened: 0.80, unknown: 0.10 }
  const frustration = Math.min(1, Math.max(0, frustrationMap[state] ?? 0.10))

  // Fatigue: derived from reflective load + state
  const fatigueBase = { settled: 0.10, attentive: 0.25, reflective: 0.35, tense: 0.50, burdened: 0.75, unknown: 0.20 }
  const fatigueLoadBoost = { low: 0, medium: 0.10, high: 0.20 }
  const fatigue = Math.min(1, Math.max(0, (fatigueBase[state] ?? 0.20) + (fatigueLoadBoost[reflectiveLoad] ?? 0)))

  return { confidence, curiosity, frustration, fatigue }
}

export function ChatSupportRail({ session, selection, isStreaming, jarvisSurface }) {
  const affective = jarvisSurface?.affectiveMetaState || {}
  const summary = jarvisSurface?.summary || {}
  const memorySummary = summary?.retained_memory || {}

  // Real affective meta state fields from the API
  const affectiveState = affective.state || 'unknown'
  const bearing = affective.bearing || 'unknown'
  const monitoringMode = affective.monitoring_mode || 'unknown'
  const reflectiveLoad = affective.reflective_load || 'unknown'

  // Derived emotional gauges
  const emotions = deriveEmotions(affective)
  const emotionCards = [
    { label: 'CONF', value: emotions.confidence, color: '#4caf82', icon: Smile },
    { label: 'CURIO', value: emotions.curiosity, color: '#d4963a', icon: Lightbulb },
    { label: 'FRUS', value: emotions.frustration, color: '#c05050', icon: Frown },
    { label: 'FATIGUE', value: emotions.fatigue, color: '#4a80c0', icon: Battery },
  ]

  // Inner voice from protected_inner_voice.current
  const voiceData = jarvisSurface?.protectedVoice?.current || {}
  const innerVoiceText = voiceData.voice_line || voiceData.current_concern || 'ingen tanker endnu...'
  const voiceMood = voiceData.mood_tone || null

  return (
    <aside className="chat-support-rail">
      <PanelSection title="Emotional State">
        <div className="emotion-grid">
          {emotionCards.map(({ label, value, color, icon: Icon }) => {
            const pct = Math.round(value * 100)
            return (
              <div key={label} className="emotion-card">
                <div className="emotion-card-header">
                  <Icon size={9} color={color} />
                  <span className="mono">{label}</span>
                </div>
                <div className="emotion-card-value mono">{pct}%</div>
                <div className="progress-bar">
                  <div className="progress-bar-fill" style={{ width: `${pct}%`, background: color }} />
                </div>
              </div>
            )
          })}
        </div>
      </PanelSection>

      <PanelSection title="Affective State">
        <div className="rail-affective-grid">
          {[
            { label: 'STATE', value: affectiveState, icon: Activity, color: '#5ab8a0' },
            { label: 'BEARING', value: bearing, icon: Compass, color: '#d4963a' },
            { label: 'MONITOR', value: monitoringMode, icon: Eye, color: '#4a80c0' },
            { label: 'REFLECT', value: reflectiveLoad, icon: Gauge, color: '#8b6cc0' },
          ].map(({ label, value, icon: Icon, color }) => (
            <div key={label} className="rail-affective-card">
              <div className="rail-affective-card-header">
                <Icon size={9} color={color} />
                <span className="mono">{label}</span>
              </div>
              <div className="rail-affective-card-value mono" style={{ color }}>{value}</div>
            </div>
          ))}
        </div>
        {affective.summary ? (
          <div className="rail-affective-summary mono">{affective.summary}</div>
        ) : null}
      </PanelSection>

      <PanelSection title="Memory">
        {[
          { label: 'Kind', value: memorySummary.kind || 'unknown', color: '#5ab8a0' },
          { label: 'Focus', value: memorySummary.focus || 'none', color: '#8b909e' },
        ].map(({ label, value, color }) => (
          <div key={label} className="rail-memory-row">
            <span>{label}</span>
            <span className="mono" style={{ color }}>{value}</span>
          </div>
        ))}
      </PanelSection>

      <PanelSection title="Inner Voice">
        <div className="rail-inner-voice">
          {voiceMood ? (
            <div className="rail-inner-voice-mood mono">{voiceMood}</div>
          ) : null}
          <span>{innerVoiceText}</span>
        </div>
      </PanelSection>
    </aside>
  )
}
