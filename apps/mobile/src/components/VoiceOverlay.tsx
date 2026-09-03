import { Animated, Modal, Pressable, StyleSheet, Text, View } from 'react-native'
import { X } from 'lucide-react-native'
import type { VoiceState, VoiceMode } from '../lib/useVoiceConversation'
import { VoiceOrb } from './VoiceOrb'
import { useStyles, useTheme, type Theme } from '../theme/ThemeContext'

/** Samtale-mode. Push-to-talk: hold kuglen. Hænderfri: den lytter selv videre. */

const LABEL: Record<VoiceState, string> = {
  idle: '',
  listening: 'Jeg lytter',
  transcribing: 'Hører hvad du sagde',
  thinking: 'Tænker',
  speaking: 'Tryk for at afbryde',
}

export interface VoiceOverlayProps {
  active: boolean
  state: VoiceState
  /** 0..1 — hvor kraftigt der tales lige nu. En Animated.Value og ikke et tal:
   *  niveauet opdateres mange gange i sekundet, og at rendre skærmen så tit for
   *  at puste en kugle op ville koste mere end den er værd. */
  level?: Animated.Value
  /** Hvorfor det gik i stå. Tom = intet at melde. */
  problem?: string
  mode: VoiceMode
  lastProvider: string
  setMode: (m: VoiceMode) => void
  startListening: () => void
  stopListening: () => void
  interrupt: () => void
  exit: () => void
}

export function VoiceOverlay(p: VoiceOverlayProps) {
  const tokens = useTheme()
  const s = useStyles(makes)
  const busy = p.state === 'transcribing' || p.state === 'thinking'

  // I push-to-talk holder man kuglen. I hænderfri trykker man kun for at gribe
  // ind — starte, stoppe, eller afbryde ham midt i et svar.
  const down = () => { if (p.mode === 'push' && !busy && p.state !== 'speaking') p.startListening() }
  const up = () => { if (p.mode === 'push') p.stopListening() }
  const tap = () => {
    if (p.state === 'speaking') { p.interrupt(); return }
    if (p.mode !== 'hands-free') return
    if (p.state === 'listening') p.stopListening()
    else if (!busy) p.startListening()
  }

  const providerLabel = p.lastProvider === 'elevenlabs' ? 'ElevenLabs'
    : p.lastProvider === 'edge' ? 'edge-tts'
      : p.lastProvider === 'device' ? 'telefonens stemme' : ''

  const hint = p.mode === 'push'
    ? 'Hold kuglen mens du taler'
    : 'Tal frit — jeg sender når du holder pause'

  return (
    <Modal visible={p.active} transparent={false} animationType="fade" onRequestClose={p.exit}>
      <View style={s.screen}>
        <View style={s.top}>
          <Pressable onPress={p.exit} hitSlop={16} accessibilityRole="button" accessibilityLabel="Luk samtale">
            <X size={24} color={tokens.color.fg2} strokeWidth={2} />
          </Pressable>
        </View>

        {/* Kuglen ER grænsefladen. Alt andet holder sig i udkanten, så der er
            noget at hvile øjnene på mens man taler. */}
        <View style={s.middle}>
          <Pressable
            onPressIn={down}
            onPressOut={up}
            onPress={tap}
            accessibilityRole="button"
            accessibilityLabel={p.state === 'speaking' ? 'Afbryd Jarvis' : 'Tal med Jarvis'}
          >
            <VoiceOrb state={p.state} level={p.level} />
          </Pressable>
          <Text style={s.state}>{LABEL[p.state]}</Text>
          {p.problem ? <Text style={s.problem}>{p.problem}</Text> : null}
        </View>

        <View style={s.bottom}>
          <View style={s.modeRow}>
            {(['hands-free', 'push'] as VoiceMode[]).map((m) => (
              <Pressable
                key={m}
                onPress={() => { if (!busy && p.state !== 'listening') p.setMode(m) }}
                style={[s.modeBtn, p.mode === m && s.modeBtnActive]}
              >
                <Text style={[s.modeTxt, p.mode === m && s.modeTxtActive]}>
                  {m === 'push' ? 'Push-to-talk' : 'Hænderfri'}
                </Text>
              </Pressable>
            ))}
          </View>
          <Text style={s.hint}>{hint}{providerLabel ? `  ·  ${providerLabel}` : ''}</Text>
        </View>
      </View>
    </Modal>
  )
}

const makes = (tokens: Theme) => StyleSheet.create({
  screen: { flex: 1, backgroundColor: tokens.color.bg0, paddingTop: 52, paddingBottom: 34 },
  top: { alignItems: 'flex-end', paddingHorizontal: 22 },
  middle: { flex: 1, alignItems: 'center', justifyContent: 'center', gap: 26 },
  state: { color: tokens.color.fg2, fontSize: 15, minHeight: 20 },
  problem: {
    color: tokens.color.warn, fontSize: 13.5, lineHeight: 20,
    textAlign: 'center', paddingHorizontal: 40,
  },
  bottom: { alignItems: 'center', gap: 14, paddingHorizontal: 24 },
  modeRow: { flexDirection: 'row', gap: 8 },
  modeBtn: {
    paddingVertical: 7, paddingHorizontal: 18, borderRadius: 999,
    borderWidth: 1, borderColor: tokens.color.line,
  },
  modeBtnActive: { backgroundColor: tokens.color.accent, borderColor: tokens.color.accent },
  modeTxt: { color: tokens.color.fg2, fontSize: 13 },
  modeTxtActive: { color: tokens.color.onAccent },
  hint: { color: tokens.color.fg3, fontSize: 12, textAlign: 'center' },
})
