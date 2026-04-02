import { Smile, Frown, Lightbulb, Battery } from 'lucide-react'

function PanelSection({ title, children }) {
  return (
    <div className="rail-panel-section">
      <div className="rail-panel-title mono">{title}</div>
      {children}
    </div>
  )
}

export function ChatSupportRail({ session, selection, isStreaming, jarvisSurface }) {
  const affective = jarvisSurface?.affectiveMetaState || {}
  const summary = jarvisSurface?.summary || {}
  const memorySummary = summary?.retained_memory || {}

  const emotions = [
    { label: 'CONF', value: affective.confidenceLevel || 0, color: '#4caf82', icon: Smile },
    { label: 'CURIO', value: affective.curiosityLevel || 0, color: '#d4963a', icon: Lightbulb },
    { label: 'FRUS', value: affective.frustrationLevel || 0, color: '#c05050', icon: Frown },
    { label: 'FATIGUE', value: affective.fatigueLevel || 0, color: '#4a80c0', icon: Battery },
  ]

  const innerVoice = jarvisSurface?.protectedVoice?.preview || 'ingen tanker endnu...'

  return (
    <aside className="chat-support-rail">
      <PanelSection title="Emotional State">
        <div className="emotion-grid">
          {emotions.map(({ label, value, color, icon: Icon }) => {
            const pct = typeof value === 'number' && value <= 1 ? value * 100 : Number(value) || 0
            return (
              <div key={label} className="emotion-card">
                <div className="emotion-card-header">
                  <Icon size={9} color={color} />
                  <span className="mono">{label}</span>
                </div>
                <div className="emotion-card-value mono">{pct.toFixed(0)}%</div>
                <div className="progress-bar">
                  <div className="progress-bar-fill" style={{ width: `${pct}%`, background: color }} />
                </div>
              </div>
            )
          })}
        </div>
      </PanelSection>

      <PanelSection title="Skills">
        <div className="rail-skill-list">
          {(jarvisSurface?.skills || []).slice(0, 6).map(sk => (
            <div key={sk.name || sk} className="rail-skill-item">
              <div className={`rail-skill-dot ${sk.status === 'active' || sk.status === 'registered' ? 'active' : ''}`} />
              <span className="mono">{sk.name || sk}</span>
              <span className="rail-skill-uses mono">{sk.uses || 0}</span>
            </div>
          ))}
          {!(jarvisSurface?.skills || []).length && (
            <span className="rail-empty mono">no skills loaded</span>
          )}
        </div>
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
          <span>{innerVoice}</span>
        </div>
      </PanelSection>
    </aside>
  )
}
