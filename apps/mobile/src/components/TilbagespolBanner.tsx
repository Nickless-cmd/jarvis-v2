import { Pressable, StyleSheet, Text, View } from 'react-native'
import { X } from 'lucide-react-native'
import { useStyles, useTheme, type Theme } from '../theme/ThemeContext'

/**
 * Banneret efter en tilbagespoling — Claude Desktops tre løfter (§8):
 * beskederne kan komme tilbage, filerne er uændrede, fortryd lukker ved næste
 * besked. Som desk'ens `TilbagespolBanner`.
 */
export function TilbagespolBanner({ fjernet, fejl, onFortryd, onLuk }: {
  fjernet: number | null
  fejl: string
  onFortryd: () => void
  onLuk: () => void
}) {
  const tokens = useTheme()
  const styles = useStyles(makestyles)
  if (fjernet == null && !fejl) return null
  return (
    <View style={styles.banner} testID="tilbagespol-banner">
      <View style={styles.tekst}>
        {fjernet != null ? (
          <Text style={styles.linje}>
            Spolede tilbage — {fjernet} {fjernet === 1 ? 'besked' : 'beskeder'} fjernet. Dine filer er uændrede.
          </Text>
        ) : null}
        {fejl ? <Text style={styles.fejl}>{fejl}</Text> : null}
      </View>
      {fjernet != null ? (
        <Pressable accessibilityRole="button" accessibilityLabel="Fortryd" onPress={onFortryd} style={styles.fortryd} hitSlop={6}>
          <Text style={styles.fortrydTekst}>Fortryd</Text>
        </Pressable>
      ) : null}
      <Pressable accessibilityRole="button" accessibilityLabel="Luk" onPress={onLuk} hitSlop={10}>
        <X size={16} color={tokens.color.fg3} strokeWidth={2} />
      </Pressable>
    </View>
  )
}

const makestyles = (tokens: Theme) => StyleSheet.create({
  banner: {
    flexDirection: 'row', alignItems: 'center', gap: tokens.spacing.sm,
    marginHorizontal: tokens.spacing.lg, marginBottom: tokens.spacing.xs,
    paddingHorizontal: tokens.spacing.md, paddingVertical: 8,
    borderRadius: 12, borderWidth: StyleSheet.hairlineWidth, borderColor: tokens.color.line,
    backgroundColor: tokens.color.bg2,
  },
  tekst: { flex: 1, gap: 2 },
  linje: { color: tokens.color.fg2, fontSize: 13 },
  fejl: { color: tokens.color.error, fontSize: 13 },
  fortryd: { borderWidth: 1, borderColor: tokens.color.accent, borderRadius: 8, paddingHorizontal: 10, paddingVertical: 4 },
  fortrydTekst: { color: tokens.color.accent, fontSize: 13, fontWeight: '600' },
})
