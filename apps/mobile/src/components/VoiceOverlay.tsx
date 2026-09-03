import { Modal, Pressable, StyleSheet, Text, View } from 'react-native'
import type { VoiceState, VoiceMode } from '../lib/useVoiceConversation'
import { useStyles, useTheme, type Theme } from '../theme/ThemeContext'

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
  /** Hvorfor det gik i stå. Tom = intet at melde. */
  problem?: string
  mode: VoiceMode
  lastProvider: string
  setMode: (m: VoiceMode) => void
  startListening: () => void
  stopListening: () => void
  exit: () => void
}

export function VoiceOverlay(p: VoiceOverlayProps) {
  const t = useTheme()
  const s = useStyles(makes)
  const busy = p.state === 'transcribing' || p.state === 'thinking' || p.state === 'speaking'
  const micDown = () => { if (p.mode === 'push' && !busy) p.startListening() }
  // Slip ALTID, uden at spørge om tilstanden først. Et kort tryk kan nå at
  // blive sluppet før optageren er oppe, og så stod her 'listening' endnu ikke
  // — knappen gjorde ingenting, og optagelsen kørte videre. Hook'en holder
  // selv styr på om der faktisk optages.
  const micUp = () => { if (p.mode === 'push') p.stopListening() }
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

          {p.problem ? (
            /* Grunden STÅR der. Før satte hver fejl-gren bare tilstanden til
               idle, og et overlay der blinker tilbage uden et ord efterlader
               kun én mulig konklusion: «det virker ikke». */
            <Text style={s.problem}>{p.problem}</Text>
          ) : null}

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

// Overlayet var hårdkodet i sine egne farver — blandt andet en lilla (#7b61ff)
// fra dengang accenten var lilla. Den fulgte hverken tema eller brugerens
// farvevalg, og stod tilbage som det eneste sted i appen med en fremmed farve.
const makes = (tokens: Theme) => StyleSheet.create({
  overlay: { flex: 1, alignItems: 'center', justifyContent: 'center', backgroundColor: tokens.color.scrim },
  panel: { alignItems: 'center', gap: 16, padding: 28, borderRadius: tokens.radius.xl, minWidth: 300, backgroundColor: tokens.color.bg2 },
  header: { flexDirection: 'row', width: '100%', justifyContent: 'space-between', alignItems: 'center' },
  title: { color: tokens.color.fg1, fontWeight: '600', fontSize: 16 },
  close: { color: tokens.color.fg3, fontSize: 20 },
  problem: { color: tokens.color.warn, fontSize: 13.5, lineHeight: 20, marginBottom: tokens.spacing.sm, textAlign: 'center' },
  modeRow: { flexDirection: 'row', gap: 8 },
  modeBtn: { paddingVertical: 6, paddingHorizontal: 16, borderRadius: 999, borderWidth: 1, borderColor: tokens.color.line },
  modeBtnActive: { backgroundColor: tokens.color.accent, borderColor: tokens.color.accent },
  modeTxt: { color: tokens.color.fg2, fontSize: 13 },
  modeTxtActive: { color: tokens.color.onAccent },
  mic: { width: 104, height: 104, borderRadius: 52, borderWidth: 3, backgroundColor: tokens.color.bg1, alignItems: 'center', justifyContent: 'center' },
  micActive: { backgroundColor: tokens.color.accentGhost },
  micIcon: { fontSize: 44 },
  state: { fontWeight: '500', minHeight: 20, color: tokens.color.fg1 },
  hint: { color: tokens.color.fg3, fontSize: 12, textAlign: 'center', maxWidth: 280 },
})
