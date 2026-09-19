import { Modal, Platform, Pressable, ScrollView, StyleSheet, Text, View } from 'react-native'
import { useMemo } from 'react'
import { useStyles, type Theme } from '../theme/ThemeContext'
import { linjeDiff } from '../lib/linjeDiff'

/**
 * Diff-arket — mobilens udgave af Claude Desktops diff-rude (cc-desktop-
 * chatview.md §9: «Click a filename on an Edited or Wrote row to open that
 * file in the diff pane»). Telefonen har ingen side-rude, så ændringen glider
 * op som et ark: filens navn, +/−, og linjerne i rød og grøn.
 *
 * Viser DETTE kalds ændring (old → new), ikke filens samlede git-diff — det
 * er det man trykkede på.
 */
export function DiffArk({ aendring, onClose }: {
  aendring: { sti: string; gammel: string; ny: string } | null
  onClose: () => void
}) {
  const styles = useStyles(makestyles)
  const linjer = useMemo(() => (aendring ? linjeDiff(aendring.gammel, aendring.ny) : []), [aendring])
  if (!aendring) return null
  const plus = linjer.filter((l) => l.slags === '+').length
  const minus = linjer.filter((l) => l.slags === '-').length
  const navn = aendring.sti.split('/').filter(Boolean).pop() ?? aendring.sti
  return (
    <Modal transparent visible animationType="slide" onRequestClose={onClose}>
      <Pressable style={styles.scrim} onPress={onClose} testID="diff-ark-scrim">
        <Pressable style={styles.ark} onPress={(e) => e.stopPropagation()} testID="diff-ark">
          <View style={styles.greb} />
          <View style={styles.hoved}>
            <Text style={styles.navn} numberOfLines={1}>{navn}</Text>
            {plus ? <Text style={[styles.tal, styles.plus]}>+{plus}</Text> : null}
            {minus ? <Text style={[styles.tal, styles.minus]}>−{minus}</Text> : null}
          </View>
          <Text style={styles.sti} numberOfLines={1}>{aendring.sti}</Text>
          <ScrollView style={styles.krop} contentContainerStyle={styles.kropIndhold}>
            <ScrollView horizontal showsHorizontalScrollIndicator={false}>
              <View>
                {linjer.map((l, i) => (
                  <Text
                    key={i}
                    style={[styles.linje, l.slags === '+' ? styles.linjePlus : l.slags === '-' ? styles.linjeMinus : null]}
                  >
                    {l.slags}{' '}{l.tekst || ' '}
                  </Text>
                ))}
              </View>
            </ScrollView>
          </ScrollView>
        </Pressable>
      </Pressable>
    </Modal>
  )
}

const MONO = Platform.select({ ios: 'Menlo', default: 'monospace' })

const makestyles = (tokens: Theme) => StyleSheet.create({
  scrim: { flex: 1, backgroundColor: 'rgba(0,0,0,0.4)', justifyContent: 'flex-end' },
  ark: {
    maxHeight: '80%', backgroundColor: tokens.color.bgFloat,
    borderTopLeftRadius: 18, borderTopRightRadius: 18, paddingBottom: 24,
  },
  greb: { alignSelf: 'center', width: 36, height: 4, borderRadius: 2, backgroundColor: tokens.color.line, marginTop: 8, marginBottom: 10 },
  hoved: { flexDirection: 'row', alignItems: 'center', gap: 8, paddingHorizontal: tokens.spacing.lg },
  navn: { color: tokens.color.fg1, fontSize: 16, fontWeight: '600', flexShrink: 1 },
  tal: { fontSize: 13, fontWeight: '600', fontVariant: ['tabular-nums'] },
  plus: { color: tokens.color.ok },
  minus: { color: tokens.color.error },
  sti: { color: tokens.color.fg3, fontSize: 12, paddingHorizontal: tokens.spacing.lg, marginTop: 2, marginBottom: 10 },
  krop: { borderTopWidth: StyleSheet.hairlineWidth, borderTopColor: tokens.color.line },
  kropIndhold: { paddingVertical: 8 },
  linje: { fontFamily: MONO, fontSize: 12, lineHeight: 18, color: tokens.color.fg2, paddingHorizontal: tokens.spacing.lg },
  linjePlus: { backgroundColor: tokens.color.ok + '22', color: tokens.color.fg1 },
  linjeMinus: { backgroundColor: tokens.color.error + '22', color: tokens.color.fg1 },
})
