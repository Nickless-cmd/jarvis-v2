import { StyleSheet, Text, View } from 'react-native'
import { useStyles, useTheme, type Theme } from '../theme/ThemeContext'
import { PulsIkon } from './PulsIkon'
import { Prikker } from './Prikker'

/**
 * Arbejdslinjen — nederst i beskeden, kun mens der streames.
 *
 * Bjørn 29/9-2026: linjen skal ligge i BUNDEN af beskeden (ikke over
 * composeren), leve fra streamen starter til den slutter, og forsvinde igen.
 * Så forlader den skærmen sammen med arbejdet i stedet for at stå tilbage som
 * en tom bjælke — og den melder hvad der sker LIGE NU, hvor intet andet i
 * beskeden gør det mens turen kører.
 *
 * Puls-mærket og prikkerne er mobilens egne komponenter, uændrede: samme
 * geometri som desks `JarvisRing`, så de to klienter viser samme tegn.
 *
 * Teksten kommer fra `arbejdslinjeTekst` — sætningen er bygget i Jarvis'
 * stemme, ikke i serverens label-sprog. `null` = intet at vise = ingen linje.
 */
export function Arbejdslinje({ tekst }: { tekst: string | null }) {
  const tokens = useTheme()
  const styles = useStyles(makestyles)
  if (!tekst) return null
  return (
    <View
      style={styles.linje}
      testID="arbejdslinje"
      accessibilityRole="text"
      accessibilityLabel={tekst}
    >
      <PulsIkon size={15} color={tokens.color.accent} />
      <Text style={styles.tekst} numberOfLines={2}>{tekst}</Text>
      <Prikker farve={tokens.color.fg3} />
    </View>
  )
}

const makestyles = (tokens: Theme) => StyleSheet.create({
  linje: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: tokens.spacing.sm,
    paddingHorizontal: tokens.spacing.lg,
    paddingVertical: tokens.spacing.sm,
  },
  // `flexShrink` så en lang sti ikke skubber prikkerne ud af skærmen.
  tekst: { color: tokens.color.fg2, fontSize: 13.5, flexShrink: 1 },
})
