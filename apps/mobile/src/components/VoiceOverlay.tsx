import { Modal, Pressable, StyleSheet, Text, View } from 'react-native'
import type { VoiceState, VoiceMode } from '../lib/useVoiceConversation'

/** Samtale-mode overlay (Trin 3, mobil). Push-to-talk: hold mic. Hænderfri: tryk. */

const LABEL: Record<VoiceState, string> = {
  idle: 'Klar — tryk for at tale',
  listening: 'Lytter…',
  transcribing: 'Hører hvad du sagde…',
  thinking: 'Jarvis tænker…',
  speaking: 'Jarvis taler…',
}
const COLOR: Record<VoiceState, string> = {
  idle: '#8a8a8e', listening: '#e0245e', transcribing: '#f5a623', thinking: '#7b61ff', speaking: '#2ecc71',
}

export interface VoiceOverlayProps {
  active: boolean
  state: VoiceState
  mode: VoiceMode
  lastProvider: string
  setMode: (m: VoiceMode) => void
  startListening: () => void
  stopListening: () => void
  exit: () => void
}

export function VoiceOverlay(p: VoiceOverlayProps) {
  const busy = p.state === 'transcribing' || p.state === 'thinking' || p.state === 'speaking'
  const micDown = () => { if (p.mode === 'push' && !busy) p.startListening() }
  const micUp = () => { if (p.mode === 'push' && p.state === 'listening') p.stopListening() }
  const micTap = () => {
    if (p.mode !== 'hands-free') return
    if (p.state === 'listening') p.stopListening()
    else if (!busy) p.startListening()
  }
  const providerLabel = p.lastProvider === 'elevenlabs' ? 'ElevenLabs' : p.lastProvider === 'edge' ? 'edge-tts' : p.lastProvider === 'device' ? 'enhed' : p.lastProvider

  return (
    <Modal visible={p.active} transparent animationType="fade" onRequestClose={p.exit}>
      <View style={s.overlay}>
        <View style={s.panel}>
          <View style={s.header}>
            <Text style={s.title}>🎙️ Samtale med Jarvis</Text>
            <Pressable onPress={p.exit} hitSlop={12}><Text style={s.close}>✕</Text></Pressable>
          </View>

          <View style={s.modeRow}>
            {(['push', 'hands-free'] as VoiceMode[]).map((m) => (
              <Pressable
                key={m}
                onPress={() => { if (!busy && p.state !== 'listening') p.setMode(m) }}
                style={[s.modeBtn, p.mode === m && s.modeBtnActive]}
              >
                <Text style={[s.modeTxt, p.mode === m && s.modeTxtActive]}>{m === 'push' ? 'Push-to-talk' : 'Hænderfri'}</Text>
              </Pressable>
            ))}
          </View>

          <Pressable
            onPressIn={micDown}
            onPressOut={micUp}
            onPress={micTap}
            style={[s.mic, { borderColor: COLOR[p.state] }, p.state === 'listening' && s.micActive]}
          >
            <Text style={s.micIcon}>{p.state === 'speaking' ? '🔊' : '🎤'}</Text>
          </Pressable>

          <Text style={[s.state, { color: COLOR[p.state] }]}>{LABEL[p.state]}</Text>
          <Text style={s.hint}>
            {p.mode === 'push' ? 'Hold knappen mens du taler.' : 'Tal frit — jeg sender når du holder pause.'}
            {p.lastProvider ? `  ·  stemme: ${providerLabel}` : ''}
          </Text>
        </View>
      </View>
    </Modal>
  )
}

const s = StyleSheet.create({
  overlay: { flex: 1, alignItems: 'center', justifyContent: 'center', backgroundColor: 'rgba(0,0,0,0.45)' },
  panel: { alignItems: 'center', gap: 16, padding: 28, borderRadius: 18, minWidth: 300, backgroundColor: '#1c1c1e' },
  header: { flexDirection: 'row', width: '100%', justifyContent: 'space-between', alignItems: 'center' },
  title: { color: '#eee', fontWeight: '600', fontSize: 16 },
  close: { color: '#bbb', fontSize: 20 },
  modeRow: { flexDirection: 'row', gap: 8 },
  modeBtn: { paddingVertical: 6, paddingHorizontal: 16, borderRadius: 999, borderWidth: 1, borderColor: '#444' },
  modeBtnActive: { backgroundColor: '#7b61ff', borderColor: '#7b61ff' },
  modeTxt: { color: '#ccc', fontSize: 13 },
  modeTxtActive: { color: '#fff' },
  mic: { width: 104, height: 104, borderRadius: 52, borderWidth: 3, backgroundColor: '#0e0e10', alignItems: 'center', justifyContent: 'center' },
  micActive: { backgroundColor: '#2a0d16' },
  micIcon: { fontSize: 44 },
  state: { fontWeight: '500', minHeight: 20 },
  hint: { color: '#888', fontSize: 12, textAlign: 'center', maxWidth: 280 },
})
