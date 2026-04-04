import { Activity, Brain, Compass, Eye, Gauge, MessageCircle } from 'lucide-react'

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

  // Real affective meta state fields from the API
  const affectiveState = affective.state || 'unknown'
  const bearing = affective.bearing || 'unknown'
  const monitoringMode = affective.monitoring_mode || 'unknown'
  const reflectiveLoad = affective.reflective_load || 'unknown'

  // Inner voice from protected_inner_voice.current
  const voiceData = jarvisSurface?.protectedVoice?.current || {}
  const innerVoiceText = voiceData.voice_line || voiceData.current_concern || 'ingen tanker endnu...'
  const voiceMood = voiceData.mood_tone || null

  return (
    <aside className="chat-support-rail">
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
