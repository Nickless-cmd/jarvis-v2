import { StyleSheet, Text, View } from 'react-native'
import { useStyles, useTheme, type Theme } from '../theme/ThemeContext'
import { AnimeretPuls } from './AnimeretPuls'
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
 * Puls-mærket er mobilens EGEN komponent i sin ANIMEREDE form
 * (`AnimeretPuls`, ikke det statiske `PulsIkon`): samme geometri og samme
 * rytme som desks `JarvisRing`, så de to klienter viser samme tegn — og
 * samme bevægelse. Bjørn 30/9-2026: «dit/husets ikon mangler animation som i
 * header» — mærket i tilbage-badgen pulserer, og prikkerne ved siden af
 * rullede allerede, så det statiske mærke imellem dem stod stille i en linje
 * hvor alt andet bevægede sig.
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
      {/* `size={15}` er mærkets mål i denne linje: bjælkerne bliver 2,85 x
          9,15 dp — præcis de tal det statiske `PulsIkon` tegnede ved 15. Kun
          bevægelsen er ny. `testID` bevares, så tegnet kan findes som før. */}
      <AnimeretPuls size={15} farve={tokens.color.accent} testID="puls-ikon" />
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
