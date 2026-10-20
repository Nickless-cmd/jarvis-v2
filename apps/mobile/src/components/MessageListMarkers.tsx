import { StyleSheet, Text, View } from 'react-native'
import { useStyles, type Theme } from '../theme/ThemeContext'

export function NyeBeskederRow() {
  const styles = useStyles(makeStyles)
  return (
    <View style={styles.nyeRow} accessibilityRole="text" accessibilityLabel="Nye beskeder" testID="nye-beskeder">
      <View style={styles.nyeStreg} />
      <Text style={styles.nyeTekst}>Nye beskeder</Text>
      <View style={styles.nyeStreg} />
    </View>
  )
}

export function CompactMarkerRow({ content }: { content: string }) {
  const styles = useStyles(makeStyles)
  return (
    <View style={styles.compactMarkerRow} testID="compact-marker">
      <Text style={styles.compactMarkerText}>{content}</Text>
    </View>
  )
}

const makeStyles = (theme: Theme) => StyleSheet.create({
  nyeRow: { flexDirection: 'row', alignItems: 'center', gap: 10, marginHorizontal: theme.spacing.lg, marginVertical: 10 },
  nyeStreg: { flex: 1, height: StyleSheet.hairlineWidth, backgroundColor: theme.color.accent, opacity: 0.6 },
  nyeTekst: { color: theme.color.accent, fontSize: 12, fontWeight: '600', letterSpacing: 0.3 },
  compactMarkerRow: {
    marginHorizontal: theme.spacing.lg,
    marginVertical: theme.spacing.sm,
    paddingVertical: theme.spacing.sm,
    paddingHorizontal: theme.spacing.md,
    borderRadius: theme.radius.sm,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: theme.color.warn + '33',
    backgroundColor: theme.color.warn + '0D',
  },
  compactMarkerText: {
    fontSize: 11,
    fontStyle: 'italic',
    lineHeight: 15,
    color: theme.color.warn,
    opacity: 0.8,
  },
})
