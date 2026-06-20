import { ActivityIndicator, Pressable, StyleSheet, Text, View } from 'react-native'
import { tokens } from '../theme/tokens'
import type { UpdateManifest } from '../lib/appUpdate'

/** Banner i toppen når en opdatering er fundet. Viser version + noter +
 *  "Opdatér"/"Senere". `busy` viser progress mens download/install kører. */
export function UpdateBanner({
  manifest,
  busy,
  progress,
  onUpdate,
  onDismiss,
}: {
  manifest: UpdateManifest
  busy: boolean
  progress: number
  onUpdate: () => void
  onDismiss: () => void
}) {
  return (
    <View style={styles.root}>
      <View style={styles.textCol}>
        <Text style={styles.title}>Ny version {manifest.version}</Text>
        {manifest.notes ? (
          <Text style={styles.notes} numberOfLines={2}>
            {manifest.notes}
          </Text>
        ) : null}
        {busy ? (
          <Text style={styles.notes}>Henter… {Math.round(progress * 100)}%</Text>
        ) : null}
      </View>
      {busy ? (
        <ActivityIndicator color={tokens.color.accent} />
      ) : (
        <View style={styles.btnRow}>
          <Pressable
            accessibilityRole="button"
            accessibilityLabel="Senere"
            onPress={onDismiss}
            hitSlop={8}
            style={({ pressed }) => [styles.btn, pressed && styles.pressed]}
          >
            <Text style={styles.btnGhost}>Senere</Text>
          </Pressable>
          <Pressable
            accessibilityRole="button"
            accessibilityLabel="Opdatér"
            onPress={onUpdate}
            hitSlop={8}
            style={({ pressed }) => [styles.btn, styles.btnPrimary, pressed && styles.pressed]}
          >
            <Text style={styles.btnPrimaryText}>Opdatér</Text>
          </Pressable>
        </View>
      )}
    </View>
  )
}

const styles = StyleSheet.create({
  root: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: tokens.spacing.sm,
    paddingHorizontal: tokens.spacing.md,
    paddingVertical: tokens.spacing.sm,
    backgroundColor: tokens.color.bg2,
    borderBottomColor: tokens.color.line,
    borderBottomWidth: 1,
  },
  textCol: { flex: 1 },
  title: { color: tokens.color.fg1, fontWeight: '700' },
  notes: { color: tokens.color.fg3, fontSize: 12, marginTop: tokens.spacing.xs },
  btnRow: { flexDirection: 'row', gap: tokens.spacing.xs },
  btn: { minHeight: 36, paddingHorizontal: tokens.spacing.md, borderRadius: tokens.radius.md, alignItems: 'center', justifyContent: 'center' },
  btnPrimary: { backgroundColor: tokens.color.accent },
  btnPrimaryText: { color: tokens.color.bg0, fontWeight: '700' },
  btnGhost: { color: tokens.color.fg2 },
  pressed: { opacity: 0.7 },
})
