import type { VoiceState, VoiceMode } from '../../hooks/useVoiceConversation'

/** Samtale-mode overlay (Trin 2). Vises når active. Push-to-talk: hold mic. Hænderfri:
 *  tryk for at starte, VAD auto-stopper. Alt best-effort — knappen vender tilbage til idle. */

const _STATE_LABEL: Record<VoiceState, string> = {
  idle: 'Klar — tryk for at tale',
  listening: 'Lytter…',
  transcribing: 'Hører hvad du sagde…',
  thinking: 'Jarvis tænker…',
  speaking: 'Jarvis taler…',
}

const _STATE_COLOR: Record<VoiceState, string> = {
  idle: 'var(--text-muted, #888)',
  listening: '#e0245e',
  transcribing: '#f5a623',
  thinking: '#7b61ff',
  speaking: '#2ecc71',
}

export interface VoiceConversationProps {
  active: boolean
  state: VoiceState
  mode: VoiceMode
  supported: boolean
  lastProvider: string
  setMode: (m: VoiceMode) => void
  startListening: () => void
  stopListening: () => void
  exit: () => void
}

export function VoiceConversation(p: VoiceConversationProps) {
  if (!p.active) return null
  const busy = p.state === 'transcribing' || p.state === 'thinking' || p.state === 'speaking'
  const label = p.supported ? _STATE_LABEL[p.state] : 'Mikrofon ikke tilgængelig'

  // Push-to-talk: hold. Hænderfri: tryk for at starte/stoppe en tur.
  const micDown = () => { if (p.mode === 'push' && !busy) p.startListening() }
  const micUp = () => { if (p.mode === 'push' && p.state === 'listening') p.stopListening() }
  const micTap = () => {
    if (p.mode !== 'hands-free') return
    if (p.state === 'listening') p.stopListening()
    else if (!busy) p.startListening()
  }

  return (
    <div className="voice-overlay" style={_overlay}>
      <div style={_panel}>
        <div style={_header}>
          <span style={{ fontWeight: 600 }}>🎙️ Samtale med Jarvis</span>
          <button onClick={p.exit} style={_close} title="Luk samtale-mode">✕</button>
        </div>

        <div style={_modeRow}>
          {(['push', 'hands-free'] as VoiceMode[]).map((m) => (
            <button
              key={m}
              onClick={() => p.setMode(m)}
              disabled={busy || p.state === 'listening'}
              style={{ ..._modeBtn, ...(p.mode === m ? _modeBtnActive : {}) }}
            >
              {m === 'push' ? 'Push-to-talk' : 'Hænderfri'}
            </button>
          ))}
        </div>

        <button
          onPointerDown={micDown}
          onPointerUp={micUp}
          onPointerLeave={micUp}
          onClick={micTap}
          disabled={!p.supported || (busy && p.state !== 'speaking')}
          style={{
            ..._mic,
            borderColor: _STATE_COLOR[p.state],
            boxShadow: p.state === 'listening' ? `0 0 0 6px ${_STATE_COLOR[p.state]}33` : 'none',
          }}
          title={p.mode === 'push' ? 'Hold for at tale' : 'Tryk for at tale'}
        >
          <span style={{ fontSize: 40 }}>{p.state === 'speaking' ? '🔊' : '🎤'}</span>
        </button>

        <div style={{ color: _STATE_COLOR[p.state], fontWeight: 500, minHeight: 20 }}>{label}</div>
        <div style={_hint}>
          {p.mode === 'push' ? 'Hold knappen inde mens du taler.' : 'Tal frit — jeg sender selv når du holder pause.'}
          {p.lastProvider ? `  ·  stemme: ${p.lastProvider === 'elevenlabs' ? 'ElevenLabs' : p.lastProvider === 'edge' ? 'edge-tts' : p.lastProvider === 'device' ? 'enhed' : p.lastProvider}` : ''}
        </div>
      </div>
    </div>
  )
}

const _overlay: React.CSSProperties = {
  position: 'fixed', inset: 0, display: 'flex', alignItems: 'center',
  justifyContent: 'center', background: 'rgba(0,0,0,0.35)', zIndex: 50,
}
const _panel: React.CSSProperties = {
  display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 16,
  padding: '28px 32px', borderRadius: 16, minWidth: 300,
  background: 'var(--bg-elevated, #1c1c1e)', color: 'var(--text, #eee)',
  boxShadow: '0 12px 48px rgba(0,0,0,0.5)',
}
const _header: React.CSSProperties = { display: 'flex', width: '100%', justifyContent: 'space-between', alignItems: 'center' }
const _close: React.CSSProperties = { background: 'none', border: 'none', color: 'inherit', fontSize: 18, cursor: 'pointer', opacity: 0.7 }
const _modeRow: React.CSSProperties = { display: 'flex', gap: 8 }
const _modeBtn: React.CSSProperties = {
  padding: '6px 14px', borderRadius: 999, border: '1px solid var(--border, #444)',
  background: 'transparent', color: 'inherit', cursor: 'pointer', fontSize: 13,
}
const _modeBtnActive: React.CSSProperties = { background: 'var(--accent, #7b61ff)', borderColor: 'var(--accent, #7b61ff)', color: '#fff' }
const _mic: React.CSSProperties = {
  width: 96, height: 96, borderRadius: '50%', border: '3px solid',
  background: 'var(--bg, #0e0e10)', cursor: 'pointer', display: 'flex',
  alignItems: 'center', justifyContent: 'center', transition: 'box-shadow 0.15s',
}
const _hint: React.CSSProperties = { fontSize: 12, opacity: 0.6, textAlign: 'center', maxWidth: 280 }
