import { useState } from 'react'
import { Pressable, StyleSheet, Text, TextInput, View } from 'react-native'
import { tokens } from '../theme/tokens'

/**
 * Composer som hævet kort (ikke flad bjælke) med inline-kontroller:
 * `+` vedhæft, model-pille (rolle-bevidst — owner: palette, member: Standard/Pro),
 * mic, og send/stop. Spec §7 "intelligent plads / levende papir".
 */
export function Composer({
  disabled,
  working,
  modelLabel,
  onSend,
  onStop,
  onPressModel,
  onAttach,
  onMic
}: {
  disabled?: boolean
  working?: boolean
  modelLabel?: string
  onSend: (text: string) => void | Promise<void>
  onStop: () => void
  onPressModel?: () => void
  onAttach?: () => void
  onMic?: () => void
}) {
  const [text, setText] = useState('')
  const [submitting, setSubmitting] = useState(false)

  const submit = async () => {
    const value = text.trim()
    if (!value || disabled || working || submitting) return

    setSubmitting(true)
    try {
      await onSend(value)
      setText('')
    } catch {
      // Behold kladden hvis send fejler.
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <View style={styles.outer}>
      <View style={styles.card}>
        <TextInput
          testID="composer-input"
          value={text}
          onChangeText={setText}
          multiline
          editable={!disabled}
          placeholder="Skriv til Jarvis"
          placeholderTextColor={tokens.color.fg3}
          style={styles.input}
        />
        <View style={styles.controls}>
          <View style={styles.left}>
            <Pressable accessibilityRole="button" accessibilityLabel="Vedhæft" onPress={onAttach} hitSlop={6} style={styles.iconBtn}>
              <Text style={styles.iconPlus}>+</Text>
            </Pressable>
            {modelLabel ? (
              <Pressable accessibilityRole="button" onPress={onPressModel} style={styles.modelPill}>
                <Text style={styles.modelText} numberOfLines={1}>{modelLabel}</Text>
                <Text style={styles.modelChev}>▾</Text>
              </Pressable>
            ) : null}
          </View>
          <View style={styles.right}>
            <Pressable accessibilityRole="button" accessibilityLabel="Diktér" onPress={onMic} hitSlop={6} style={styles.iconBtn}>
              <Text style={styles.mic}>🎙</Text>
            </Pressable>
            <Pressable
              testID="composer-button"
              accessibilityRole="button"
              disabled={(disabled && !working) || submitting}
              onPress={working ? onStop : submit}
              style={({ pressed }) => [
                styles.sendBtn,
                working ? styles.stopBtn : null,
                (disabled && !working) || submitting ? styles.disabled : null,
                pressed ? styles.pressed : null
              ]}
            >
              <Text style={styles.sendText}>{working ? '■' : '↑'}</Text>
            </Pressable>
          </View>
        </View>
      </View>
    </View>
  )
}

const styles = StyleSheet.create({
  outer: {
    paddingHorizontal: tokens.spacing.md,
    paddingTop: tokens.spacing.sm,
    paddingBottom: tokens.spacing.md
  },
  card: {
    backgroundColor: tokens.color.bg1,
    borderRadius: 22,
    borderWidth: 1,
    borderColor: tokens.color.line,
    paddingHorizontal: tokens.spacing.md,
    paddingTop: tokens.spacing.sm,
    paddingBottom: tokens.spacing.sm,
    // dybde — hævet kort
    shadowColor: '#000',
    shadowOpacity: 0.3,
    shadowRadius: 10,
    shadowOffset: { width: 0, height: 4 },
    elevation: 4
  },
  input: {
    minHeight: 28,
    maxHeight: 140,
    color: tokens.color.fg1,
    fontSize: 16,
    paddingHorizontal: tokens.spacing.xs,
    paddingTop: tokens.spacing.xs
  },
  controls: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginTop: tokens.spacing.xs
  },
  left: { flexDirection: 'row', alignItems: 'center', gap: tokens.spacing.sm, flexShrink: 1 },
  right: { flexDirection: 'row', alignItems: 'center', gap: tokens.spacing.sm },
  iconBtn: {
    width: 34,
    height: 34,
    borderRadius: 17,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: tokens.color.bg2
  },
  iconPlus: { color: tokens.color.fg1, fontSize: 20, lineHeight: 22, fontWeight: '600' },
  mic: { fontSize: 15 },
  modelPill: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    paddingHorizontal: tokens.spacing.sm,
    height: 34,
    borderRadius: 17,
    backgroundColor: tokens.color.bg2,
    flexShrink: 1
  },
  modelText: { color: tokens.color.fg2, fontSize: 13, fontWeight: '600', flexShrink: 1 },
  modelChev: { color: tokens.color.fg3, fontSize: 11 },
  sendBtn: {
    width: 38,
    height: 38,
    borderRadius: 19,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: tokens.color.accent
  },
  stopBtn: { backgroundColor: tokens.color.warn },
  disabled: { opacity: 0.4 },
  pressed: { opacity: 0.85 },
  sendText: { color: tokens.color.bg0, fontWeight: '800', fontSize: 18 }
})
