import { Pressable, StyleSheet, Text, View } from 'react-native'
import { tokens } from '../theme/tokens'

interface Props {
  /** Hvad der blev gjort, i datid: «Læste db.py», «Ændrede 16 filer». */
  summary: string
  onPress?: () => void
  /** Sandt mens værktøjet stadig kører. */
  running?: boolean
}

/**
 * Et værktøjs-resultat som ÉN kompakt linje inde i samtalen.
 *
 * Målt i ChatGPT/Codex-appen på enheden 2026-09-02. Sådan ser det ud dér:
 *
 *     </> Redigerede test_push_dispatcher.py  >
 *     </> Ændrede 16 filer  >
 *
 * Ingen kort, ingen ramme, ingen udfoldet output — bare en grå linje mellem
 * afsnittene, med et chevron der siger «der er mere at se her». Det er hele
 * grunden til at deres tråd virker rolig: værktøjsarbejde fylder én linje,
 * ikke en blok.
 */
export function InlineToolLine({ summary, onPress, running }: Props) {
  const body = (
    <View style={styles.row}>
      <Text style={styles.glyph}>{'</>'}</Text>
      <Text style={[styles.summary, running && styles.running]} numberOfLines={1}>
        {summary}
      </Text>
      {onPress ? <Text style={styles.chevron}>{'›'}</Text> : null}
    </View>
  )
  if (!onPress) return body
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel={summary}
      onPress={onPress}
      testID="inline-tool-line"
    >
      {body}
    </Pressable>
  )
}

const styles = StyleSheet.create({
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: tokens.spacing.sm,
    paddingVertical: tokens.spacing.sm
  },
  glyph: {
    color: tokens.color.fg2,
    fontSize: 13,
    fontFamily: 'monospace'
  },
  summary: {
    color: tokens.color.fg2,
    fontSize: 15,
    flexShrink: 1
  },
  running: { color: tokens.color.fg3 },
  chevron: { color: tokens.color.fg2, fontSize: 17 }
})
