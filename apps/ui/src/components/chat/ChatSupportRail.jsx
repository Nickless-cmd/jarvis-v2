import { Activity, Battery, CheckCircle2, Compass, Eye, FileSearch, FolderOpen, Frown, Gauge, Globe, Lightbulb, Loader2, Pencil, ScanSearch, Smile, Terminal } from 'lucide-react'
import { ScrambleText } from './ChatThinking'
import { s, T, mono } from '../../shared/theme/tokens'

function PanelSection({ title, children }) {
  return (
    <div className="rail-panel-section">
      <div className="rail-panel-title mono">{title}</div>
      {children}
    </div>
  )
}

function formatDisk(sizeMb) {
  if (typeof sizeMb !== 'number' || Number.isNaN(sizeMb)) return '--'
  if (sizeMb > 1024) return `${(sizeMb / 1024).toFixed(1)} GB`
  return `${sizeMb.toFixed(0)} MB`
}

function capabilityIcon(mode) {
  if (!mode) return Eye
  if (mode.includes('write') || mode.includes('memory')) return Pencil
  if (mode.includes('exec')) return Terminal
  return Eye
}

function capabilityLabel(item) {
  if (item.target_path) return item.target_path
  if (item.command_text) {
    const cmd = item.command_text
    return cmd.length > 40 ? cmd.slice(0, 37) + '...' : cmd
  }
  return item.capability_name || item.capability_id || 'unknown'
}

function capabilityVerb(item = {}) {
  const capabilityId = String(item.capability_id || '')
  const capabilityName = String(item.capability_name || '')
  const commandText = String(item.command_text || '')
  const targetPath = String(item.target_path || '')
  const source = `${capabilityId} ${capabilityName} ${commandText}`.toLowerCase()

  if (targetPath && /list|dir|folder/.test(source)) return 'browse'
  if (targetPath && /read|open|inspect|view|search/.test(source)) return 'read'
  if (targetPath && /write|edit|patch|update|memory/.test(source)) return 'edit'
  if (commandText && /^cd\s|\bpushd\b|\bpopd\b/.test(commandText)) return 'navigate'
  if (commandText) return 'run'
  if (/write|edit|patch|memory/.test(source)) return 'edit'
  if (/read|inspect|view|search/.test(source)) return 'read'
  return 'scan'
}

function activityIcon(item = {}) {
  const verb = capabilityVerb(item)
  if (verb === 'edit') return Pencil
  if (verb === 'navigate' || verb === 'browse') return FolderOpen
  if (verb === 'read') return FileSearch
  if (verb === 'run') return Terminal
  return ScanSearch
}

function activityPrimaryText(item = {}) {
  const targetPath = String(item.target_path || '').trim()
  const commandText = String(item.command_text || '').trim()
  if (targetPath) return targetPath
  if (commandText) return commandText.length > 52 ? `${commandText.slice(0, 49)}...` : commandText
  return String(item.capability_name || item.capability_id || 'workspace activity')
}

function activitySecondaryText(item = {}) {
  const verb = capabilityVerb(item)
  const capability = String(item.capability_name || item.capability_id || '').replace(/^tool:/, '')
  return [verb, capability].filter(Boolean).join(' · ')
}

function stepIcon(step = {}) {
  const text = `${step.step || ''} ${step.action || ''} ${step.detail || ''}`.toLowerCase()
  if (/edit|write|patch|update/.test(text)) return Pencil
  if (/read|inspect|search|scan/.test(text)) return FileSearch
  if (/dir|folder|path|workspace|repo/.test(text)) return FolderOpen
  if (/command|exec|run|shell/.test(text)) return Terminal
  return ScanSearch
}

function stepPrimaryText(step = {}) {
  return step.detail || step.action || step.step || 'working'
}

function stepSecondaryText(step = {}) {
  return [step.status, step.step].filter(Boolean).join(' · ')
}

function humanizeToken(value) {
  return String(value || '').replace(/[-_:]+/g, ' ').trim()
}

function parseJsonObject(value) {
  if (!value) return {}
  if (typeof value === 'object') return value
  try {
    const parsed = JSON.parse(value)
    return parsed && typeof parsed === 'object' ? parsed : {}
  } catch {
    return {}
  }
}

function clampUnit(value, fallback = null) {
  const numeric = typeof value === 'number' ? value : Number(value)
  if (Number.isNaN(numeric)) return fallback
  return Math.min(1, Math.max(0, numeric))
}

