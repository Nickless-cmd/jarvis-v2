import { StyleSheet, Text, View } from 'react-native'
import { tokens } from '../theme/tokens'

// Oversæt stream-status til en farvet prik + dansk etiket (labeled status,
// som "Dispatch ● Idle" i Claude-appen).
const STATUS: Record<string, { dot: string; label: string }> = {
  idle: { dot: tokens.color.fg3, label: 'klar' },
  working: { dot: tokens.color.accent, label: 'arbejder' },
  done: { dot: tokens.color.accent, label: 'klar' },
  interrupted: { dot: tokens.color.warn, label: 'afbrudt' },
  hung: { dot: tokens.color.warn, label: 'hænger' },
  error: { dot: tokens.color.error, label: 'fejl' }
}

export function ConnectionPill({ label }: { label: string }) {
  const s = STATUS[label] ?? { dot: tokens.color.fg3, label }
  return (
    <View style={styles.root}>
      <View style={[styles.dot, { backgroundColor: s.dot }]} />
      <Text style={styles.text}>{s.label}</Text>
    </View>
  )
}

const styles = StyleSheet.create({
  root: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: tokens.spacing.xs,
    paddingHorizontal: tokens.spacing.sm,
    paddingVertical: tokens.spacing.xs,
    borderRadius: tokens.radius.lg,
    backgroundColor: tokens.color.bg2,
    borderWidth: 1,
    borderColor: tokens.color.line
  },
  dot: {
    width: 7,
    height: 7,
    borderRadius: 3.5
  },
  text: {
    color: tokens.color.fg2,
    fontSize: 12,
    fontWeight: '600'
  }
})
