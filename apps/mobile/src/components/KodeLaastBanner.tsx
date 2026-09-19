import { StyleSheet, Text, View } from 'react-native'
import { Lock } from 'lucide-react-native'
import { useStyles, useTheme, type Theme } from '../theme/ThemeContext'

/**
 * Code mode er lukket på denne telefon — enheds-reglen (19/9-2026, Codex'
 * fjernstyring): code mode kræver at telefonen er tilføjet i desk. Siger HVOR
 * man gør det, som Codex' fejltekster siger hvad der mangler.
 */
export function KodeLaastBanner({ vis }: { vis: boolean }) {
  const tokens = useTheme()
  const styles = useStyles(makestyles)
  if (!vis) return null
  return (
    <View style={styles.banner} testID="kode-laast" accessibilityRole="alert">
      <Lock size={16} color={tokens.color.warn} strokeWidth={2} />
      <Text style={styles.tekst}>
        Code mode er lukket på denne telefon. Tilføj den i desk på computeren: Indstillinger → Konto → Enheder → «Tilføj telefon», og scan koden igen.
      </Text>
    </View>
  )
}

const makestyles = (tokens: Theme) => StyleSheet.create({
  banner: {
    flexDirection: 'row', alignItems: 'flex-start', gap: tokens.spacing.sm,
    marginHorizontal: tokens.spacing.lg, marginBottom: tokens.spacing.xs,
    paddingHorizontal: tokens.spacing.md, paddingVertical: 10,
    borderRadius: 12, borderWidth: 1, borderColor: tokens.color.warn + '66',
    backgroundColor: tokens.color.warn + '14',
  },
  tekst: { color: tokens.color.fg1, fontSize: 13, lineHeight: 19, flex: 1 },
})