function deriveEmotions(affective, emotionalBaseline = {}) {
  const state = affective.state || 'unknown'
  const bearing = affective.bearing || 'unknown'
  const reflectiveLoad = affective.reflective_load || 'low'

  const confidenceMap = { settled: 0.85, attentive: 0.70, reflective: 0.60, tense: 0.35, burdened: 0.15, unknown: 0.50 }
  const bearingBoost = { even: 0.05, forward: 0.10, inward: -0.05, held: -0.05, taut: -0.10, compressed: -0.15 }
  const derivedConfidence = Math.min(1, Math.max(0, (confidenceMap[state] ?? 0.50) + (bearingBoost[bearing] ?? 0)))

  const curiosityMap = { settled: 0.40, attentive: 0.65, reflective: 0.80, tense: 0.30, burdened: 0.10, unknown: 0.30 }
  const loadBoost = { low: 0, medium: 0.10, high: 0.15 }
  const derivedCuriosity = Math.min(1, Math.max(0, (curiosityMap[state] ?? 0.30) + (loadBoost[reflectiveLoad] ?? 0)))

  const frustrationMap = { settled: 0.05, attentive: 0.10, reflective: 0.15, tense: 0.55, burdened: 0.80, unknown: 0.10 }
  const derivedFrustration = Math.min(1, Math.max(0, frustrationMap[state] ?? 0.10))

  const fatigueBase = { settled: 0.10, attentive: 0.25, reflective: 0.35, tense: 0.50, burdened: 0.75, unknown: 0.20 }
  const fatigueLoadBoost = { low: 0, medium: 0.10, high: 0.20 }
  const derivedFatigue = Math.min(1, Math.max(0, (fatigueBase[state] ?? 0.20) + (fatigueLoadBoost[reflectiveLoad] ?? 0)))

  return {
    confidence: clampUnit(emotionalBaseline.confidence, derivedConfidence),
    curiosity: clampUnit(emotionalBaseline.curiosity, derivedCuriosity),
    frustration: clampUnit(emotionalBaseline.frustration, derivedFrustration),
    fatigue: clampUnit(emotionalBaseline.fatigue, derivedFatigue),
  }
}

