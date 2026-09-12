import { ActivityIndicator, Animated, Pressable, StyleSheet, Text, View } from 'react-native'
import { Check, X } from 'lucide-react-native'
import type { DictationState } from '../lib/useComposerDictation'
import { useStyles, useTheme, type Theme } from '../theme/ThemeContext'

function duration(ms: number): string {
  const seconds = Math.max(0, Math.floor(ms / 1000))
  return `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, '0')}`
}

export function DictationBar({ state, elapsedMs, error, level, onStop, onCancel }: {
  state: DictationState
  elapsedMs: number
  error?: string
  /** Mikrofon-niveauet (0..1) fra useComposerDictation.
   *
   *  Uden den står prikken stille — den er ikke et krav, men uden den
   *  kan man ikke se om mikrofonen overhovedet hører noget. */
  level?: Animated.Value
  onStop: () => void
  onCancel: () => void
}) {
  const tokens = useTheme()
  const styles = useStyles(makeStyles)
  if (state === 'idle') return null
  return (
    <View testID="dictation-bar" style={styles.row}>
      {state === 'transcribing' ? (
        <ActivityIndicator size="small" color={tokens.color.accent} />
      ) : (
        <Animated.View
          testID="dictation-level"
          style={[styles.liveDot, level ? {
            transform: [{
              scale: level.interpolate({ inputRange: [0, 1], outputRange: [1, 2.2] }),
            }],
          } : null]}
        />
      )}
      <Text style={styles.status} numberOfLines={1}>
        {state === 'recording' ? duration(elapsedMs)
          : state === 'transcribing' ? 'Transskriberer...'
            : error || 'Diktering fejlede'}
      </Text>
      {state === 'recording' ? (
        <Pressable accessibilityRole="button" accessibilityLabel="Stop diktering" onPress={onStop} style={styles.button}>
          <Check size={18} color={tokens.color.fg1} />
        </Pressable>
      ) : null}
      <Pressable accessibilityRole="button" accessibilityLabel="Annuller diktering" onPress={onCancel} style={styles.button}>
        <X size={18} color={tokens.color.fg2} />
      </Pressable>
    </View>
  )
}

const makeStyles = (tokens: Theme) => StyleSheet.create({
  row: {
    minHeight: 36, flexDirection: 'row', alignItems: 'center', gap: 8,
    paddingHorizontal: 6, paddingBottom: 6,
  },
  liveDot: { width: 8, height: 8, borderRadius: 4, backgroundColor: tokens.color.error },
  status: { flex: 1, color: tokens.color.fg2, fontSize: 13 },
  button: {
    width: 30, height: 30, borderRadius: 15,
    alignItems: 'center', justifyContent: 'center', backgroundColor: tokens.color.bg2,
  },
})
