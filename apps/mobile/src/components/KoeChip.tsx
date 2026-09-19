import { Pressable, StyleSheet, Text, View } from 'react-native'
import { X } from 'lucide-react-native'
import { useStyles, useTheme, type Theme } from '../theme/ThemeContext'

/**
 * Den køede besked over skrivefeltet — som desk'ens `KoeChip`. Claude
 * Desktops regel (cc-desktop-chatview.md §6): at fjerne den fra køen
 * afbryder ALDRIG turen der kører. ×'en rører kun køen.
 */
export function KoeChip({ tekst, onAnnuller }: { tekst: string | null; onAnnuller: () => void }) {
  const tokens = useTheme()
  const styles = useStyles(makestyles)
  if (!tekst) return null
  return (
    <View style={styles.chip} testID="koe-chip">
      <Text style={styles.label}>I kø</Text>
      <Text style={styles.tekst} numberOfLines={1}>{tekst}</Text>
      <Pressable accessibilityRole="button" accessibilityLabel="Fjern fra kø" onPress={onAnnuller} hitSlop={10}>
        <X size={16} color={tokens.color.fg3} strokeWidth={2} />
      </Pressable>
    </View>
  )
}

const makestyles = (tokens: Theme) => StyleSheet.create({
  chip: {
    flexDirection: 'row', alignItems: 'center', gap: tokens.spacing.sm,
    marginHorizontal: tokens.spacing.lg, marginBottom: tokens.spacing.xs,
    paddingHorizontal: tokens.spacing.md, paddingVertical: 8,
    borderRadius: 12, borderWidth: StyleSheet.hairlineWidth, borderColor: tokens.color.line,
    backgroundColor: tokens.color.bg2,
  },
  label: { color: tokens.color.accent, fontSize: 13, fontWeight: '600' },
  tekst: { color: tokens.color.fg2, fontSize: 13, flex: 1 },
})