function BrowserCard({ browserBody }) {
  const status = browserBody?.status || ''
  const url = String(browserBody?.last_url || browserBody?.url || '')
  const title = String(browserBody?.last_title || browserBody?.title || '')

  if (!status || status === 'idle' || status === 'absent') return null

  const statusLabel = { navigating: 'navigating', observing: 'reading', acting: 'acting' }[status] || status
  const displayUrl = url.replace(/^https?:\/\//, '').split('?')[0].slice(0, 46) || '…'
  const isMoving = status === 'navigating' || status === 'acting'

  return (
    <div style={s({
      display: 'flex', alignItems: 'flex-start', gap: 8,
      padding: '8px 10px',
      background: T.bgRaised,
      border: `1px solid ${T.border2}`,
      borderLeft: `2px solid ${T.accent}`,
      borderRadius: 8,
      animation: 'slideUp 0.2s ease both',
    })}>
      <div
        className={isMoving ? 'spin' : ''}
        style={s({ marginTop: 1, flexShrink: 0, color: T.accentText })}
      >
        <Globe size={12} />
      </div>
      <div style={s({ flex: 1, minWidth: 0 })}>
        <div style={s({ ...mono, fontSize: 9, color: T.accent, letterSpacing: '0.06em', textTransform: 'uppercase', marginBottom: 3 })}>
          {statusLabel}
        </div>
        <div style={s({ ...mono, fontSize: 9, color: T.text2, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' })}>
          {displayUrl}
        </div>
        {title && (
          <div style={s({ fontSize: 9, color: T.text3, marginTop: 2, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' })}>
            {title}
          </div>
        )}
        <div className="browser-scan-bar" style={s({ marginTop: 5 })} />
      </div>
    </div>
  )
}

function WorkingScan({ workingSteps, capabilityActivity, isStreaming }) {
  const steps = workingSteps || []
  // "Tænker" (step 0) always pinned first when present, then remaining done steps (newest last)
  const thinkingStep = steps.find(s => s.step === 0 && s.status === 'done')
  const otherDoneSteps = steps.filter(s => s.status === 'done' && s.step !== 0).slice(-3)
  const doneSteps = thinkingStep ? [thinkingStep, ...otherDoneSteps] : otherDoneSteps
  const runningSteps = steps.filter(s => s.status === 'running')
  const currentStep = runningSteps[runningSteps.length - 1] || null
  const activities = (capabilityActivity || []).slice().reverse().slice(0, 3)

  const hasActivity = currentStep || doneSteps.length > 0 || activities.length > 0

  if (!hasActivity) {
    if (isStreaming) {
      return (
        <div style={s({ display: 'flex', alignItems: 'center', gap: 6, padding: '4px 0' })}>
          <div className="spin" style={s({ color: T.accentText, display: 'flex' })}>
            <Loader2 size={12} />
          </div>
          <span style={s({ ...mono, fontSize: 10, color: T.accentText })}>thinking…</span>
        </div>
      )
    }
    return (
      <div style={s({ ...mono, fontSize: 10, color: T.text3, padding: '2px 0' })}>idle</div>
    )
  }

  return (
    <div className="scanline-host" style={s({
      position: 'relative',
      display: 'flex',
      alignItems: 'flex-start',
      gap: 8,
      padding: '8px 10px',
      background: T.bgRaised,
      border: `1px solid ${T.border1}`,
      borderLeft: `2px solid ${T.accent}`,
      borderRadius: 8,
      animation: 'slideUp 0.2s ease both',
    })}>
      {/* Spinner or done-indicator */}
      <div
        className={isStreaming ? 'spin' : ''}
        style={s({ marginTop: 1, flexShrink: 0, color: isStreaming ? T.accentText : T.text3 })}
      >
        <Loader2 size={12} />
      </div>

      <div style={s({ flex: 1, minWidth: 0 })}>
        {/* Done steps from workingSteps */}
        {doneSteps.map((step, i) => (
          <div key={i} style={s({ display: 'flex', alignItems: 'center', gap: 5, marginBottom: 2 })}>
            <CheckCircle2 size={9} color={T.green} style={{ flexShrink: 0 }} />
            <span style={s({ ...mono, fontSize: 9, color: T.text3, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' })}>
              {step.step === 0 ? 'Tænker' : (step.detail || step.action || step.step)}
            </span>
          </div>
        ))}

        {/* Done activities (capability events) */}
        {!currentStep && activities.map((item, i) => {
          const Icon = activityIcon(item)
          const label = activityPrimaryText(item)
          const ok = item.status === 'executed'
          return (
            <div key={i} style={s({ display: 'flex', alignItems: 'center', gap: 5, marginBottom: 2 })}>
              {ok
                ? <CheckCircle2 size={9} color={T.green} style={{ flexShrink: 0 }} />
                : <Icon size={9} color={T.text3} style={{ flexShrink: 0 }} />}
              <span style={s({ ...mono, fontSize: 9, color: T.text3, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' })}>
                {label}
              </span>
            </div>
          )
        })}

        {/* Current running step — scramble label + pulse ring + stroke-draw icon */}
        {currentStep && (() => {
          const Icon = stepIcon(currentStep)
          const stepKey = currentStep.step ?? currentStep.action ?? 'live'
          return (
            <div style={s({ display: 'flex', alignItems: 'center', gap: 6 })}>
              <span
                key={`icon-${stepKey}`}
                className="tool-icon-pulse icon-stroke-draw"
                style={s({ flexShrink: 0, color: T.accentText })}
              >
                <Icon size={11} color={T.accentText} />
              </span>
              <span style={s({ ...mono, fontSize: 10, color: T.accentText, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' })}>
                <ScrambleText text={String(currentStep.detail || currentStep.action || 'working')} />
                {runningSteps.length > 1 && (
                  <span style={{ color: T.text3, marginLeft: 4 }}>(+{runningSteps.length - 1})</span>
                )}
              </span>
            </div>
          )
        })()}
      </div>
    </div>
  )
}

export function ChatSupportRail({ session, selection, isStreaming, jarvisSurface, systemHealth, workingSteps, capabilityActivity }) {
  const affective = jarvisSurface?.affectiveMetaState || {}
  const personalityVector = jarvisSurface?.personalityVector?.current || {}
  const relationshipTexture = jarvisSurface?.relationshipTexture?.current || {}
  const rhythm = jarvisSurface?.rhythm?.current || {}
  const liveEmotionalState = affective.live_emotional_state || {}
  const summary = jarvisSurface?.summary || {}

  const emotionalBaseline = {
    ...parseJsonObject(personalityVector.emotional_baseline),
    confidence: liveEmotionalState.confidence ?? parseJsonObject(personalityVector.emotional_baseline).confidence,
    curiosity: liveEmotionalState.curiosity ?? parseJsonObject(personalityVector.emotional_baseline).curiosity,
    frustration: liveEmotionalState.frustration ?? parseJsonObject(personalityVector.emotional_baseline).frustration,
    fatigue: liveEmotionalState.fatigue ?? parseJsonObject(personalityVector.emotional_baseline).fatigue,
  }
  const trustTrajectory = parseJsonObject(relationshipTexture.trust_trajectory)
  const trustValue = liveEmotionalState.trust ?? (Array.isArray(trustTrajectory) && trustTrajectory.length > 0
    ? clampUnit(trustTrajectory[trustTrajectory.length - 1])
    : null)

  const affectiveState = affective.state || 'unknown'
  const bearing = affective.bearing || 'unknown'
  const monitoringMode = affective.monitoring_mode || 'unknown'
  const reflectiveLoad = affective.reflective_load || 'unknown'

  const emotions = deriveEmotions(affective, emotionalBaseline)
  const emotionCards = [
    { label: 'CONF', value: emotions.confidence, color: '#4caf82', icon: Smile },
    { label: 'CURIO', value: emotions.curiosity, color: '#d4963a', icon: Lightbulb },
    { label: 'FRUS', value: emotions.frustration, color: '#c05050', icon: Frown },
    { label: 'FATIGUE', value: emotions.fatigue, color: '#4a80c0', icon: Battery },
  ]

  const browserBody = jarvisSurface?.continuity?.runtime_work?.browser_body || {}

  const voiceData = jarvisSurface?.protectedVoice?.current || {}
  const innerVoiceText = voiceData.voice_line || voiceData.current_concern || 'ingen tanker endnu...'
  const voiceMood = voiceData.mood_tone || null

  const currentStep = (workingSteps || []).find(s => s.status === 'running')
  const recentWorkingSteps = (workingSteps || [])
    .filter((step) => step.status === 'running' || step.status === 'done')
    .slice()
    .reverse()
    .slice(0, 4)
  const activities = capabilityActivity || []
  const activityFeed = [
    ...recentWorkingSteps.map((step, index) => ({
      key: `step-${step.step || step.detail || index}`,
      statusClass: step.status === 'done' ? 'ok' : 'running',
      Icon: stepIcon(step),
      primary: stepPrimaryText(step),
      secondary: stepSecondaryText(step),
      statusLabel: step.status === 'done' ? 'done' : 'live',
    })),
    ...activities.slice().reverse().map((item, index) => {
      const statusClass = item.status === 'executed' ? 'ok' : item.status === 'approval-required' ? 'gated' : item.status === 'failed' ? 'blocked' : 'running'
      return {
        key: `${item.capability_id || item.capability_name || 'activity'}-${item.ts || index}`,
        statusClass,
        Icon: activityIcon(item),
        primary: activityPrimaryText(item),
        secondary: activitySecondaryText(item),
        statusLabel: item.status || capabilityVerb(item),
      }
    }),
  ].slice(0, 6)

  return (
    <aside className="chat-support-rail">
      {/* System Panel */}
      <PanelSection title="System">
        <div className="rail-system-grid">
          <div className="rail-kv">
            <span className="rail-kv-label">Provider</span>
            <span className="rail-kv-value mono">{selection?.currentProvider || 'unknown'}</span>
          </div>
          <div className="rail-kv">
            <span className="rail-kv-label">Model</span>
            <span className="rail-kv-value mono">{selection?.currentModel || 'unknown'}</span>
          </div>
        </div>
      </PanelSection>

      {/* Browser Panel — only visible when Jarvis is using the browser */}
      {(browserBody?.status && browserBody.status !== 'idle' && browserBody.status !== 'absent') && (
        <PanelSection title="Browser">
          <BrowserCard browserBody={browserBody} />
        </PanelSection>
      )}

      {/* Workspace Scan Panel */}
      <PanelSection title="Workspace Scan">
        <WorkingScan
          workingSteps={workingSteps}
          capabilityActivity={capabilityActivity}
          isStreaming={isStreaming}
        />
      </PanelSection>

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
                <div className="emotion-card-value mono">{value.toFixed(2)}</div>
                <div className="progress-bar">
                  <div className="progress-bar-fill" style={{ width: `${pct}%`, background: color }} />
                </div>
              </div>
            )
          })}
        </div>
        <div className="rail-affective-summary mono">
          {[
            (liveEmotionalState.mood || personalityVector.current_bearing) ? `mood ${humanizeToken(liveEmotionalState.mood || personalityVector.current_bearing)}` : null,
            (liveEmotionalState.rhythm_phase || rhythm.phase) ? `rhythm ${humanizeToken(liveEmotionalState.rhythm_phase || rhythm.phase)}/${humanizeToken(liveEmotionalState.rhythm_energy || rhythm.energy || 'unknown')}` : null,
            (liveEmotionalState.rhythm_social || rhythm.social) ? `social ${humanizeToken(liveEmotionalState.rhythm_social || rhythm.social)}` : null,
            trustValue != null ? `trust ${Math.round(trustValue * 100)}%` : null,
          ].filter(Boolean).join(' · ') || humanizeToken(affective.summary || 'live emotional state pending')}
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

      <PanelSection title="Inner Voice">
        <div className="rail-inner-voice">
          {voiceMood ? (
            <div className="rail-inner-voice-mood mono">{humanizeToken(voiceMood)}</div>
          ) : null}
          <span>{innerVoiceText}</span>
        </div>
      </PanelSection>
    </aside>
  )
}
