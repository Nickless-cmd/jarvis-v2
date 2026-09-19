import { Pressable, StyleSheet, Text, View } from 'react-native'
import { useOpmaerksomhed, type OpmTilstand } from '../lib/opmaerksomhed'
import { useStyles, useTheme, type Theme } from '../theme/ThemeContext'

export function farveFor(tokens: Theme, t: OpmTilstand): string {
  switch (t) {
    case 'waiting': return tokens.color.warn
    case 'failed': return tokens.color.error
    case 'review': return tokens.color.ok
    case 'running': return tokens.color.accent
    default: return tokens.color.fg3
  }
}

/**
 * Tilstands-hjernens linje øverst i sidepanelet — samme som desk's linje over
 * sidepanelets fod. Tavs når intet kræver dig. Tryk åbner den samtale der
 * vinder prioriteten.
 */
export function OpmaerksomhedsLinje({ onAabn }: { onAabn: (sessionId: string) => void }) {
  const tokens = useTheme()
  const styles = useStyles(makeStyles)
  const o = useOpmaerksomhed()
  if (!o || o.tilstand === 'idle') return null
  const antal = o.antal[o.tilstand as keyof typeof o.antal] ?? 0
  const fokus = o.fokus
  return (
    <Pressable
      testID="opmaerksomhed"
      accessibilityRole="button"
      accessibilityLabel={`${o.etiket}${fokus?.titel ? `: ${fokus.titel}` : ''}`}
      disabled={!fokus?.session_id}
      onPress={() => { if (fokus?.session_id) onAabn(fokus.session_id) }}
      style={({ pressed }) => [styles.linje, pressed && styles.pressed]}
    >
      <View style={[styles.prik, { backgroundColor: farveFor(tokens, o.tilstand) }]} />
      <Text style={styles.etiket} numberOfLines={1}>{o.etiket}{antal > 1 ? ` · ${antal}` : ''}</Text>
      {fokus?.titel ? <Text style={styles.titel} numberOfLines={1}>{fokus.titel}</Text> : null}
    </Pressable>
  )
}

const makeStyles = (tokens: Theme) => StyleSheet.create({
  linje: {
    flexDirection: 'row', alignItems: 'center', gap: 8,
    marginHorizontal: tokens.spacing.md, marginBottom: tokens.spacing.sm,
    paddingVertical: 9, paddingHorizontal: 12,
    borderRadius: tokens.radius.lg, borderWidth: StyleSheet.hairlineWidth, borderColor: tokens.color.line,
    backgroundColor: tokens.color.bg1,
  },
  prik: { width: 8, height: 8, borderRadius: 4 },
  etiket: { color: tokens.color.fg1, fontWeight: '700', fontSize: 14 },
  titel: { color: tokens.color.fg3, fontSize: 13, flexShrink: 1 },
  pressed: { opacity: 0.7 },
})
